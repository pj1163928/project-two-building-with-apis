"""Pack workflows that cross models: adding a member's saved assets to their packs.

Every write here runs in one transaction, so a failure part-way leaves no
half-made item behind.
"""

from django.db import transaction
from django.db.models import Max

from catalog.library import save_to_library
from catalog.models import SavedAsset

from .models import Pack, PackItem, default_variant


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
