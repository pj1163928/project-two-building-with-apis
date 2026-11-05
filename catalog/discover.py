"""Discover's shared logic: which shelves a search shows, and what each one holds.

The views stay thin; everything they decide comes from here.
"""

import hashlib
import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from types import ModuleType
from urllib.parse import urlencode

from django.core.cache import cache
from django.urls import reverse

from providers import (
    KINDS,
    PROVIDERS,
    PROVIDERS_BY_KEY,
    AssetRecord,
    ProviderError,
    providers_for_kind,
)

# Longest query passed to a provider. Longer input is cut, not refused.
MAX_QUERY_LENGTH = 100
DEFAULT_KIND = KINDS[0]
# Results per shelf page, and how far Load more goes: 20 pages is 240 results,
# the deepest Openverse lets anonymous clients page.
PAGE_SIZE = 12
MAX_PAGE = 20

# With no query, Discover shows a random one of these for the kind, so the
# shelves are never empty. Each one fills both of its kind's shelves
# (ambientCG's few models are all food, hence the model picks).
FEATURED_QUERIES = {
    "texture": ("brick", "wood", "rock", "moss", "metal", "fabric", "tiles", "concrete", "marble"),
    "hdri": ("sunset", "forest", "sky", "night", "overcast", "city", "field"),
    "model": ("apple", "bread", "fruit", "food"),
    "sound": ("rain", "footsteps", "wind", "door", "thunder", "birds", "fire"),
}

# How long a successful shelf's results are reused (the PRD: 1 hour).
SEARCH_CACHE_SECONDS = 60 * 60
# How long a provider's last known status is kept before it reads as unknown again.
STATUS_CACHE_SECONDS = 60 * 60


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
    page: int = 1  # Load more fetches the next page into the same shelf

    @property
    def url(self) -> str:
        return shelf_url(self.kind, self.key, self.query, self.page)

    @property
    def has_more(self) -> bool:
        """Whether Load more is offered: this page came back full and isn't the last allowed."""
        return (
            self.loaded
            and not self.error
            and len(self.records) == PAGE_SIZE
            and self.page < MAX_PAGE
        )

    @property
    def page_size(self) -> int:
        return PAGE_SIZE

    @property
    def page_url(self) -> str:
        """The Discover page this shelf belongs on: where sign-in sends a visitor back to."""
        return discover_url(self.kind, self.query)

    @property
    def next_url(self) -> str:
        return shelf_url(self.kind, self.key, self.query, self.page + 1)

    @property
    def shown_count(self) -> int:
        """How many results the shelf holds once this page is in: every earlier page was full."""
        return (self.page - 1) * PAGE_SIZE + len(self.records)

    @property
    def credit(self) -> str:
        return PROVIDERS_BY_KEY[self.key].CREDIT

    @property
    def credit_url(self) -> str:
        return PROVIDERS_BY_KEY[self.key].HOME_URL

    @property
    def tile(self) -> KindTile:
        """The shelf's type tile: its icon and colour stand in for a missing thumbnail."""
        return TILES_BY_KIND[self.kind]

    @property
    def status(self) -> "ProviderStatus":
        """The provider's status now, sent with a loaded shelf to update the status bar."""
        return provider_status(PROVIDERS_BY_KEY[self.key])

    @property
    def dom_id(self) -> str:
        return f"shelf-{self.key}"

    @property
    def results_id(self) -> str:
        return f"shelf-{self.key}-results"

    @property
    def more_id(self) -> str:
        return f"shelf-{self.key}-more"

    @property
    def count_id(self) -> str:
        return f"shelf-{self.key}-count"


def clean_query(raw: str | None) -> str:
    """Trim a search query, collapse its inner whitespace and cap its length."""
    return " ".join((raw or "").split())[:MAX_QUERY_LENGTH].strip()


def clean_kind(raw: str | None) -> str:
    """The Discover page's kind: a known kind, or textures for anything else."""
    return raw if raw in KINDS else DEFAULT_KIND


def clean_page(raw: str | None) -> int | None:
    """A shelf URL's page: 1 when absent, an int from 1 to MAX_PAGE, or None if invalid."""
    if raw is None:
        return 1
    if not raw.isdigit() or not 1 <= int(raw) <= MAX_PAGE:
        return None
    return int(raw)


def featured_query(
    kind: str, after: str = "", choose: Callable[[Sequence[str]], str] | None = None
) -> str:
    """A random search for `kind`, shown when Discover has no query.

    `after` is the pick being shuffled away from, so Shuffle always changes
    it. `choose` picks from the candidates (random.choice by default).
    """
    choices = [query for query in FEATURED_QUERIES[kind] if query != after]
    return (choose or random.choice)(choices)


def shuffle_url(kind: str, featured: str) -> str:
    """Discover for `kind` with a new random pick, never `featured` again."""
    return f"{reverse('catalog:discover')}?{urlencode({'type': kind, 'shuffle': featured})}"


def shelf_url(kind: str, provider_key: str, query: str, page: int = 1) -> str:
    """The fragment URL for one page of one provider's shelf of `query` results."""
    path = reverse("catalog:discover_shelf", args=[kind, provider_key])
    params = {"q": query, "page": page} if page > 1 else {"q": query}
    return f"{path}?{urlencode(params)}"


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


@dataclass(frozen=True)
class ProviderStatus:
    """A provider's last known status for the status bar: ok, error or unknown."""

    key: str
    name: str
    state: str = "unknown"

    @property
    def title(self) -> str:
        return {
            "ok": f"{self.name}: OK",
            "error": f"{self.name}: error on the last search",
        }.get(self.state, f"{self.name}: status unknown")


def _status_cache_key(provider_key: str) -> str:
    return f"discover:status:{provider_key}"


def record_status(provider: ModuleType, ok: bool) -> ProviderStatus:
    """Remember how `provider`'s latest search went, and return its new status."""
    state = "ok" if ok else "error"
    cache.set(_status_cache_key(provider.KEY), state, STATUS_CACHE_SECONDS)
    return ProviderStatus(key=provider.KEY, name=provider.NAME, state=state)


def provider_status(provider: ModuleType) -> ProviderStatus:
    """`provider`'s last known status: ok, error, or unknown if no shelf has used it."""
    state = cache.get(_status_cache_key(provider.KEY), "unknown")
    return ProviderStatus(key=provider.KEY, name=provider.NAME, state=state)


def provider_statuses() -> list[ProviderStatus]:
    """Every provider's last known status, in PROVIDERS order. Unused ones are unknown."""
    states = cache.get_many([_status_cache_key(provider.KEY) for provider in PROVIDERS])
    return [
        ProviderStatus(
            key=provider.KEY,
            name=provider.NAME,
            state=states.get(_status_cache_key(provider.KEY), "unknown"),
        )
        for provider in PROVIDERS
    ]


def search_cache_key(provider_key: str, kind: str, query: str, page: int = 1) -> str:
    """The cache key for one page of one search.

    Searches that differ only in case or spacing share it. The normalized
    query is hashed, so the key holds no spaces or user text.
    """
    normalized = clean_query(query).casefold()
    digest = hashlib.sha256(normalized.encode()).hexdigest()
    return f"discover:search:{provider_key}:{kind}:{digest}:{page}"


def load_shelf(provider: ModuleType, kind: str, query: str, page: int = 1) -> Shelf:
    """Search one provider and return page `page` of its loaded shelf.

    A successful search is cached for SEARCH_CACHE_SECONDS. A ProviderError
    becomes the shelf's error message. Nothing else is caught: any other
    exception is a bug and should surface as one.
    """
    number = providers_for_kind(kind).index(provider) + 1
    shelf = Shelf(
        key=provider.KEY, name=provider.NAME, kind=kind, query=query, number=number, page=page
    )
    key = search_cache_key(provider.KEY, kind, query, page)
    records = cache.get(key)
    if records is None:
        try:
            records = tuple(provider.search_records(query, kind, limit=PAGE_SIZE, page=page))
        except ProviderError as error:
            record_status(provider, ok=False)
            return replace(shelf, loaded=True, error=str(error))
        record_status(provider, ok=True)
        cache.set(key, records, SEARCH_CACHE_SECONDS)
    return replace(shelf, loaded=True, records=records)
