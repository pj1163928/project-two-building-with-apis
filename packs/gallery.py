"""The public gallery on the main page: public packs only, searched, filtered,
sorted and paged by filter_public_packs(), and each card's mosaic and type count.

The gallery is open to everyone. It starts from Pack.objects.public(), and
every parameter only narrows that, so no query can surface a private or
unlisted pack.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from typing import Any
from urllib.parse import urlencode

from django.core.paginator import Page, Paginator
from django.db.models import Prefetch, Q
from django.urls import reverse

from catalog.discover import KIND_TILES, clean_query
from catalog.tags import normalize_tag
from providers import KINDS

from .models import Pack, PackItem

PAGE_SIZE = 12
DEFAULT_SORT = "newest"
# The sort select's options: newest made first, or most items first.
GALLERY_SORTS = {"newest": "Newest", "items": "Most items"}
# Each sort's order; both end on newest and then id, so pages never shift.
SORT_ORDERS = {
    "newest": ("-created_at", "-id"),
    "items": ("-item_count", "-created_at", "-id"),
}
# How many thumbnails a gallery card's mosaic shows.
MOSAIC_SIZE = 4


@dataclass(frozen=True)
class GalleryParams:
    """The gallery's search, type, sort and page, tidied from a query string."""

    q: str = ""
    type: str = ""
    sort: str = DEFAULT_SORT
    page: int = 1

    @property
    def is_filtered(self) -> bool:
        """Whether a search or the type filter narrows the gallery."""
        return bool(self.q or self.type)

    def query_string(self, page: int | None = None) -> str:
        """These parameters (or another `page` of them), defaults left out."""
        page = self.page if page is None else page
        pairs = [("q", self.q)] if self.q else []
        if self.type:
            pairs.append(("type", self.type))
        if self.sort != DEFAULT_SORT:
            pairs.append(("sort", self.sort))
        if page > 1:
            pairs.append(("page", page))
        return urlencode(pairs)

    def url(self, page: int | None = None) -> str:
        """The main page's URL for these parameters; the whole gallery is plain /."""
        query = self.query_string(page)
        path = reverse("packs:home")
        return f"{path}?{query}" if query else path


@dataclass(frozen=True)
class GalleryPage:
    """One page of the gallery, with the tidied parameters behind it.

    Each pack on the page carries `item_count`, its `tags` and `owner`, and
    `gallery_items` (every item in position order, with its Asset), which
    the card's mosaic and type count read without further queries.
    """

    page: Page
    params: GalleryParams

    @property
    def url(self) -> str:
        return self.params.url()

    @property
    def previous_url(self) -> str:
        return self.params.url(self.page.previous_page_number()) if self.page.has_previous() else ""

    @property
    def next_url(self) -> str:
        return self.params.url(self.page.next_page_number()) if self.page.has_next() else ""

    @property
    def cards(self) -> list["GalleryCard"]:
        """A card for each pack on this page, in order."""
        return [gallery_card(pack) for pack in self.page.object_list]


def _last(params: Mapping[str, Any], name: str) -> str:
    """The last value given for `name`, from a QueryDict or a plain dict, or ""."""
    if hasattr(params, "getlist"):
        values = params.getlist(name)
        return values[-1] if values else ""
    value = params.get(name)
    return "" if value is None else str(value)


def _page_number(raw: str) -> int:
    """A whole page number from 1, or 1 (six digits at most, so int() stays cheap)."""
    if raw.isascii() and raw.isdigit() and len(raw) <= 6 and int(raw) >= 1:
        return int(raw)
    return 1


def clean_gallery_params(params: Mapping[str, Any]) -> GalleryParams:
    """Tidy the gallery's query parameters, falling back to the defaults.

    An unknown type is no type filter, an unknown sort is "newest", and a
    page that isn't a whole number from 1 is page 1. None of these is an error.
    """
    kind = _last(params, "type")
    sort = _last(params, "sort")
    return GalleryParams(
        q=clean_query(_last(params, "q")),
        type=kind if kind in KINDS else "",
        sort=sort if sort in SORT_ORDERS else DEFAULT_SORT,
        page=_page_number(_last(params, "page")),
    )


def filter_public_packs(params: Mapping[str, Any]) -> GalleryPage:
    """One page of public packs for the gallery's query parameters.

    `q` keeps packs where every word is in the title or a tag (case ignored;
    a word is tidied like a tag before it's matched against tags), `type`
    keeps packs holding at least one item of that kind, `sort` is "newest"
    (the default) or "items" (most items first), and pages hold PAGE_SIZE.
    Bad values fall back to the defaults (clean_gallery_params()), and a page
    past the end is the last page. Only public packs are ever listed: never a
    private or unlisted one, whatever the parameters.
    """
    cleaned = clean_gallery_params(params)
    packs = Pack.objects.public()
    for word in cleaned.q.split():
        tagged = Pack.objects.filter(tags__name__icontains=normalize_tag(word) or word)
        packs = packs.filter(Q(title__icontains=word) | Q(pk__in=tagged.values("pk")))
    if cleaned.type:
        holding = PackItem.objects.filter(saved_asset__asset__kind=cleaned.type)
        packs = packs.filter(pk__in=holding.values("pack"))
    packs = (
        packs.with_item_count()
        .select_related("owner")
        .prefetch_related(
            "tags",
            Prefetch(
                "items",
                queryset=PackItem.objects.select_related("saved_asset__asset").order_by(
                    "position", "id"
                ),
                to_attr="gallery_items",
            ),
        )
        .order_by(*SORT_ORDERS[cleaned.sort])
    )
    page = Paginator(packs, PAGE_SIZE).get_page(cleaned.page)
    return GalleryPage(page=page, params=replace(cleaned, page=page.number))


# ------------------------------------------------------------------ a gallery card


@dataclass(frozen=True)
class GalleryCard:
    """What one gallery card shows: the pack, the Assets of its first MOSAIC_SIZE
    items by position, how many empty tiles fill the rest, and its count by type."""

    pack: Pack
    mosaic: list[Any]
    blanks: int
    summary: str

    @property
    def blank_tiles(self) -> range:
        """One step per empty mosaic tile, for the template to loop over."""
        return range(self.blanks)


def gallery_card(pack: Pack) -> GalleryCard:
    """The card for a pack from filter_public_packs() (which prefetches
    `gallery_items`; any other pack reads its items in position order)."""
    items = getattr(pack, "gallery_items", None)
    if items is None:
        items = list(pack.ordered_items())
    assets = [item.saved_asset.asset for item in items]
    mosaic = assets[:MOSAIC_SIZE]
    return GalleryCard(
        pack=pack,
        mosaic=mosaic,
        blanks=MOSAIC_SIZE - len(mosaic),
        summary=type_summary(asset.kind for asset in assets),
    )


# Each kind's name for a count of one and of more.
TYPE_NOUNS = {
    "texture": ("texture", "textures"),
    "hdri": ("HDRI", "HDRIs"),
    "model": ("model", "models"),
    "sound": ("sound", "sounds"),
}
EMPTY_SUMMARY = "No items yet"


def type_summary(kinds: Iterable[str]) -> str:
    """The count by type for a pack's items' kinds, e.g. "3 textures · 1 HDRI · 2 sounds".

    Types come in Discover's order (KINDS), whatever the items' order; one is
    singular and more are plural; a type the pack doesn't hold is left out.
    An empty pack is EMPTY_SUMMARY.
    """
    kinds = list(kinds)
    parts = []
    for kind in KINDS:
        count = kinds.count(kind)
        if count:
            one, many = TYPE_NOUNS[kind]
            parts.append(f"{count} {one if count == 1 else many}")
    return " · ".join(parts) or EMPTY_SUMMARY


def gallery_type_choices() -> list[tuple[str, str]]:
    """The type filter's choices: Any, then each kind as Discover names it."""
    return [("", "Any type"), *((tile.key, tile.label) for tile in KIND_TILES)]
