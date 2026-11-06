"""Pack workflows that cross models: adding a member's saved assets to their packs.

Every write here runs in one transaction, so a failure part-way leaves no
half-made item behind.
"""

from collections.abc import Sequence

from django.db import transaction
from django.db.models import Max

from catalog.library import save_asset, save_to_library
from catalog.models import Asset, SavedAsset
from providers import KINDS

from .models import TITLE_MAX_LENGTH, Pack, PackItem, default_variant


class NotYourEntryError(ValueError):
    """A pack item may only point to a SavedAsset owned by the pack's owner."""


def add_to_pack(pack: Pack, saved_asset: SavedAsset) -> tuple[PackItem, bool]:
    """Add one of the owner's saved assets to `pack`; return (item, created).

    A new item goes at the end, on the asset's default variant
    (packs.models.default_variant) with a blank import path. An entry
    already in the pack returns its item untouched with created=False.
    Raises NotYourEntryError, writing nothing, when the entry isn't the
    pack owner's. Reading the last position and inserting run in one
    transaction.
    """
    if saved_asset.user_id != pack.owner_id:
        raise NotYourEntryError("A pack can only hold its owner's saved assets.")
    with transaction.atomic():
        item = pack.items.filter(saved_asset=saved_asset).first()
        if item is not None:
            return item, False
        last = pack.items.aggregate(last=Max("position"))["last"]
        asset = saved_asset.asset
        item = PackItem.objects.create(
            pack=pack,
            saved_asset=saved_asset,
            preferred_variant=default_variant(asset.kind, asset.variants),
            position=0 if last is None else last + 1,
        )
    return item, True


def move_item(item: PackItem, step: int) -> bool:
    """Move an item one place earlier (step -1) or later (step 1) in its pack.

    It swaps positions with its neighbour, in one transaction, and returns
    False without writing anything when there's no neighbour that way.
    """
    if step not in (-1, 1):
        raise ValueError("An item moves one place at a time.")
    with transaction.atomic():
        items = list(item.pack.items.select_for_update().order_by("position", "id"))
        index = next(i for i, other in enumerate(items) if other.pk == item.pk)
        if not 0 <= index + step < len(items):
            return False
        items[index], items[index + step] = items[index + step], items[index]
        # Positions are rewritten 0, 1, 2…, which also closes any gaps a Remove left.
        for position, other in enumerate(items):
            if other.position != position:
                other.position = position
                other.save(update_fields=["position"])
    return True


# The builder's auto sorts, by their form value, each with its label. Every
# sort ends on the title and then the item's id, so equal items keep a stable
# order.
ITEM_SORTS = {
    "type": "Type",
    "title": "Title A–Z",
    "provider": "Provider",
    "license": "License",
}


class ReorderError(ValueError):
    """A new order must name every item of the pack exactly once."""


def _rewrite_positions(items: Sequence[PackItem]) -> None:
    """Save positions 0, 1, 2… in the given order, touching only items that moved."""
    for position, item in enumerate(items):
        if item.position != position:
            item.position = position
            item.save(update_fields=["position"])


def reorder_items(pack: Pack, item_ids: Sequence[int]) -> None:
    """Put the pack's items in the order of `item_ids` (drag and drop).

    `item_ids` must hold every item of the pack exactly once, so a stale
    page (an item added or removed in another tab) can't lose or duplicate
    one: it raises ReorderError and writes nothing. Positions are rewritten
    0, 1, 2… in one transaction.
    """
    with transaction.atomic():
        items = {item.pk: item for item in pack.items.select_for_update()}
        if len(item_ids) != len(items) or set(item_ids) != set(items):
            raise ReorderError("That order doesn't match the pack's items. Reload and try again.")
        _rewrite_positions([items[pk] for pk in item_ids])


def _sort_key(sort: str):
    kind_rank = {kind: index for index, kind in enumerate(KINDS)}

    def key(item: PackItem):
        asset = item.asset
        title = (asset.title.casefold(), item.pk)
        if sort == "type":
            return (kind_rank.get(asset.kind, len(kind_rank)), *title)
        if sort == "provider":
            return (asset.get_provider_display().casefold(), *title)
        if sort == "license":
            info = asset.license_info
            # Freest first: what needs no credit, then by the license's name.
            return (info.needs_credit, asset.license.casefold(), *title)
        return title

    return key


def sort_items(pack: Pack, sort: str) -> None:
    """Auto sort the pack's items by one of ITEM_SORTS, in one transaction.

    "type" follows the Discover order (textures, HDRIs, models, sounds),
    "provider" and "title" go A–Z, and "license" puts what needs no credit
    first. Ties fall back to the title, then the item's id. Raises
    ValueError for an unknown sort, writing nothing.
    """
    if sort not in ITEM_SORTS:
        raise ValueError(f"Unknown sort: {sort!r}")
    with transaction.atomic():
        items = list(pack.items.select_for_update().select_related("saved_asset__asset"))
        _rewrite_positions(sorted(items, key=_sort_key(sort)))


def add_from_provider(pack: Pack, provider_key: str, external_id: str) -> tuple[PackItem, bool]:
    """Add a provider asset (a Discover result) to `pack`; return (item, created).

    The asset goes through the owner's library first (save_to_library): an
    entry they already have is used as it is, and otherwise a new To review
    entry is made, fetching the Asset if no one has saved it yet. Raises
    UnknownProviderError or ProviderError, and then nothing is saved or
    added. The save and the add share one transaction.
    """
    with transaction.atomic():
        entry, _ = save_to_library(pack.owner, provider_key, external_id)
        return add_to_pack(pack, entry)


def add_suggestion(pack: Pack, asset: Asset) -> tuple[SavedAsset, bool, PackItem]:
    """Add a suggestion, a stored Asset, to `pack`; return (entry, entry_created, item).

    The asset goes through the owner's library first (save_asset): an entry
    they already have is used untouched, otherwise a new To review entry is
    made. Then add_to_pack(). No provider is ever called, because the Asset
    is already stored. Both steps share one transaction, so a failure leaves
    no new entry and no item behind.
    """
    with transaction.atomic():
        entry, entry_created = save_asset(pack.owner, asset)
        item, _ = add_to_pack(pack, entry)
    return entry, entry_created, item


COPY_SUFFIX = " (copy)"


def copy_title(title: str) -> str:
    """The copy's title, "<title> (copy)", shortened so it fits the title's limit."""
    room = TITLE_MAX_LENGTH - len(COPY_SUFFIX)
    return title[:room].rstrip() + COPY_SUFFIX


def copy_pack(pack: Pack, user) -> Pack:
    """Copy pack: a private copy of `pack` for `user`, in one transaction.

    The copy is titled "<title> (copy)", keeps the intended use and tags, and
    points back with copied_from. Each item becomes an item of the copy on
    `user`'s own entry for its asset: an entry they have is used untouched,
    otherwise a new To review one is made (save_asset), so no provider is
    ever called and nothing of the original owner's review comes along. The
    variant, import path and position are copied as they are. A failure
    part-way leaves no pack, item or entry behind.
    """
    with transaction.atomic():
        title = copy_title(pack.title)
        copy = Pack.objects.create(
            owner=user,
            title=title,
            description=pack.description,
            slug=Pack.objects.free_slug(title),
            copied_from=pack,
        )
        copy.tags.set(pack.tags.all())
        for item in pack.ordered_items():
            entry, _ = save_asset(user, item.asset)
            PackItem.objects.create(
                pack=copy,
                saved_asset=entry,
                preferred_variant=item.preferred_variant,
                import_path=item.import_path,
                position=item.position,
            )
    return copy
