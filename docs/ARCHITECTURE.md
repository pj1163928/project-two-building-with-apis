# Architecture

How the Toolbox is put together. The PRD
([prd/axcenity-toolbox.md](../prd/axcenity-toolbox.md)) is the full
specification. This page covers the shape of the code and the rules that
cut across apps. Sections marked *(planned)* describe code that later plan
phases add.

## Apps

| App | Owns | URL namespace |
|---|---|---|
| `config` | Settings, root URLs, the shell's context processor | — |
| `providers` | API clients for ambientCG, Poly Haven and Openverse (plain Python, not a Django app) | — |
| `accounts` | Sign-up, sign-in, sign-out, profile, settings, and the API token page *(planned)* | `accounts:` |
| `catalog` | Discover and the library; Asset, Tag and SavedAsset *(planned)*; the library API *(planned)* | `catalog:` |
| `packs` | Home and the public gallery; Pack and PackItem, the builder, export and the pack API *(planned)* | `packs:` |

`config/urls.py` mounts `accounts.urls` at `/accounts/`, and mounts
`catalog.urls` and `packs.urls` at the root.

## Current URLs

| Name | Path | Access |
|---|---|---|
| `packs:home` | `/` | Everyone |
| `catalog:discover` | `/discover/?type=<kind>&q=<query>` | Everyone |
| `catalog:discover_shelf` | `/discover/<kind>/<provider>/?q=<query>&page=<n>` | Everyone (an HTMX fragment; `page` is optional, 1 to 20) |
| `catalog:library` | `/library/` | Members |
| `packs:list` | `/packs/` | Members |
| `accounts:signup` | `/accounts/signup/` | Everyone (members are sent home) |
| `accounts:login` | `/accounts/login/` | Everyone |
| `accounts:logout` | `/accounts/logout/` | POST only, with CSRF |
| `accounts:profile` | `/accounts/profile/` | Members |
| `accounts:settings` | `/accounts/settings/` | Members |

Planned additions: `/library/<id>/`, `/packs/<slug>/` (slugs are unique
site-wide), and `/api/library/`, `/api/packs/` and `/api/packs/{id}/export/`.

## Discover

- **Kinds:** one vocabulary everywhere: `texture`, `hdri`, `model`, `sound`
  (`providers.KINDS`). The same words go in `?type=`, in shelf URLs, and
  later in `Asset.kind` and the manifest.
- **The mapping** lives with the providers. Each module's `KIND_FILTERS`
  maps the kinds it serves to its own filter value, and
  `providers_for_kind(kind)` returns the matching modules in shelf order.
- **The page** (`DiscoverView`) never calls a provider. An unknown `type`
  falls back to textures. It renders one pending shelf per provider, and
  each shelf fetches itself (`hx-trigger="load"`). With no `q`, the
  shelves search a random pick from `FEATURED_QUERIES` for the kind
  (`featured_query()`), so Discover is never empty. The pick isn't put in
  the command bar. Shuffle (`?shuffle=<pick>`) chooses a different one.
  Each pick was checked live to fill both of its kind's shelves
  (ambientCG's 34 models are all food, hence the model picks).
- **A shelf** (`DiscoverShelfView`) checks things in this order:
  1. The kind and provider must be real, and the provider must serve that
     kind. Otherwise **404**.
  2. The query, after `clean_query()`, must not be blank. Otherwise
     **400**.
  3. `page`, if given, must be a whole number from 1 to `MAX_PAGE` (20).
     Otherwise **400**.
  4. Only then does it look at HTMX. A plain or boosted request redirects
     to its Discover page. An HTMX request gets the fragment.

  So a bad shelf URL never becomes a redirect, and never reaches a
  provider.
- **Load more:** each `search_records(query, kind, limit=12, page=1)` takes
  a 1-based page. ambientCG sends `offset`, and Openverse sends `page` and
  returns nothing past its anonymous depth of 240 without asking. Poly
  Haven's `/search` has no offset, so page N asks for N x 12 hits, keeps
  the last 12 and fetches `/info` only for those. Pages after the first
  stop at `keywordMatches`, so Load more never shows unrelated semantic
  guesses. A shelf offers Load more when its page came back full
  (`Shelf.has_more`) and it isn't page 20. Each page is cached on its own.
- **Sound previews:** `AssetRecord.preview_url` is Openverse's audio `url`
  (often a Freesound preview MP3). The browser streams it from the
  provider; the Toolbox never downloads or proxies it. Other kinds leave
  it blank.
- `catalog/discover.py` holds this logic: `clean_query()`, `clean_kind()`,
  `shelf_provider()`, `pending_shelves()` and `load_shelf()`. `load_shelf()`
  catches only `ProviderError`, so any other exception still surfaces as a
  bug.
- **Provider status** (the status bar) comes from shelf outcomes, with no
  health-check requests. When `load_shelf()` actually reaches a provider, it
  calls `record_status()`, which stores `ok` or `error` in the cache for 1 h.
  A shelf served from the search cache leaves the status alone.
  `provider_statuses()` reads every provider's status for the context
  processor, and a provider no shelf has used yet is `unknown`. Each loaded
  shelf also sends its provider's status out of band (see FRONTEND.md).
- **Credits:** each provider module has a `CREDIT` line and a `HOME_URL`,
  which every shelf shows.

## Authentication

- Django's `LoginView` and `LogoutView`. `LogoutView` accepts only POST,
  so a GET returns 405.
- `accounts.views.SignUpView` is built on `UserCreationForm`. It signs the
  new member in and honours a same-site `next`.
- `LOGIN_URL = "accounts:login"`. `LoginRequiredMixin` adds `?next=` so the
  member comes back after signing in.
- `LOGIN_REDIRECT_URL` and `LOGOUT_REDIRECT_URL` both point to `packs:home`.
- *(planned)* The API uses DRF `SessionAuthentication` (CSRF still applies)
  and `TokenAuthentication` (`Authorization: Token <key>`, no CSRF).

## Access rules (apply to site and API)

- Signed-out visitors are sent to sign-in on the website, and refused with
  401/403 by the API.
- A pk or slug the caller doesn't own returns **404**. That includes
  private packs.
- No public view, public serializer or export ever shows a SavedAsset's
  notes, rating or status.
- A PackItem may only point to a SavedAsset owned by the pack's owner.

The full table is in the PRD under "Acceptance criteria: access rules".
Every rule has a test (see [TESTING.md](TESTING.md)).

## Shared functions

Each of these has exactly one implementation, used by both the pages and
the API. All but `search_records()` are *(planned)*:

| Function | Purpose |
|---|---|
| `normalize_tag()` | The one way to tidy tag names |
| `filter_library(user, params)` | Library search, filters, sorts, pages of 12 |
| `filter_public_packs(params)` | Gallery search, type filter, sorts, pages of 12 |
| `add_to_pack(pack, saved_asset)` | Adds an item and enforces ownership |
| Manifest builder | The Option A export shape, locked by a golden file |
| `search_records()` | Built (Phase 2a). Returns `AssetRecord`s (`providers/records.py`), next to the console's `search()` |
| `fetch_record()` | Provider details for saving (Phase 3), next to the console's `get_details()` |

## Provider errors

- Every failure in `get_json()` is a `ProviderError` whose message is safe
  to show users. It may name the provider and an HTTP status, but never
  includes exception text, a response body or a header value.
  `Retry-After` is repeated only when it's a plain number of seconds.
- The details go to the `providers` logger as a warning: the exception, the
  URL, the status and the first 300 characters of the body.
  `config/settings.py` sends that logger to the server console. The
  package adds a `NullHandler`, so the console script, which sets up no
  logging, stays quiet.
- A response of the wrong shape becomes "<provider> sent back results the
  Toolbox couldn't read." A malformed item is skipped.
- Poly Haven cuts its search hits to the limit before calling `/info`, so
  a search makes at most 12 `/info` requests.

## Caching

Django's local-memory cache (`CACHES` in settings):

- **Searches** are cached for 1 h per (provider, kind, normalized query), in
  `load_shelf()`. `search_cache_key()` builds the key from the
  `clean_query()` text, case-folded and hashed, so searches that differ only
  in case or spacing share an entry. The provider is sent the first search's
  cleaned query.
- **Poly Haven info** is cached for 12 h (`polyhaven.INFO_CACHE_SECONDS`).
  `providers` is plain Python, so it never imports Django. Instead
  `providers/cache.py` offers `use_cache()` and `remember()`, and
  `CatalogConfig.ready()` installs Django's cache. The console script
  installs none, so it caches nothing. Every Toolbox lookup goes through
  `polyhaven._cached_info()`, while the console's `search()` and
  `get_details()` keep calling `_info()` directly. *(Phase 3's
  `fetch_record()` must use `_cached_info()` too.)*
- **Provider status** is kept for 1 h (see Discover).
- **Failures are never cached:** a `ProviderError` returns before anything
  is stored, so Retry always reaches the provider again.

Tests clear the cache around every test.
