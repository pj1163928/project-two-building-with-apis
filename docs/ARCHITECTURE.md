# Architecture

The shape of the code and the rules that cut across apps. The PRD
([prd/axcenity-toolbox.md](../prd/axcenity-toolbox.md)) is the full spec.
**This page is an index:** read it, then open only the topic file for the
area you're changing.

## Topic files

| Open… | Before you touch… |
|---|---|
| [architecture/urls.md](architecture/urls.md) | any URL: every route, its access rule and its HTMX reply |
| [architecture/providers.md](architecture/providers.md) | provider clients, `ProviderError`, caching |
| [architecture/discover.md](architecture/discover.md) | Discover's shelves, license filters, drawer, provider status |
| [architecture/library.md](architecture/library.md) | Asset, Tag, SavedAsset, saving, `filter_library()`, review, status history, community rating, files and bundles |
| [architecture/packs.md](architecture/packs.md) | Pack, PackItem, pack services, unlisted links, suggestions, Save and Copy, the pack page |
| [architecture/exports.md](architecture/exports.md) | the export manifest, Download files, licenses, credits, the Attribution center |
| [architecture/home-and-demo.md](architecture/home-and-demo.md) | the public gallery, the orbit hero, `seed_demo` |
| [architecture/api.md](architecture/api.md) | the library and pack APIs, sign-in, API tokens |

## Apps

| App | Owns | Namespace |
|---|---|---|
| `config` | Settings, root URLs, the shell's context processor | — |
| `providers` | API clients for ambientCG, Poly Haven, Openverse (plain Python, not a Django app) | — |
| `accounts` | Sign-up, sign-in, sign-out, profile, settings, theme, download defaults, API token page | `accounts:` |
| `catalog` | Discover, the library, Asset / Tag / SavedAsset / StatusChange, saving, the library API | `catalog:` |
| `packs` | Main page and gallery, Pack / PackItem, builder, picker, pack pages, export, downloads, Attribution center, pack API, demo data | `packs:` |

Service modules hold cross-model workflows: `catalog/library.py` and
`packs/services.py`. Each workflow runs in one transaction.

## Access rules (site and API)

- Signed-out visitors are sent to sign-in on the website (HTMX gets
  `HX-Redirect`, with `next` set to the page they were on, never a POST-only
  URL), and refused with **401** by the API.
- A pk, slug or token the caller may not use returns **404**, never 403.
  That includes private and unlisted packs.
- Read rows only through the scoped managers, never `.objects.all()` or a
  bare `get(pk=)` in a view:
  - entries: `SavedAsset.objects.for_user(user)`
  - packs to change: `Pack.objects.owned_by(user)`
  - packs to read: `Pack.objects.visible_to(user)` (by slug or id) or
    `Pack.objects.shared_by_link(token)`
  - packs listed to others: `Pack.objects.public()`
- No public view, public serializer or export ever shows a SavedAsset's
  notes, rating or status. Pack pages and the pack API never show the
  community rating either.
- A PackItem may only point to a SavedAsset owned by the pack's owner.
- The Toolbox never downloads, hosts or proxies a provider's file. The
  browser fetches and zips (PRD Out of Scope).

The full table is in the PRD under "Acceptance criteria: access rules".
Every rule has a test (see [TESTING.md](TESTING.md)).

## Patterns every app follows

- **Fragment or page:** a view that returns a fragment for HTMX checks
  `request.htmx and not request.htmx.boosted` and also skips
  `request.htmx.history_restore_request`. Everything else gets the full
  page in the same state.
- **Tidy parameters:** `clean_*_params()` never fails. Unknown values are
  dropped, unknown sorts fall back to the default, a bad page is 1 and a
  page past the end is the last. `.url()` builds the tidy URL with
  defaults left out, and the view sends it as `HX-Push-Url`.
- **Autosaving forms** bind only the posted fields and save only those
  (`update_fields`), so two fields saving at once never overwrite each
  other. A bad value is a **400** with one plain sentence, and nothing is
  saved.
- **Validate before a provider call:** provider and ID (1 to 200
  characters) are checked first, so a bad request never reaches the network.
- **Per-member data is never cached:** shared caches hold provider data
  only, and "In library" and the community rating are looked up per request.

## Shared functions

Each has exactly one implementation, used by both the pages and the API.

| Function | Where | Purpose |
|---|---|---|
| `normalize_tag()` | `catalog/tags.py` | The one way to tidy tags: lowercase, trimmed, single spaces; number-only tags dropped (`None`); a plural "s" stripped from the last word unless it ends in "ss" |
| `search_records()` / `fetch_record()` | `providers/*.py` | The Toolbox's provider calls, next to the console's `search()` / `get_details()` ([providers.md](architecture/providers.md)) |
| `load_shelf(provider, kind, query, page, filters)` | `catalog/discover.py` | One page of one shelf, cached, license filters applied |
| `asset_preview(provider_key, external_id)` | `catalog/preview.py` | One Discover result for its drawer; never stores |
| `save_to_library()` / `save_asset()` | `catalog/library.py` | Save a provider asset / a stored Asset for a member, reusing their entry |
| `filter_library(user, params)` | `catalog/library.py` | Library search, filters, sorts, pages of 12, own entries only |
| `add_to_pack(pack, saved_asset)` | `packs/services.py` | Add at the end on the default variant, once per entry; refuses another member's entry |
| `copy_pack(pack, user)` | `packs/services.py` | A private copy on the copier's own entries, in one transaction |
| `suggest_assets(pack, limit)` | `packs/suggestions.py` | Stored Assets ranked by shared tags, never the pack's own |
| `build_manifest(pack, *, source_url, exported_at=None)` | `packs/manifest.py` | The Option A export, locked by a golden file |
| `pack_credits(items)` | `packs/credits.py` | Licenses, required and optional credits, warnings, the formal notice |
| `license_info(name)` | `catalog/licenses.py` | What a license allows and asks |
| `filter_public_packs(params)` | `packs/gallery.py` | Gallery search, type filter, sorts, pages of 12, public packs only |
| `hero_orbit(rng=None)` | `packs/hero.py` | The main page's orbit of textures from public packs only |
| `seed_demo(snapshot=None)` | `packs/demo.py` | Demo members, libraries and packs, offline and idempotent |
| `rotate_token(user)` | `accounts/tokens.py` | Replace a member's API token; the old key stops at once |
