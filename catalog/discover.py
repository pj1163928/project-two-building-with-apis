"""Discover's shared logic: which shelves a search shows, and what each one holds.

The views stay thin; everything they decide comes from here.
"""

from dataclasses import dataclass, replace
from types import ModuleType
from urllib.parse import urlencode

from django.urls import reverse

from providers import KINDS, PROVIDERS_BY_KEY, AssetRecord, ProviderError, providers_for_kind

# Longest query passed to a provider. Longer input is cut, not refused.
MAX_QUERY_LENGTH = 100
DEFAULT_KIND = KINDS[0]


@dataclass(frozen=True)
class KindTile:
    """One of Discover's four type tiles.

    The colour classes are written out in full so Tailwind finds them. They
    are type colours, so they are used for nothing but the asset's type.
    """

    key: str
    label: str
    blurb: str
    text_class: str
    bar_class: str

    @property
    def provider_names(self) -> str:
        return " + ".join(provider.NAME for provider in providers_for_kind(self.key))

    @property
    def search_hint(self) -> str:
        return f"Type in the command bar above. {self.label} come from {self.provider_names}."


KIND_TILES = (
    KindTile("texture", "Textures", "PBR materials and surfaces", "text-texture", "bg-texture"),
    KindTile("hdri", "HDRIs", "Skies and image-based light", "text-hdri", "bg-hdri"),
    KindTile("model", "Models", "Props and scanned meshes", "text-model", "bg-model"),
    KindTile("sound", "Sounds", "Effects and ambience", "text-sound", "bg-sound"),
)
TILES_BY_KIND = {tile.key: tile for tile in KIND_TILES}


@dataclass(frozen=True)
class Shelf:
    """One provider's shelf for one search: still loading, loaded, or failed."""

    key: str  # the provider's KEY
    name: str  # the provider's display name
    kind: str
    query: str
    number: int  # 1-based position on the page
    loaded: bool = False
    records: tuple[AssetRecord, ...] = ()
    error: str = ""  # a ProviderError message, safe to show

    @property
    def url(self) -> str:
        return shelf_url(self.kind, self.key, self.query)

    @property
    def dom_id(self) -> str:
        return f"shelf-{self.key}"


def clean_query(raw: str | None) -> str:
    """Trim a search query, collapse its inner whitespace and cap its length."""
    return " ".join((raw or "").split())[:MAX_QUERY_LENGTH].strip()


def clean_kind(raw: str | None) -> str:
    """The Discover page's kind: a known kind, or textures for anything else."""
    return raw if raw in KINDS else DEFAULT_KIND


def shelf_url(kind: str, provider_key: str, query: str) -> str:
    """The fragment URL for one provider's shelf of `query` results."""
    path = reverse("catalog:discover_shelf", args=[kind, provider_key])
    return f"{path}?{urlencode({'q': query})}"


def discover_url(kind: str, query: str = "") -> str:
    """The Discover page for `kind`, with `query` in the command bar."""
    params = {"type": kind, "q": query} if query else {"type": kind}
    return f"{reverse('catalog:discover')}?{urlencode(params)}"


def shelf_provider(kind: str, provider_key: str) -> ModuleType | None:
    """Return the provider module for a shelf URL, or None if the URL is invalid.

    Valid means a known provider that serves `kind` (the PRD's mapping), so an
    unknown kind, an unknown provider and a mismatch are all refused alike.
    """
    provider = PROVIDERS_BY_KEY.get(provider_key)
    if provider is None or provider not in providers_for_kind(kind):
        return None
    return provider


def pending_shelves(kind: str, query: str) -> list[Shelf]:
    """The not-yet-loaded shelves the Discover page shows for a search."""
    return [
        Shelf(key=provider.KEY, name=provider.NAME, kind=kind, query=query, number=number)
        for number, provider in enumerate(providers_for_kind(kind), start=1)
    ]


def load_shelf(provider: ModuleType, kind: str, query: str) -> Shelf:
    """Search one provider and return its loaded shelf.

    A ProviderError becomes the shelf's error message. Nothing else is caught:
    any other exception is a bug and should surface as one.
    """
    number = providers_for_kind(kind).index(provider) + 1
    shelf = Shelf(key=provider.KEY, name=provider.NAME, kind=kind, query=query, number=number)
    try:
        records = provider.search_records(query, kind)
    except ProviderError as error:
        return replace(shelf, loaded=True, error=str(error))
    return replace(shelf, loaded=True, records=tuple(records))
