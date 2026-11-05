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
| `catalog` | Discover and the library; Asset, Tag and SavedAsset; saving; the library API *(planned)* | `catalog:` |
| `packs` | Home and the public gallery; Pack and PackItem, the builder, export and the pack API *(planned)* | `packs:` |

`config/urls.py` mounts `accounts.urls` at `/accounts/`, and mounts
`catalog.urls` and `packs.urls` at the root.

## Current URLs

| Name | Path | Access |
|---|---|---|
| `packs:home` | `/` | Everyone |
| `catalog:discover` | `/discover/?type=<kind>&q=<query>` | Everyone |
| `catalog:discover_shelf` | `/discover/<kind>/<provider>/?q=<query>&page=<n>` | Everyone (an HTMX fragment; `page` is optional, 1 to 20) |
| `catalog:library` | `/library/?q=&type=&provider=&status=&tag=&min_rating=&sort=&page=` | Members (the controls' HTMX requests get the results fragment) |
| `catalog:save` | `/library/save/` | Members; POST only, with CSRF (an HTMX fragment) |
| `catalog:remove` | `/library/<id>/remove/` | Members, own entries only (anything else is **404**); POST only, with CSRF (HTMX gets the results fragment) |
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

## Library and saving

- **Models** (`catalog/models.py`):
  - `Tag`: a unique, normalized name. `Tag.objects.from_names(names)`
    normalizes, de-duplicates and creates as needed.
  - `Asset`: the shared copy of one provider asset, unique on
    (`provider`, `external_id`). It holds the PRD's fields, with `variants`
    as JSON: `[{"label", "files": [{"url", "filename", "size"}],
    "total_size"}]`. A size the provider doesn't give is `null`.
    `Asset.objects.from_record(record)` stores a fetched `AssetRecord` (tags
    normalized), or returns the row already stored, never overwriting it.
  - `SavedAsset`: one member's entry: `notes`, `rating` (null or 1 to 5, a
    database check), `status` (`SavedAsset.Status`, To review by default)
    and `saved_at`. It's unique on (`user`, `asset`). Its FK to Asset is
    `PROTECT`, so deleting an entry never touches the Asset, and an Asset
    in anyone's library can't be deleted. `SavedAsset.objects.for_user(user)`
    is the only way pages read entries, and it's empty for a visitor.
- **Saving** (`catalog/library.py`, the service module):
  - `get_or_fetch_asset(provider_key, external_id)` reuses a stored Asset
    or calls the provider's `fetch_record()` once. An unknown provider is
    `UnknownProviderError`. A `ProviderError` passes through, and nothing
    is stored.
  - `save_to_library(user, provider_key, external_id)` returns
    `(entry, created)`. Saving an asset the member already has returns
    their entry with `created=False`. The API (Phase 6) uses the same
    functions.
- **The save URL** (`SaveAssetView`) checks the provider and a non-blank ID
  of at most 200 characters (**400** otherwise) before any provider call.
  It replies with the "In library" badge, or with the `ProviderError`
  message and Try again. A signed-out POST is sent to sign-in with `next`
  set to the Discover page it came from (`HX-Current-URL`; an HTMX request
  gets `HX-Redirect`), never to the POST-only URL itself.
- **"In library" on Discover:** shelves are cached for everyone, so the
  shelf view looks up the member's saved IDs among the shelf's records on
  every request (`SavedAsset.objects.saved_external_ids()`).
- **The library page** lists the member's entries from stored Assets
  only, so it works with every provider down. It's all one URL,
  `/library/`, read through `filter_library()` (below).
- **Browsing** (`catalog/library.py`):
  - `filter_library(user, params)` returns a `LibraryPage`: one Django
    `Page` of 12 and the tidied `LibraryParams` behind it. It starts from
    `SavedAsset.objects.for_user(user)`, so no parameter can reach another
    member's entries, and a visitor gets none. The API (Phase 6) calls it
    with `request.query_params`; it takes a QueryDict or a plain dict.
  - **Parameters:** `q`, `type`, `provider`, `status` and `tag` (each may
    repeat), `min_rating` (1 to 5), `sort` (`newest`, the default, `oldest`,
    `title`, `rating`) and `page`.
  - **Tags** *(Phase 4 polish, 2026-11-05, at the user's request)*: `tag`
    keeps entries whose asset has **every** chosen tag
    (`SavedAssetQuerySet.tagged()`, one subquery per tag, so no entry is
    listed twice). Tags are stored normalized, so one tag gathers the same
    word from all three providers. Each value goes through `normalize_tag()`
    (a hand-typed "Bricks" finds "brick"); only the first 10 are read, and
    they're kept A–Z. `Tag.objects.in_library(user)` lists the member's own
    tags with `uses` (how many of their entries carry each), most used
    first; `filter_groups()` turns the first 24, plus any chosen beyond
    those, into the side panel's Tags chips.
  - `clean_library_params()` tidies them and never fails: unknown filter
    values are dropped, an unknown sort is `newest`, a page that isn't a
    whole number from 1 is 1, and a page past the end is the last page.
  - **Search** (`SavedAssetQuerySet.search()`): every word must match the
    title, a tag or the member's notes, ignoring case. A word goes through
    `normalize_tag()` before it's matched against tags, so "bricks" finds
    "brick". Tags match through a subquery, so an entry is never listed
    twice.
  - **Sorts** (`LIBRARY_SORTS` in `catalog/models.py`, applied by
    `sorted_by()`): title A–Z ignores case; rating puts unrated entries
    last. Every sort ends on newest saved and then id, so pages never
    shift.
  - `LibraryParams.url(page=None)` builds the tidy URL, leaving out
    defaults, so the whole library is plain `/library/`. `LibraryPage`
    has `url`, `previous_url` and `next_url`. `filter_groups()` gives the
    side panel's chips, checked to match.
- **`LibraryView`** answers the controls' HTMX requests
  (`request.htmx`, not boosted, not a history restore) with
  `catalog/partials/library_results.html` and an `HX-Push-Url` header
  holding the tidy URL. A boosted request and a history restore (Back
  after a swap) get the whole page. A signed-out fragment request gets
  `HX-Redirect` to sign-in with `next` set to the full library URL, so
  the sign-in page never lands inside the results.
- **Remove** *(Phase 4 polish)*: `RemoveFromLibraryView` deletes one of the
  member's own entries (`get_object_or_404` over `for_user()`, so anything
  else is a 404). The shared Asset stays (`PROTECT`). An HTMX request gets
  `library_results.html` again for the view it came from: the parameters
  are read from `HX-Current-URL`, but only when that's a library URL, and
  `HX-Replace-Url` keeps the address bar right when the page shrinks away.
  The saved count comes along out of band. A plain POST redirects to the
  library. A signed-out visitor goes to sign-in and back to the library.
  Phase 7 adds the list of packs the entry leaves, and Phase 6 the API's
  DELETE.
- **Saved count:** `config.context_processors.shell` adds `saved_count`
  (the member's own entries) for signed-in members only.

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
the API. `normalize_tag()`, `filter_library()`, `search_records()` and `fetch_record()` are built; the rest are *(planned)*:

| Function | Purpose |
|---|---|
| `normalize_tag()` | Built (Phase 3), `catalog/tags.py`. The one way to tidy tag names: lowercase, trimmed, single spaces; number-only tags dropped; a plural "s" stripped from the last word unless it ends in "ss". Returns `None` for a dropped tag |
| `filter_library(user, params)` | Built (Phase 4), `catalog/library.py`. Library search (title, tags, notes), filters (type, provider, status, tags, minimum rating), sorts and pages of 12, for the caller's own entries only (see "Library and saving") |
| `filter_public_packs(params)` | Gallery search, type filter, sorts, pages of 12 |
| `add_to_pack(pack, saved_asset)` | Adds an item and enforces ownership |
| Manifest builder | The Option A export shape, locked by a golden file |
| `search_records()` | Built (Phase 2a). Returns `AssetRecord`s (`providers/records.py`), next to the console's `search()` |
| `fetch_record()` | Built (Phase 3). One asset's full `AssetRecord` with its `variants`, next to the console's `get_details()`. ambientCG: one variant per download zip. Poly Haven: `_cached_info()` plus `/files`, keeping every URL; loose maps grouped by resolution and format ("2K JPG"), and each bundle (glTF, Blend…) its own variant with its included files. Openverse: the main file, then one per other file type. An ID that isn't a plain slug is refused before any request |

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
  `get_details()` keep calling `_info()` directly. `fetch_record()` uses
  `_cached_info()` too; its `/files` request isn't cached.
- **Provider status** is kept for 1 h (see Discover).
- **Failures are never cached:** a `ProviderError` returns before anything
  is stored, so Retry always reaches the provider again.

Tests clear the cache around every test.
