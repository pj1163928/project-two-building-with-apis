"""The library's cross-model workflows: saving a provider asset for a member,
and browsing a member's library.

Saving touches both models: the shared Asset (created from the provider on
the first save by anyone, reused after that) and the member's own
SavedAsset. Browsing is filter_library(), shared by the library page and
the API.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from typing import Any
from urllib.parse import urlencode

from django.core.paginator import Page, Paginator
from django.db import transaction
from django.db.models import Count, Prefetch
from django.urls import reverse

from providers import KINDS, PROVIDERS_BY_KEY

from .discover import KIND_TILES, clean_query, discover_url
from .files import Bundle
from .filters import FilterChip, FilterGroup
from .licenses import CREDIT_LABELS, LICENSE_ORDER, LICENSES, license_info, license_key
from .models import LIBRARY_SORTS, PROVIDER_CHOICES, Asset, SavedAsset, StatusChange, Tag
from .tags import normalize_tag


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


def save_to_library(
    user,
    provider_key: str,
    external_id: str,
    *,
    via: str = StatusChange.Via.SITE,
    status_reason: str = "",
    **review: Any,
) -> tuple[SavedAsset, bool]:
    """Save one provider asset to `user`'s library; return (entry, created).

    The shared Asset comes from get_or_fetch_asset(). A member who already
    has the asset gets their existing entry back untouched with
    created=False, never a second one. A new entry starts as To review with
    no rating, unless `review` gives its notes, rating or status (the API's
    create). Its first status is recorded as set by `user`, from `via`, with
    the optional `status_reason`. Raises UnknownProviderError or
    ProviderError, and then saves nothing.
    """
    asset = get_or_fetch_asset(provider_key, external_id)
    return save_asset(user, asset, via=via, status_reason=status_reason, **review)


def save_asset(
    user,
    asset: Asset,
    *,
    via: str = StatusChange.Via.SITE,
    status_reason: str = "",
    **review: Any,
) -> tuple[SavedAsset, bool]:
    """Save an Asset that's already stored to `user`'s library; return (entry, created).

    It never contacts a provider. An entry the member already has comes back
    untouched with created=False. A new one starts as To review with no
    rating (unless `review` says otherwise), its first status recorded as set
    by `user` from `via`. The entry and its status record share one
    transaction.
    """
    with transaction.atomic():
        entry, created = SavedAsset.objects.get_or_create(user=user, asset=asset, defaults=review)
        if created:
            entry.status_changes.create(
                status=entry.status, changed_by=user, via=via, reason=status_reason
            )
        return entry, created


def status_history() -> Prefetch:
    """Entries' status changes, newest first, with who made each: the prefetch behind
    SavedAsset.latest_status_change and the drawer's history."""
    return Prefetch("status_changes", StatusChange.objects.select_related("changed_by"))


def bundle_manifest(entry: SavedAsset, bundle: Bundle) -> dict[str, Any] | None:
    """What the drawer's "Download bundle" needs, as JSON for the browser, or None
    when there's nothing to bundle.

    The browser fetches each file from the provider's URL and zips them with
    a CREDITS.txt (static/js/bundle-download.js); the Toolbox never touches
    the files. `credits` holds the license and attribution, so a CC BY
    asset's credit travels with it.
    """
    if not bundle.files or bundle.too_large:
        return None
    asset = entry.asset
    facts = [
        asset.title,
        f"By {asset.author}" if asset.author else "",
        f"From {asset.get_provider_display()}: {asset.source_url}" if asset.source_url else "",
        f"License: {asset.license}" + (f" ({asset.license_url})" if asset.license_url else ""),
        f"Attribution: {asset.attribution}" if asset.attribution else "",
        f"Files: {bundle.variant.label}" if bundle.variant else "",
    ]
    footer = "Bundled by Axcenity Toolbox. The files come straight from the provider."
    credits = "\n".join([*(fact for fact in facts if fact), "", footer, ""])
    return {
        "zip_name": bundle.zip_name(asset.external_id),
        "provider": asset.get_provider_display(),
        "files": bundle.manifest(asset.external_id),
        "credits": credits,
    }


# ------------------------------------------------- one entry's related assets and packs

# How many similar entries the entry's page and drawer list.
SIMILAR_LIMIT = 6
# How many of the asset's tags go into its "Find more on Discover" search.
FIND_MORE_TAGS = 2


@dataclass(frozen=True)
class EntryRelated:
    """What sits around one library entry: the member's own similar entries,
    the public packs featuring its asset, and a Discover search for more."""

    similar: list[SavedAsset]
    public_packs: list[Any]
    find_more_url: str


def entry_related(user, entry: SavedAsset) -> EntryRelated:
    """The entry's similar entries, the public packs featuring it, and a Discover link.

    Similar entries come from `user`'s own library only (most shared tags,
    then the same kind). Public packs are other members' packs that hold the
    same asset; private packs never show. The Discover search uses the
    asset's most widely used tags (or its title, when it has none).
    """
    from packs.models import Pack  # packs depends on catalog, so import it late

    asset = entry.asset
    # Counted over every asset, not through asset.tags (whose join would count only this one).
    tags = (
        Tag.objects.filter(pk__in=asset.tags.values("pk"))
        .annotate(assets_using=Count("assets"))
        .order_by("-assets_using", "name")
        .values_list("name", flat=True)[:FIND_MORE_TAGS]
    )
    query = " ".join(tags) or asset.title
    return EntryRelated(
        similar=SavedAsset.objects.for_user(user).similar_to(entry, SIMILAR_LIMIT),
        public_packs=list(Pack.objects.public_featuring(asset, exclude_owner=user)),
        find_more_url=discover_url(asset.kind, query),
    )


# ---------------------------------------------------------------- browsing (Phase 4)

PAGE_SIZE = 12
DEFAULT_SORT = "newest"
# The minimum-rating filter's values, as they arrive in the query string.
MIN_RATINGS = ("1", "2", "3", "4", "5")
# The side panel lists this many of the member's most used tags (plus any chosen),
# showing the first TAG_CHIPS_SHOWN and folding the rest behind "Show N more".
TAG_CHIP_LIMIT = 48
TAG_CHIPS_SHOWN = 8
# Only this many tag filters are read from one query string.
MAX_TAG_FILTERS = 10
# The sort select's options, in the PRD's order; the keys are LIBRARY_SORTS'.
SORT_LABELS = {
    "newest": "Newest saved",
    "oldest": "Oldest",
    "title": "Title A–Z",
    "rating": "Rating, high to low",
    "community": "Community rating",
}


@dataclass(frozen=True)
class LibraryParams:
    """The library's search, filters, sort and page, tidied from a query string."""

    q: str = ""
    types: tuple[str, ...] = ()
    providers: tuple[str, ...] = ()
    statuses: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    min_rating: int | None = None
    sort: str = DEFAULT_SORT
    page: int = 1

    @property
    def is_filtered(self) -> bool:
        """Whether a search or any filter narrows the library."""
        return bool(
            self.q or self.types or self.providers or self.statuses or self.tags or self.min_rating
        )

    def url(self, page: int | None = None) -> str:
        """The library URL for these parameters (or for another `page` of them).

        Defaults are left out, so the whole library is plain /library/.
        """
        query = self.query_string(page)
        path = reverse("catalog:library")
        return f"{path}?{query}" if query else path

    def query_string(self, page: int | None = None) -> str:
        """These parameters (or another `page` of them) as a tidy query string,
        defaults left out. The library page and the API share it."""
        page = self.page if page is None else page
        pairs = [("q", self.q)] if self.q else []
        pairs += [("type", value) for value in self.types]
        pairs += [("provider", value) for value in self.providers]
        pairs += [("status", value) for value in self.statuses]
        pairs += [("tag", value) for value in self.tags]
        if self.min_rating:
            pairs.append(("min_rating", self.min_rating))
        if self.sort != DEFAULT_SORT:
            pairs.append(("sort", self.sort))
        if page > 1:
            pairs.append(("page", page))
        return urlencode(pairs)


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


def filter_groups(params: LibraryParams, tags: Iterable[Tag] = ()) -> list[FilterGroup]:
    """The side panel's filter chips, each checked to match `params`.

    `tags` are the member's own tags, most used first, each with its `uses`
    (Tag.objects.in_library). The Tags group lists the first TAG_CHIP_LIMIT,
    plus any chosen tag beyond those, so a chosen chip never disappears. It
    shows the first TAG_CHIPS_SHOWN and folds the rest away.
    """

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
        FilterGroup("tag", "Tags", True, _tag_chips(tags, params.tags), fold=TAG_CHIPS_SHOWN),
    ]


def _tag_chips(tags: Iterable[Tag], chosen: tuple[str, ...]) -> list[FilterChip]:
    tags = list(tags)
    shown = tags[:TAG_CHIP_LIMIT] + [tag for tag in tags[TAG_CHIP_LIMIT:] if tag.name in chosen]
    return [FilterChip(tag.name, tag.name, tag.name in chosen, tag.uses) for tag in shown]


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
        tags=_tags(_values(params, "tag")),
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


def _tags(given: list[str]) -> tuple[str, ...]:
    """The given tag names through normalize_tag(), once each, A–Z. Names that
    normalize to nothing are dropped, and only the first MAX_TAG_FILTERS are read."""
    names = {normalize_tag(value) for value in given[:MAX_TAG_FILTERS]} - {None}
    return tuple(sorted(names))


def _known(given: list[str], allowed) -> tuple[str, ...]:
    """The allowed values among `given`, once each, in `allowed`'s order."""
    return tuple(value for value in allowed if value in given)


def filter_library(
    user,
    params: Mapping[str, Any],
    *,
    exclude_entries: Iterable[int] = (),
    licenses: Iterable[str] | None = None,
) -> LibraryPage:
    """One page of `user`'s library for the library's query parameters.

    The page and the API both use it. It searches the title, tags and notes
    (q), filters by type, provider, status, tag (every chosen tag, whichever
    provider it came from) and min_rating, sorts by one of LIBRARY_SORTS and
    pages by PAGE_SIZE. Each entry carries its asset's community rating
    (SavedAsset.community). Bad values fall back to the
    defaults (see clean_library_params), and a page past the end is the last
    page. `exclude_entries` leaves out those entry ids before paging (the pack
    builder hides what's already in the pack). `licenses`, when given, keeps
    only entries whose license is one of those strings, as the provider wrote
    it (see license_filter(); an empty list matches nothing). Only `user`'s own
    entries are ever returned, and none for a signed-out visitor.
    """
    cleaned = clean_library_params(params)
    entries = (
        SavedAsset.objects.for_user(user)
        .with_community_rating()
        .select_related("asset")
        .prefetch_related("asset__tags", status_history())
    )
    if cleaned.q:
        entries = entries.search(cleaned.q)
    if cleaned.types:
        entries = entries.filter(asset__kind__in=cleaned.types)
    if cleaned.providers:
        entries = entries.filter(asset__provider__in=cleaned.providers)
    if cleaned.statuses:
        entries = entries.filter(status__in=cleaned.statuses)
    if cleaned.tags:
        entries = entries.tagged(cleaned.tags)
    if cleaned.min_rating:
        entries = entries.filter(rating__gte=cleaned.min_rating)
    if licenses is not None:
        entries = entries.filter(asset__license__in=list(licenses))
    exclude = list(exclude_entries)
    if exclude:
        entries = entries.exclude(pk__in=exclude)
    page = Paginator(entries.sorted_by(cleaned.sort), PAGE_SIZE).get_page(cleaned.page)
    return LibraryPage(page=page, params=replace(cleaned, page=page.number))


# ------------------------------------------------- the Attribution center's license filters


@dataclass(frozen=True)
class LicenseChoice:
    """One chip of the Attribution center's filters: a license type or a credit rule."""

    value: str
    label: str
    count: int
    chosen: bool


def library_licenses(user) -> dict[str, int]:
    """Each license in `user`'s library, as the providers wrote it, with its entry count."""
    rows = (
        SavedAsset.objects.for_user(user)
        .values("asset__license")
        .annotate(count=Count("id"))
        .order_by()
    )
    return {row["asset__license"]: row["count"] for row in rows}


def clean_license_params(params) -> tuple[list[str], list[str]]:
    """The chosen license types (`license`, LICENSES keys) and credit rules (`credit`,
    CREDIT_LABELS keys) from the query string, each once, unknown values dropped."""

    def chosen(name: str, allowed) -> list[str]:
        values = params.getlist(name) if hasattr(params, "getlist") else params.get(name, [])
        return [value for value in dict.fromkeys(values) if value in allowed]

    return chosen("license", LICENSES), chosen("credit", CREDIT_LABELS)


def license_filter(user, keys: Iterable[str], credits: Iterable[str]) -> list[str] | None:
    """The licenses in `user`'s library of one of the license types `keys` and one of
    the credit rules `credits`, for filter_library(licenses=); None when neither is
    chosen, so nothing is filtered. A type and a rule must both match when both are
    chosen."""
    keys, credits = set(keys), set(credits)
    if not keys and not credits:
        return None
    return [
        written
        for written in library_licenses(user)
        if (not keys or license_key(written) in keys)
        and (not credits or license_info(written).credit in credits)
    ]


def license_choices(
    user, keys: Iterable[str], credits: Iterable[str]
) -> tuple[list[LicenseChoice], list[LicenseChoice]]:
    """The filter chips for `user`'s library: each license type in it (in the guide's
    order) and each credit rule, with how many entries have it."""
    by_key: dict[str, int] = {}
    by_credit: dict[str, int] = {}
    for written, count in library_licenses(user).items():
        info = license_info(written)
        by_key[info.key] = by_key.get(info.key, 0) + count
        by_credit[info.credit] = by_credit.get(info.credit, 0) + count
    keys, credits = set(keys), set(credits)
    types = [
        LicenseChoice(key, LICENSES[key].name, by_key[key], key in keys)
        for key in LICENSE_ORDER
        if key in by_key
    ]
    rules = [
        LicenseChoice(credit, label, by_credit.get(credit, 0), credit in credits)
        for credit, label in CREDIT_LABELS.items()
    ]
    return types, rules
