"""The library's cross-model workflows: saving a provider asset for a member,
and browsing a member's library.

Saving touches both models: the shared Asset (created from the provider on
the first save by anyone, reused after that) and the member's own
SavedAsset. Browsing is filter_library(), shared by the library page and
the API.
"""

from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Any
from urllib.parse import urlencode

from django.core.paginator import Page, Paginator
from django.db import transaction
from django.urls import reverse

from providers import KINDS, PROVIDERS_BY_KEY

from .discover import KIND_TILES, clean_query
from .models import LIBRARY_SORTS, PROVIDER_CHOICES, Asset, SavedAsset


class UnknownProviderError(LookupError):
    """A save named a provider the Toolbox doesn't have."""


def get_or_fetch_asset(provider_key: str, external_id: str) -> Asset:
    """The shared Asset for one provider asset, fetching and storing it the first time.

    A stored Asset is reused without contacting the provider. Otherwise the
    provider's fetch_record() is called once. Raises UnknownProviderError for
    an unknown provider, and lets ProviderError through, in which case
    nothing is stored.
    """
    provider = PROVIDERS_BY_KEY.get(provider_key)
    if provider is None:
        raise UnknownProviderError(provider_key)
    external_id = external_id.strip()
    asset = Asset.objects.filter(provider=provider.KEY, external_id=external_id).first()
    if asset is None:
        asset = Asset.objects.from_record(provider.fetch_record(external_id))
    return asset


def save_to_library(user, provider_key: str, external_id: str) -> tuple[SavedAsset, bool]:
    """Save one provider asset to `user`'s library; return (entry, created).

    The shared Asset comes from get_or_fetch_asset(). A member who already
    has the asset gets their existing entry back with created=False, never a
    second one. A new entry starts as To review with no rating. Raises
    UnknownProviderError or ProviderError, and then saves nothing.
    """
    asset = get_or_fetch_asset(provider_key, external_id)
    with transaction.atomic():
        return SavedAsset.objects.get_or_create(user=user, asset=asset)


# ---------------------------------------------------------------- browsing (Phase 4)

PAGE_SIZE = 12
DEFAULT_SORT = "newest"
# The minimum-rating filter's values, as they arrive in the query string.
MIN_RATINGS = ("1", "2", "3", "4", "5")
# The sort select's options, in the PRD's order; the keys are LIBRARY_SORTS'.
SORT_LABELS = {
    "newest": "Newest saved",
    "oldest": "Oldest",
    "title": "Title A–Z",
    "rating": "Rating, high to low",
}


@dataclass(frozen=True)
class LibraryParams:
    """The library's search, filters, sort and page, tidied from a query string."""

    q: str = ""
    types: tuple[str, ...] = ()
    providers: tuple[str, ...] = ()
    statuses: tuple[str, ...] = ()
    min_rating: int | None = None
    sort: str = DEFAULT_SORT
    page: int = 1

    @property
    def is_filtered(self) -> bool:
        """Whether a search or any filter narrows the library."""
        return bool(self.q or self.types or self.providers or self.statuses or self.min_rating)

    def url(self, page: int | None = None) -> str:
        """The library URL for these parameters (or for another `page` of them).

        Defaults are left out, so the whole library is plain /library/.
        """
        page = self.page if page is None else page
        pairs = [("q", self.q)] if self.q else []
        pairs += [("type", value) for value in self.types]
        pairs += [("provider", value) for value in self.providers]
        pairs += [("status", value) for value in self.statuses]
        if self.min_rating:
            pairs.append(("min_rating", self.min_rating))
        if self.sort != DEFAULT_SORT:
            pairs.append(("sort", self.sort))
        if page > 1:
            pairs.append(("page", page))
        path = reverse("catalog:library")
        return f"{path}?{urlencode(pairs)}" if pairs else path


@dataclass(frozen=True)
class LibraryPage:
    """One page of a member's library, with the tidied parameters behind it."""

    page: Page
    params: LibraryParams

    @property
    def url(self) -> str:
        return self.params.url()

    @property
    def previous_url(self) -> str:
        return self.params.url(self.page.previous_page_number()) if self.page.has_previous() else ""

    @property
    def next_url(self) -> str:
        return self.params.url(self.page.next_page_number()) if self.page.has_next() else ""


@dataclass(frozen=True)
class FilterChip:
    value: str
    label: str
    checked: bool


@dataclass(frozen=True)
class FilterGroup:
    """One group of the side panel's filter chips. `multiple` groups are
    checkboxes (any number on); the others are radios (exactly one)."""

    name: str
    title: str
    multiple: bool
    chips: list[FilterChip]


def filter_groups(params: LibraryParams) -> list[FilterGroup]:
    """The side panel's filter chips, each checked to match `params`."""

    def chips(options, chosen):
        return [FilterChip(value, label, value in chosen) for value, label in options]

    rating = str(params.min_rating or "")
    ratings = [("", "Any")] + [
        (value, f"{value}+" if value != "5" else "5") for value in MIN_RATINGS
    ]
    return [
        FilterGroup(
            "type", "Type", True, chips(((t.key, t.label) for t in KIND_TILES), params.types)
        ),
        FilterGroup("provider", "Provider", True, chips(PROVIDER_CHOICES, params.providers)),
        FilterGroup("status", "Status", True, chips(SavedAsset.Status.choices, params.statuses)),
        FilterGroup("min_rating", "Minimum rating", False, chips(ratings, (rating,))),
    ]


def _values(params: Mapping[str, Any], name: str) -> list[str]:
    """Every value given for `name`, from a QueryDict or a plain dict."""
    if hasattr(params, "getlist"):
        return params.getlist(name)
    value = params.get(name)
    if value is None:
        return []
    return [str(item) for item in value] if isinstance(value, list | tuple) else [str(value)]


def clean_library_params(params: Mapping[str, Any]) -> LibraryParams:
    """Tidy the library's query parameters, falling back to the defaults.

    Unknown filter values are dropped, and the rest keep a fixed order. An
    unknown sort is "newest". A page that isn't a whole number from 1 is
    page 1. None of these is an error.
    """
    rating = (_values(params, "min_rating") or [""])[-1]
    sort = (_values(params, "sort") or [""])[-1]
    page = (_values(params, "page") or [""])[-1]
    return LibraryParams(
        q=clean_query((_values(params, "q") or [""])[-1]),
        types=_known(_values(params, "type"), KINDS),
        providers=_known(_values(params, "provider"), PROVIDERS_BY_KEY),
        statuses=_known(_values(params, "status"), SavedAsset.Status.values),
        min_rating=int(rating) if rating in MIN_RATINGS else None,
        sort=sort if sort in LIBRARY_SORTS else DEFAULT_SORT,
        page=_page_number(page),
    )


def _page_number(raw: str) -> int:
    """A whole page number from 1, or 1. Six digits is far past any library's
    last page, and keeps int() safe from huge input."""
    if raw.isascii() and raw.isdigit() and len(raw) <= 6 and int(raw) >= 1:
        return int(raw)
    return 1


def _known(given: list[str], allowed) -> tuple[str, ...]:
    """The allowed values among `given`, once each, in `allowed`'s order."""
    return tuple(value for value in allowed if value in given)


def filter_library(user, params: Mapping[str, Any]) -> LibraryPage:
    """One page of `user`'s library for the library's query parameters.

    The page and the API both use it. It searches the title, tags and notes
    (q), filters by type, provider, status and min_rating, sorts by one of
    LIBRARY_SORTS and pages by PAGE_SIZE. Bad values fall back to the
    defaults (see clean_library_params), and a page past the end is the last
    page. Only `user`'s own entries are ever returned, and none for a
    signed-out visitor.
    """
    cleaned = clean_library_params(params)
    entries = SavedAsset.objects.for_user(user).select_related("asset")
    if cleaned.q:
        entries = entries.search(cleaned.q)
    if cleaned.types:
        entries = entries.filter(asset__kind__in=cleaned.types)
    if cleaned.providers:
        entries = entries.filter(asset__provider__in=cleaned.providers)
    if cleaned.statuses:
        entries = entries.filter(status__in=cleaned.statuses)
    if cleaned.min_rating:
        entries = entries.filter(rating__gte=cleaned.min_rating)
    page = Paginator(entries.sorted_by(cleaned.sort), PAGE_SIZE).get_page(cleaned.page)
    return LibraryPage(page=page, params=replace(cleaned, page=page.number))
