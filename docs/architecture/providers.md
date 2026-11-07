# Providers, errors and caching

`providers/` is plain Python, not a Django app, so the Project 1 console
script keeps working. How the console path works:
[../code-walkthrough.md](../code-walkthrough.md). Each API's terms, limits
and quirks: [../research/game-asset-apis.md](../research/game-asset-apis.md)
(read only the provider's section).

## Two APIs per module

- **Console (never change):** `search()` and `get_details()`, with `NAME`
  and `TYPE_FILTERS`. `PROVIDERS = [ambientcg, polyhaven, openverse]`.
- **Toolbox (sits next to them):**
  - `search_records(query, kind, limit=12, page=1)` returns `AssetRecord`s
    (`providers/records.py`). Openverse's also takes `licenses=`.
  - `fetch_record(external_id)` returns one full `AssetRecord` with
    `variants`. ambientCG: one variant per download zip. Poly Haven:
    `_cached_info()` plus `/files`, every URL kept; loose maps grouped by
    resolution and format ("2K JPG"), each bundle (glTF, Blend…) its own
    variant with its included files. Openverse: the main file, then one per
    other file type. An ID that isn't a plain slug is refused before any
    request.
- **Module constants:** `KIND_FILTERS` (kind → the provider's filter
  value), `CREDIT`, `HOME_URL`, and `LICENSES`: `("cc0",)` for a provider
  whose assets all carry one license (ambientCG, Poly Haven), `None` for
  mixed (Openverse).
- **Kinds:** one vocabulary everywhere, `providers.KINDS` = `texture`,
  `hdri`, `model`, `sound`: in `?type=`, shelf URLs, `Asset.kind` and the
  manifest. `providers_for_kind(kind)` returns the modules in shelf order.

## Paging (Load more)

- ambientCG sends `offset`. Openverse sends `page` and returns nothing past
  its anonymous depth of 240.
- Poly Haven's `/search` has no offset: page N asks for N × 12 hits, keeps
  the last 12 and fetches `/info` only for those. Pages after the first
  stop at `keywordMatches`, so Load more never shows unrelated semantic
  guesses. A search makes at most 12 `/info` requests.

## Errors

- All HTTP goes through `get_json()`. Every failure is a `ProviderError`
  whose message is safe to show: it may name the provider and an HTTP
  status, never exception text, a response body or a header value.
  `Retry-After` is repeated only when it's a plain number of seconds.
- Details go to the `providers` logger as a warning (exception, URL,
  status, first 300 characters of the body). `config/settings.py` sends it
  to the server console; the package adds a `NullHandler`, so the console
  script stays quiet.
- A response of the wrong shape becomes "<provider> sent back results the
  Toolbox couldn't read." A malformed item is skipped.

## Caching

Django's local-memory cache (`CACHES`). Tests clear it around every test.

- **Searches:** 1 h per (provider, kind, normalized query) in
  `load_shelf()`. `search_cache_key()` hashes the case-folded
  `clean_query()` text, so searches differing only in case or spacing share
  an entry. Openverse with license filters adds the allowed licenses to the
  key (`DiscoverFilters.cache_part`); a CC0-only provider shares the
  unfiltered entry.
- **Poly Haven `/info`:** 12 h (`polyhaven.INFO_CACHE_SECONDS`).
  `providers` never imports Django: `providers/cache.py` offers
  `use_cache()` and `remember()`, and `CatalogConfig.ready()` installs
  Django's cache. The console installs none, so it caches nothing. Toolbox
  lookups go through `polyhaven._cached_info()`; the console's `search()`
  and `get_details()` still call `_info()`. `/files` isn't cached.
- **Discover's drawer:** each fetched record 1 h
  (`preview.PREVIEW_CACHE_SECONDS`, `preview_cache_key()`).
- **Provider status:** 1 h (see [discover.md](discover.md)).
- **Failures are never cached:** a `ProviderError` returns before anything
  is stored, so Retry always reaches the provider again.
