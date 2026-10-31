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
| `catalog:discover` | `/discover/` | Everyone |
| `catalog:library` | `/library/` | Members |
| `packs:list` | `/packs/` | Members |
| `accounts:signup` | `/accounts/signup/` | Everyone (members are sent home) |
| `accounts:login` | `/accounts/login/` | Everyone |
| `accounts:logout` | `/accounts/logout/` | POST only, with CSRF |
| `accounts:profile` | `/accounts/profile/` | Members |
| `accounts:settings` | `/accounts/settings/` | Members |

Planned additions: `/library/<id>/`, `/packs/<slug>/` (slugs are unique
site-wide), Discover's per-shelf fragment URLs, and `/api/library/`,
`/api/packs/` and `/api/packs/{id}/export/`.

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

## Shared functions *(planned)*

Each of these has exactly one implementation, used by both the pages and
the API:

| Function | Purpose |
|---|---|
| `normalize_tag()` | The one way to tidy tag names |
| `filter_library(user, params)` | Library search, filters, sorts, pages of 12 |
| `filter_public_packs(params)` | Gallery search, type filter, sorts, pages of 12 |
| `add_to_pack(pack, saved_asset)` | Adds an item and enforces ownership |
| Manifest builder | The Option A export shape, locked by a golden file |
| `search_records()` / `fetch_record()` | Provider record functions, next to the console's `search()` / `get_details()` |

## Caching

Django's local-memory cache (`CACHES` in settings):

- Searches are cached for 1 h per (provider, kind, normalized query).
- Poly Haven info is cached for 12 h.
- Failures are never cached.

Tests clear the cache around every test.
