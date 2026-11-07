# Discover (server side)

`catalog/discover.py` (`clean_query()`, `clean_kind()`, `clean_filters()`,
`shelf_provider()`, `pending_shelves()`, `load_shelf()`),
`catalog/preview.py`, and `DiscoverView`, `DiscoverShelfView`,
`DiscoverAssetView`. Templates and HTMX:
[../frontend/discover.md](../frontend/discover.md). Provider calls and
caching: [providers.md](providers.md).

## The page

- `DiscoverView` never calls a provider. An unknown `type` falls back to
  textures. It renders one pending shelf per provider, and each shelf
  fetches itself (`hx-trigger="load"`).
- With no `q`, the shelves search a random pick from `FEATURED_QUERIES`
  for the kind (`featured_query()`), so Discover is never empty. The pick
  isn't put in the command bar; `?shuffle=<pick>` chooses a different one.
  Each pick was checked live to fill both of its kind's shelves (ambientCG's
  34 models are all food, hence the model picks).

## A shelf

`DiscoverShelfView` checks in this order, so a bad shelf URL never becomes
a redirect and never reaches a provider:

1. Kind and provider are real and the provider serves the kind, else **404**.
2. The query after `clean_query()` isn't blank, else **400**.
3. `page`, if given, is a whole number from 1 to `MAX_PAGE` (20), else **400**.
4. Only then HTMX: a plain or boosted request redirects to its Discover
   page; an HTMX request gets the fragment.

- `load_shelf()` catches only `ProviderError`, so any other exception
  surfaces as a bug.
- Load more shows when the page came back full (`Shelf.has_more`) and it
  isn't page 20. Each page is cached on its own.
- **Per-member data is never cached:** shelves are shared, so "In library"
  (`SavedAsset.objects.saved_external_ids()`) and community ratings
  (`SavedAsset.objects.community_ratings(provider, external_ids)`) are
  looked up on every request.
- **Provider status** (the status bar) comes from shelf outcomes, with no
  health-check requests. When `load_shelf()` really reaches a provider it
  calls `record_status()` (`ok` or `error`, cached 1 h); a cached shelf
  leaves it alone. `provider_statuses()` feeds the context processor; an
  unused provider is `unknown`. Each loaded shelf sends its status out of
  band.
- **Credits:** each shelf shows its module's `CREDIT` and `HOME_URL`.
- **Sound previews:** `AssetRecord.preview_url` is Openverse's audio `url`
  (often a Freesound preview MP3). The browser streams it from the
  provider; the Toolbox never downloads or proxies it. A stored sound's
  `Asset.preview_url` is its first stored file (read from `variants`), so
  the library and packs play it too.

## License filters

- `clean_filters()` reads `license` (any of `FILTER_LICENSES`: every guide
  license but "unknown") and `commercial=1` into a `DiscoverFilters`.
  `.allowed` is the set of license keys a result may carry: the chosen ones
  (or all), narrowed by Commercial use to licenses whose
  `LicenseInfo.commercial` is `True`.
- The filters ride on every Discover link (`discover_url()`, `shelf_url()`,
  `shuffle_url()`, `Shelf.page_url`).
- In `load_shelf()`: a single-license provider (`LICENSES = ("cc0",)`) is
  searched as usual when its license is allowed, otherwise not asked at all
  (the shelf is `filtered_out`). A mixed provider (`LICENSES = None`,
  Openverse) gets `search_records(..., licenses=keys)`, sent as Openverse's
  `license=` (the Toolbox's keys are Openverse's codes). An empty allowed
  set asks nobody.
- `discover_filter_groups()` builds the side panel's chips with the
  library's `FilterChip` / `FilterGroup` (`catalog/filters.py`).

## Discover's drawer

- `DiscoverAssetView` checks the provider and ID first (`valid_asset_ref()`:
  a known provider, an ID of 1 to 200 characters, the save view's rule),
  **400** otherwise, before any provider call.
- `asset_preview(provider_key, external_id)` gives an `AssetPreview`: the
  stored `Asset` when anyone has saved it (no request), else the provider's
  `fetch_record()`, cached 1 h per (provider, hashed ID). It stores nothing.
- A `ProviderError` renders its message with Retry. HTMX gets the drawer,
  anything else the full page. "In your library" checks the caller's own
  entries only.
- Save from the drawer posts `slot=drawer` to `catalog:save`, which answers
  with the drawer's button (`preview_save.html`) instead of the card's
  corner square.
