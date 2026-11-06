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
| `accounts` | Sign-up, sign-in, sign-out, profile, settings, and the API token page | `accounts:` |
| `catalog` | Discover (its shelves, license filters and drawer) and the library; Asset, Tag and SavedAsset; saving; the library API | `catalog:` |
| `packs` | The main page and its public gallery; Pack and PackItem, the member's packs, the builder and the Add to pack picker; each pack's page, its export and the pack API; the demo data (`seed_demo`) | `packs:` |

`config/urls.py` mounts `accounts.urls` at `/accounts/`, and mounts
`catalog.urls` and `packs.urls` at the root.

## Current URLs

| Name | Path | Access |
|---|---|---|
| `packs:home` | `/?q=&type=&sort=&page=` | Everyone: the main page and the public gallery (public packs only). The gallery's HTMX requests get the results fragment |
| `catalog:discover` | `/discover/?type=<kind>&q=<query>&license=<key>&commercial=1` | Everyone (`license` repeats; both filters are optional) |
| `catalog:discover_shelf` | `/discover/<kind>/<provider>/?q=<query>&page=<n>&license=&commercial=` | Everyone (an HTMX fragment; `page` is optional, 1 to 20; the filters as on the page) |
| `catalog:discover_asset` | `/discover/asset/<provider>/<external_id>/` | Everyone (Discover's drawer for HTMX, a page otherwise; never writes) |
| `catalog:library` | `/library/?q=&type=&provider=&status=&tag=&min_rating=&sort=&page=` | Members (the controls' HTMX requests get the results fragment) |
| `catalog:save` | `/library/save/` | Members; POST only, with CSRF (an HTMX fragment) |
| `catalog:entry` | `/library/<id>/` | Members, own entries only (anything else is **404**). The library's HTMX request gets the drawer; any other request gets the full page |
| `catalog:update` | `/library/<id>/update/` | Members, own entries only (**404** otherwise); POST only, with CSRF. Saves whichever of `status`, `rating`, `notes` is posted |
| `catalog:remove` | `/library/<id>/remove/` | Members, own entries only (anything else is **404**). GET is the confirm listing the packs it will leave (the library's dialog for HTMX, a page otherwise); POST removes it, with CSRF (HTMX gets the results fragment) |
| `catalog:api_library` | `/api/library/` | API: signed in by token or session (401 otherwise). GET lists the caller's entries; POST saves one |
| `catalog:api_entry` | `/api/library/<id>/` | API: the caller's own entries only (**404** otherwise). GET, PATCH, PUT, DELETE |
| `packs:list` | `/packs/?layout=grid\|list` | Members: their own packs (`layout` is optional and remembered in the session) |
| `packs:create` | `/packs/new/` | Members; POST with CSRF creates a private pack and opens its builder |
| `packs:builder` | `/packs/<id>/edit/` | The owner only (**404** otherwise) |
| `packs:details`, `packs:visibility`, `packs:delete` | `/packs/<id>/details/`, `…/visibility/`, `…/delete/` | The owner only; POST only, with CSRF. Details saves whichever of `title`, `description`, `tags` is posted; visibility takes `private`, `unlisted` or `public` |
| `packs:library_search` | `/packs/<id>/library/?q=` | The owner only; the builder's Add from my library fragment (any other request goes to the builder) |
| `packs:add_item` | `/packs/<id>/items/` | The owner only; POST `entry` (their own, **404** otherwise), with CSRF |
| `packs:suggestions` | `/packs/<id>/suggestions/` | The owner only (**404** otherwise); the builder's Suggested for this pack fragment, with Find more (any other request goes to the builder) |
| `packs:suggestion_add` | `/packs/<id>/suggestions/add/` | The owner only (**404** otherwise); POST `asset` (a stored Asset's id, **404** when unknown), with CSRF. Saves it to the owner's library as To review when needed, then adds it; never calls a provider |
| `packs:item_update`, `packs:item_move`, `packs:item_remove` | `/packs/<id>/items/<item>/`, `…/move/`, `…/remove/` | The owner only; POST only, with CSRF. Update saves whichever of `preferred_variant`, `import_path` is posted; move takes `direction` `up` or `down` |
| `packs:picker` | `/packs/picker/?entry=<id>` or `?provider=&external_id=` | Members; the Add to pack picker's list of their own packs |
| `packs:picker_add` | `/packs/<id>/add/` | The owner only; POST `entry`, or `provider` and `external_id` (a Discover result), with CSRF |
| `packs:public` | `/packs/<slug>/` | Everyone for a public pack; the owner only for a private or unlisted one (**404** otherwise). Read-only; the owner also gets Edit in builder |
| `packs:export` | `/packs/<slug>/export/` | As `packs:public`. GET only: the manifest as a download, `<slug>.axcenity-pack.json` |
| `packs:shared`, `packs:shared_export` | `/packs/link/<token>/`, `…/export/` | Anyone holding an unlisted pack's share link (a public pack's link redirects to its page). A replaced token, a private pack's or an unknown one is a **404**. `X-Robots-Tag: noindex, nofollow` |
| `packs:save_item`, `packs:shared_save_item` | `/packs/<slug>/items/<item>/save/`, `/packs/link/<token>/items/<item>/save/` | Members (sent to sign in and back to the pack's page otherwise) who can read the pack, as `packs:public` and `packs:shared` (**404** otherwise; another pack's item is a **404**); POST only, with CSRF. Saves the item's stored Asset to the member's library (To review, or their entry untouched); HTMX gets the item's "In your library" slot, anything else goes back to the page |
| `packs:copy`, `packs:shared_copy` | `/packs/<slug>/copy/`, `/packs/link/<token>/copy/` | As `packs:save_item`. Copy pack: a private copy for the member (`copy_pack()`), then its builder. Website only: the API has no copy URL |
| `packs:rotate_link` | `/packs/<id>/link/` | The owner only; POST only, with CSRF. New link: replaces the share token, so every older link is a **404** |
| `packs:items_reorder`, `packs:items_sort` | `/packs/<id>/items/order/`, `…/items/sort/` | The owner only; POST only, with CSRF. Reorder takes `order` (every item's id once, comma-separated; anything else is a **400** that changes nothing); sort takes `type`, `title`, `provider` or `license` |
| `packs:files`, `packs:shared_files` | `/packs/<slug>/files/`, `/packs/link/<token>/files/` | As `packs:public` and `packs:shared`. GET only: the JSON list Download files zips in the browser (`?item=<id>` for one item; another pack's item is a **404**) |
| `packs:attribution` | `/attribution/` | Everyone: the license guide |
| `packs:attribution_packs` | `/attribution/packs/` | Members: their own packs' licenses |
| `packs:attribution_pack`, `packs:shared_attribution` | `/attribution/packs/<slug>/`, `/packs/link/<token>/attribution/` | As `packs:public` and `packs:shared`: one pack's license terms, credits and notice (a public pack's link redirects; noindex by link) |
| `packs:attribution_assets` | `/attribution/assets/?q=&license=&credit=&page=` | Members: their own library by license; `license` (repeatable, a `LICENSES` key) and `credit` (`required`, `listed`, `optional`); unknown values ignored. The filters' HTMX requests get the results fragment |
| `packs:attribution_asset` | `/attribution/assets/<id>/` | Members, own entries only (**404** otherwise): one asset's license terms, credit and notice |
| `packs:api_packs` | `/api/packs/?mine=&page=` | API, anyone: public packs plus the caller's own, 12 to a page. `?mine=1` lists only the caller's and needs sign-in (**401** otherwise). Read-only (**405** for writes) |
| `packs:api_pack`, `packs:api_pack_export` | `/api/packs/<id>/`, `/api/packs/<id>/export/` | API: anyone for a public pack, the owner only for a private one (**404** otherwise). Read-only (**405** for writes) |
| `accounts:signup` | `/accounts/signup/` | Everyone (members are sent home) |
| `accounts:login` | `/accounts/login/` | Everyone |
| `accounts:logout` | `/accounts/logout/` | POST only, with CSRF |
| `accounts:profile` | `/accounts/profile/` | Members |
| `accounts:settings` | `/accounts/settings/` | Members |
| `accounts:theme` | `/accounts/theme/` | Everyone; POST only, with CSRF. Sets the colour scheme (`choice`: `system`, `light` or `dark`, a **400** otherwise) in the `ax-theme` cookie for a year. HTMX gets a 204; any other request goes back to the Referer when it's this site, otherwise home |
| `accounts:download_preferences` | `/accounts/settings/downloads/` | Members; POST only, with CSRF. Saves whichever download defaults are posted (HTMX gets the status line, a plain POST goes back to Settings) |
| `accounts:token` | `/accounts/token/` | Members; creates the member's API token on the first visit, never cached |

The owner's pack pages use the pk (`/packs/<id>/edit/`), and a pack's own
page uses its slug (`/packs/<slug>/`), which is unique site-wide and never
changes on a rename. `new`, `picker` and `link` are pages under `/packs/`, so
no pack is given those slugs (`RESERVED_SLUGS`; a pack titled "New" is `new-2`).

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
  it blank. A stored sound's `Asset.preview_url` is its first stored file
  (Openverse lists the main audio first), so the library and packs play it
  too (user request, 2026-11-06). No migration: it reads `variants`.
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
- **License filters** (user request, 2026-11-06): `clean_filters()` reads
  `license` (any of `FILTER_LICENSES`: every guide license but "unknown")
  and `commercial=1` into a `DiscoverFilters`. `.allowed` is the set of
  license keys a result may carry: the chosen ones (or all), narrowed by
  Commercial use to licenses whose `LicenseInfo.commercial` is `True`. The
  filters ride on every Discover link (`discover_url()`, `shelf_url()`,
  `shuffle_url()`, `Shelf.page_url`). In `load_shelf()`:
  - A provider whose assets all carry one license declares it
    (`LICENSES = ("cc0",)`: ambientCG and Poly Haven). It's searched as
    usual when that license is allowed, and otherwise not asked at all: the
    shelf is `filtered_out`.
  - A provider with mixed licenses declares `LICENSES = None` (Openverse);
    its `search_records(..., licenses=keys)` sends Openverse's `license=`
    parameter (the Toolbox's keys are Openverse's codes). An empty allowed
    set asks nobody.
  - The cache key gains the allowed licenses for such a provider
    (`DiscoverFilters.cache_part`), so each set is cached apart.
  `discover_filter_groups()` builds the side panel's chips with the
  library's `FilterChip` / `FilterGroup` (`catalog/filters.py`).
- **Discover's drawer** (user request, 2026-11-06): `DiscoverAssetView`
  (`catalog:discover_asset`) checks the provider and ID first
  (`valid_asset_ref()`: a known provider, an ID of 1 to 200 characters, the
  save view's rule), a **400** otherwise, before any provider call. Then
  `catalog/preview.py`'s `asset_preview()` gives an `AssetPreview`: the
  stored `Asset` when anyone has saved it (no request), else the provider's
  `fetch_record()`, cached 1 h per (provider, hashed ID). It stores nothing.
  A `ProviderError` renders its message with Retry. The HTMX request gets
  the drawer, anything else the full page. "In your library" comes from the
  caller's own entries only. Save from the drawer posts `slot=drawer` to
  `catalog:save`, which answers with the drawer's own button
  (`preview_save.html`) instead of the card's corner square.

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
    their entry untouched with `created=False`. Keyword arguments (`notes`,
    `rating`, `status`) set a new entry's review; the API's create passes
    them.
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
    `title`, `rating`, `community`) and `page`.
  - **Tags** *(Phase 4 polish, 2026-11-05, at the user's request)*: `tag`
    keeps entries whose asset has **every** chosen tag
    (`SavedAssetQuerySet.tagged()`, one subquery per tag, so no entry is
    listed twice). Tags are stored normalized, so one tag gathers the same
    word from all three providers. Each value goes through `normalize_tag()`
    (a hand-typed "Bricks" finds "brick"); only the first 10 are read, and
    they're kept A–Z. `Tag.objects.in_library(user)` lists the member's own
    tags with `uses` (how many of their entries carry each), most used
    first; `filter_groups()` turns the first 48 (`TAG_CHIP_LIMIT`), plus any
    chosen beyond those, into the side panel's Tags chips. The group has a
    `fold` of 8 (`TAG_CHIPS_SHOWN`): `lead_chips` always show, `more_chips`
    fold away, and `more_open` is true when a chosen chip is behind the
    fold (user request, 2026-11-05).
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
  *(Phase 7)* A GET on the same URL is the confirm: the entry's title and
  the packs it will leave (its PackItems, A–Z), as the library's Remove
  dialog for HTMX or as a page otherwise. Confirming deletes the entry, and
  its PackItems cascade; the packs' other items and the Asset stay.
- **The drawer** *(Phase 5)*: `/library/<id>/` (`EntryView`) shows one of
  the member's entries: the stored Asset's details, license and
  attribution, source link, tags and file variants, then the member's
  review. Every entry view and update looks the entry up through
  `_own_entry()` (`for_user()` then `get_object_or_404`), so another
  member's entry, or one that doesn't exist, is a 404. A card's title
  `hx-get`s it into the library's drawer (`_wants_fragment()`: HTMX, not
  boosted, not a history restore). A direct visit, a boosted link or a
  history restore gets the full page (`catalog/entry.html`), which is
  what makes the link bookmarkable. Opening the drawer doesn't change the
  address bar; the title is still a real link to the entry, and the
  drawer has "Open as page". A signed-out drawer request gets
  `HX-Redirect` to sign-in and back to the entry.
- **Saving the review** (`UpdateEntryView`, `catalog/forms.py`):
  `ReviewForm` binds only the fields that were posted (the rest at their
  stored values, so they still validate) and saves only those
  (`update_fields`). A notes autosave and a status click therefore never
  overwrite each other. Rating is 1 to 5 or empty (cleared); status is one
  of the four; notes are up to `NOTES_MAX_LENGTH` (10,000) characters,
  kept as typed, with line breaks stored as LF. Bad values, or none of the
  three fields, are a **400** with one plain sentence, and nothing is
  saved. The reply is the status line (`entry_save_status.html`). A status
  or rating change made from the library page (`_from_library()`, read
  from `HX-Current-URL`) also sends the card out of band; notes don't
  show on the card, and the full page has no card. A plain POST redirects
  to the entry's page. A signed-out HTMX save gets a **401** status line
  with a sign-in link that opens in a new tab, instead of `HX-Redirect`,
  so the notes being typed aren't lost (user request, 2026-11-05). A
  plain POST is still sent to sign-in. The API (Phase 6) gets its own
  serializer, with the same rules.
- **Remove from the drawer or the full page:** the drawer's Delete opens the
  library's Remove dialog (`catalog:remove`'s GET), which posts from the
  library page, so it gets the results for the same view. On the full page
  it's a link to the confirm page, whose boosted form is redirected to the
  library like a plain POST.
- **The drawer's packs** *(Phase 7)*: after "License and credit", the packs
  the entry is in (`_own_entry()` prefetches them), each linking to its
  builder, with the item's variant.
- **Community rating** *(user request, 2026-11-05)*: each member's own
  rating stays private, but every page that shows an asset can show the
  average of all members' ratings for it and how many rated it. It never
  shows who rated, or anyone's notes or status.
  - `SavedAssetQuerySet.with_community_rating()` annotates entries with
    `community_rating` (the average, None when no one has rated) and
    `community_count`. Both are subqueries over every member's entries, so
    each entry stays one row. `SavedAsset.community` wraps them as a
    `CommunityRating(average, count)`, or None.
  - `filter_library()` and `_own_entry()` always annotate. The library's
    `community` sort orders by the average (assets no one has rated last),
    then by the count, then newest saved.
  - `SavedAsset.objects.community_ratings(provider, external_ids)` gives
    Discover's shelves the same figures, keyed by external ID. Like
    "In library", they're looked up on every shelf request, not cached.
  - A count of 1 shows that one member's rating, but never whose. The user
    chose to show it from the first rating, not from 3. Pack pages and the
    pack API never show it (Phase 8's sentinel test checks).
- **Saved count:** `config.context_processors.shell` adds `saved_count`
  (the member's own entries) for signed-in members only. It also adds the
  colour scheme for every page: `theme_choice` (from the `ax-theme`
  cookie, through `accounts.theme.theme_choice()`; anything unknown is
  `system`), its label, and the next choice for the title bar's switch.
- **Status history** *(user request, 2026-11-05)*: who set a review status,
  when, where and why. The Toolbox has no teams yet, so today it's always
  the entry's owner (or their API token), but each change names the person,
  ready for when members share work.
  - `StatusChange` (`catalog/models.py`): `entry` (CASCADE), `status`,
    `changed_by` (SET_NULL, "a former member" once deleted), `reason` (up
    to 300 characters), `via` (`site` or `api`) and `changed_at`, newest
    first.
  - `SavedAsset.save_review(fields, by=, via=, reason=)` saves only `fields`
    and, when the status really changes, records it, in one transaction.
    `ReviewForm.save(by=)` and the API's serializer both use it.
    `SavedAsset.explain_status(reason, by=, via=)` puts a reason on the
    latest change when that set the current status (the explainer becomes
    its author), or records the current status with it.
    `latest_status_change` is the record behind the current status, or
    None.
  - `save_to_library()` records a new entry's first status, by the saver,
    with `via` and an optional `status_reason` (the API's create).
  - `status_history()` is the prefetch (changes with `changed_by`) that
    `filter_library()`, `_own_entry()` and the API use.
  - `UpdateEntryView` takes `status_reason` as its own posted field
    (`clean_status_reason()`: spaces collapsed, up to 300 characters, a
    **400** otherwise). It's members only, CSRF, and another member's entry
    is a **404**, like every update.
- **Files and bundles** *(user request, 2026-11-05)*: `catalog/files.py`
  tells an asset's stored variants apart. It has no models and makes no
  requests.
  - `describe_variant()` gives a `VariantInfo`: the resolution ("2K") and
    format ("JPG", "glTF", from the label, or the first file's extension
    when the label has none), the package (`maps`, `bundle`, `archive`,
    `audio`, `files`) and each file's `FileInfo` with its `map_key` and
    role. `map_type(filename, external_id)` reads only the part between the
    asset's ID and the resolution, so "rusty_metal_02_rough_2k.jpg" is
    Roughness, not Metalness. `Asset.file_variants` and
    `Asset.file_filters` (the resolutions and formats, once each) wrap
    them.
  - `pick_bundle(kind, variants, prefs)`: the format first (the member's,
    then `FORMAT_FALLBACKS` for the kind), then the resolution (the
    member's, else the nearest below, else the nearest above). From loose
    maps only the member's map types are kept; a bundle or archive is taken
    whole. `Bundle.notes` says where it had to differ. `Bundle.manifest()`
    puts every file under one folder named for the asset, through
    `safe_path()` (no `..`, no leading `/`, duplicates numbered).
  - `bundle_manifest(entry, bundle)` (`catalog/library.py`) is the JSON the
    drawer's Download bundle reads: the zip's name, the provider, each
    file's URL, path and size, and the credits. None over `BUNDLE_MAX_BYTES`
    (2 GB) or with nothing to bundle. **The member's browser** fetches and
    zips the files; the Toolbox never downloads, hosts or proxies them, so
    the PRD's Out of Scope still holds.
  - `DownloadPreferences` (`accounts/models.py`, one per member): the
    `resolution` (1K–8K, 2K by default), `texture_format` (JPG), `hdri_format`
    (HDR), `model_format` (glTF), `sound_format` (MP3) and `maps` (every
    map type by default). `DownloadPreferences.objects.for_user(user)`
    returns the saved row or the unsaved defaults, so reading never writes.
    `DownloadPreferencesForm` binds and saves only the posted fields, like
    `ReviewForm`; at least one map must stay.
- **Around an entry** *(user request, 2026-11-05)*: `entry_related(user,
  entry)` gives an `EntryRelated`: `similar` (`SavedAssetQuerySet.similar_to()`
  on the member's own entries: most shared tags, then the same kind, then
  newest, up to 6, each with `shared_tags`), `public_packs`
  (`Pack.objects.public_featuring(asset, exclude_owner=user)`: other
  members' public packs holding the asset through anyone's entry, never a
  private one; each links to its page) and `find_more_url` (Discover for the kind and the asset's two
  most widely used tags, or its title). `EntryView` adds it, with the
  member's `preferences`, `bundle` and `bundle_manifest`, to the drawer and
  the page alike.

## Packs

*(Phase 7.)* `packs/models.py`, `packs/services.py` (the cross-model
workflows), `packs/forms.py` and `packs/views.py`.

- **Models:**
  - `Pack`: `owner`, `title` (up to 120), `slug`, `description` ("intended
    use", up to 2,000), `tags` (to `Tag`), `visibility` (`private` by
    default, `unlisted` or `public`; `is_public` and `is_unlisted` read it),
    `share_token` (see "Unlisted packs"),
    `copied_from` (nullable, set by Copy pack) and created/updated timestamps.
    `Pack.objects.create_pack(owner, title, description, tags)` writes the
    pack, a free slug and its tags in **one transaction**. The slug is the
    slugified title, then `-2`, `-3`… (`free_slug()`), unique site-wide,
    and it never changes on a rename. `Pack.objects.owned_by(user)` is the
    only way pages read packs, and it's empty for a visitor.
  - `PackItem`: `pack`, `saved_asset`, `preferred_variant` (a variant's
    label), `import_path` and `position`. Unique on (pack, saved_asset).
    Both links `CASCADE`: deleting a pack or an entry deletes its items,
    and `SavedAsset.asset` is still `PROTECT`, so the Asset stays.
    `default_import_path` is `<kind>s/<external_id>/`.
  - Tags typed as text go through `tags_from_text()`: split on commas, then
    `Tag.objects.from_names()` (so `normalize_tag()`).
  - *(Phase 8)* `Pack.objects.visible_to(user)` is who may **read** a pack:
    every public pack plus the caller's own (private ones included), public
    packs only for a visitor. The pack page, its download and every pack API
    view read through it, so another member's private pack is a 404.
    `owned_by()` is still who may **change** one. `Pack.get_public_url()` is
    `/packs/<slug>/`; `get_absolute_url()` stays the builder.
    `Pack.objects.public()` is public packs only, for anything that lists
    packs to other people (`public_featuring()`, the Phase 9 gallery).
- **Unlisted packs** *(user request, 2026-11-05)*: readable by anyone holding
  the share link, and listed nowhere.
  - `share_token`: `secrets.token_urlsafe(16)` (128 bits, 22 characters),
    unique, stored as is so the owner can see the link again.
    `set_visibility(choice)` makes it the first time a pack is unlisted and
    keeps it through later changes, so unlisting again brings the same link
    back. `rotate_share_token()` (New link) replaces it; the old link is a
    404 at once.
  - `Pack.objects.shared_by_link(token)` finds an unlisted or public pack by
    its token, never a private one. `get_share_url()` is
    `/packs/link/<token>/`; `reader_url` is the share link while unlisted,
    otherwise the slug page, and is what the manifest's `source_url`, the
    API's `page_url`, the builder's View pack page and the pack cards use.
  - `visible_to()` leaves unlisted packs out for everyone but the owner, so
    the slug page, its download, the API's list, detail and export treat an
    unlisted pack like a private one. Slugs come from titles and pks count
    up, so neither may open an unlisted pack.
  - `PackSharedView` and `PackSharedExportView` serve the same page and
    download by link; a public pack's link redirects to its slug page. Their
    replies carry `X-Robots-Tag: noindex, nofollow`, and the site's
    `Referrer-Policy: same-origin` (SecurityMiddleware) keeps the token out
    of Referer headers to provider sites.
- **`default_variant(kind, variants)`:** the label of a 2K JPG (an MP3 for
  sounds) when the asset has one, otherwise the first variant, or "".
  Labels are compared ignoring case and hyphens (`squeeze_label()`), so
  ambientCG's "2K-JPG" counts; the label is stored as the provider wrote it,
  for the export to look up (`chosen_variant()`).
- **Services** (`packs/services.py`), each in **one transaction**:
  - `add_to_pack(pack, saved_asset)` returns `(item, created)`. It raises
    `NotYourEntryError` (writing nothing) unless the entry is the pack
    owner's. An entry already in the pack returns its item untouched.
    Otherwise the item goes at the end (`Max(position) + 1`) on the default
    variant with a blank import path.
  - `add_from_provider(pack, provider_key, external_id)` is Discover's Add
    to pack: `save_to_library()` for the pack's owner (an entry they have
    is used as it is, otherwise a new To review one), then `add_to_pack()`.
    An `UnknownProviderError` or `ProviderError` saves and adds nothing.
  - `move_item(item, step)` swaps an item with its neighbour (`-1` up, `1`
    down) and rewrites the positions 0, 1, 2…, closing any gaps a Remove
    left. It returns False, writing nothing, at either end.
  - *(User request, 2026-11-05)* `reorder_items(pack, item_ids)` (drag and
    drop) rewrites the positions in the given order. It raises
    `ReorderError`, writing nothing, unless the ids are every item of the
    pack exactly once, so a stale page can't lose or duplicate an item.
    `sort_items(pack, sort)` sorts by one of `ITEM_SORTS`: `type` (the
    Discover order), `title`, `provider`, or `license` (what needs no credit
    first), ties by title then id.
- **Suggestions and Find more** *(Phase 10)*, `packs/suggestions.py`:
  - `suggest_assets(pack, limit=8)`: stored Assets ranked by how many tags
    they share with the pack (`shared_tags`, a `Count` of the asset's tags
    filtered to the pack's), highest first; equal counts by title A–Z (case
    ignored), then id. Assets sharing no tag and assets already in the pack
    are left out. It reads only `Asset` and `Tag`, never a `SavedAsset`, so
    no member's notes, rating, status or saves can reach it; "In your
    library" is checked against the owner's own entries in the view.
  - `add_suggestion(pack, asset)` (`packs/services.py`) returns `(entry,
    entry_created, item)`: `save_asset()` for the owner (their entry used
    untouched, otherwise a new To review one with its status record), then
    `add_to_pack()`, in **one transaction**. It never calls a provider: the
    Asset is already stored. `catalog.library.save_asset(user, asset)` is the
    create-or-reuse step `save_to_library()` now shares.
  - `find_more(pack)` returns a `FindMore(kind, query, url)` or `None` when
    the pack has no tags. The query is up to `FIND_MORE_TAGS` (2) of the
    pack's tags, those most stored assets carry first, then A–Z, as the entry
    page's Find more does; the type is the one most of the pack's items have
    (ties in Discover's order), textures for an empty pack. The URL is
    `discover_url()`.
  - Add replies with the item list and `packItemsChanged`, plus the saved
    count out of band only when a new library entry was made. A tags save
    (`packs:details`) sends `packTagsChanged`, and only then. The two events
    stay separate: Add from my library listens for `packItemsChanged` only,
    the suggestions for both.
- **Save single items and Copy pack** *(Phase 11)*:
  - Who: any signed-in member who can **read** the pack, through the pack
    page's own rule (`visible_to()` by slug, `shared_by_link()` by token), so
    another member's private pack, or an unlisted one by slug, is a **404**
    that writes nothing. An unlisted pack's readers save and copy through its
    share link (decided with the user, 2026-11-06). The owner can too: their
    items are already theirs, and Copy duplicates the pack. A visitor is sent
    to sign in and back to the pack's page (`PackReaderWriteMixin`; HTMX gets
    `HX-Redirect`).
  - Save (`PackItemSaveView`) is `catalog.library.save_asset(user,
    item.asset)`: the stored Asset, so no provider is called; the member's
    entry comes back untouched, or a new To review one is made. The reply is
    `packs/partials/item_save.html` ("In your library", linking to the
    member's entry), with the saved count out of band for a new entry.
  - `copy_pack(pack, user)` (`packs/services.py`) runs in **one
    transaction**: a private pack titled `copy_title()` ("<title> (copy)",
    shortened to fit 120 characters) with `copied_from`, the intended use and
    the tags, and no share token; then for each item in position order,
    `save_asset()` for `user` (an entry they have is used untouched, otherwise
    a new To review one with its status record) and a `PackItem` with the
    original's `preferred_variant`, `import_path` and `position`, copied as
    they are. A failure part-way leaves no pack, item, entry or status record.
    Nothing of the original owner's review comes along.
  - The builder names the original ("Copied from <title> by <owner>",
    `_copied_from()`), linking to its page only when the member can still read
    it by slug, so an unlisted original's link is never shown. Deleting the
    original sets `copied_from` to null; the copy stays.
- **Forms:** `NewPackForm` (title, intended use, tags). `PackDetailsForm`
  and `PackItemForm` bind only the posted fields, like `ReviewForm`, so each
  autosaving field writes only itself. A variant must be one of the asset's
  labels. An import path is optional, up to 300 characters, backslashes
  become `/`, and it must be relative (no leading `/`, no drive like `C:`)
  with no `..` segment. A bad value is a **400** with one sentence.
- **Views:** all members only (`PacksPageMixin`). A signed-out visitor goes
  to sign-in and back to `login_return_url()`: the builder for any of a
  pack's URLs, the page a picker was on, otherwise the page itself. An HTMX
  request gets `HX-Redirect`. `OwnPackMixin.get_pack()` looks the pack up
  through `owned_by()`, and items through that pack, so another member's
  pack or item is a **404**. Entries come through
  `SavedAsset.objects.for_user()`, so another member's entry is a **404**
  too, before `add_to_pack()` is ever called.
  - The builder's add, move and remove reply with the item list
    (`packs/partials/items.html`) and `HX-Trigger: packItemsChanged`, which
    refreshes Add from my library. Details, variant and import path reply
    with a status line. Any non-HTMX POST redirects to the builder.
  - Add from my library is `filter_library(user, {"q": q, "page": page},
    exclude_entries=<the pack's entries>)`: one page of 12, with what's in
    the pack left out before paging (user request, 2026-11-05). `show_in=1`
    includes them, marked "In pack". It reports how many are hidden.
  - The picker (`PickerView`) takes the member's `entry`, or a `provider`
    and `external_id`, checked before any provider is called (**400**
    otherwise). It lists `owned_by()` packs with their item counts and
    marks those the asset is already in. `PickerAddView` adds it and
    replies with the list again, "Added to …", and (for Discover) the saved
    count out of band, or the `ProviderError` message with nothing saved.
- **Side panel:** every packs page lists the member's packs
  (`packs/partials/pack_nav.html`, `my_packs`), with New. The pack page shows
  a visitor a short "Shared pack" note with Sign up instead.
- **The pack page** *(Phase 8)*: `PackPageView` at `/packs/<slug>/`, open to
  everyone (no login mixin) and read through `visible_to()`. It shows the pack
  (title, owner, intended use, tags) and each item in position order: the
  stored Asset's thumbnail, type, provider, title, author, license, credit
  (for non-CC0 items), the chosen variant with its file count and size, the
  import path and the source link. Those come from `manifest_item()`, so the
  page shows what the export will hold. It never reads anything from a
  library entry: no notes, rating, status or community rating. Only the
  owner sees Edit in builder (and a Private chip). Its only forms are Phase
  11's Save to library on each item and Copy pack; "In your library" checks
  the reader's own entries only.
  `PackExportView` (`/packs/<slug>/export/`) serves `manifest_for()` as an
  indented JSON download.

## Main page and gallery

*(Phase 9.)* `packs/gallery.py` and `HomeView` (`packs/views.py`).

- **`filter_public_packs(params)`** returns a `GalleryPage` (one Django
  `Page` of 12 and the tidied `GalleryParams`), like `filter_library()`. It
  starts from `Pack.objects.public()`, and every parameter only narrows
  that, so no query can list a private or unlisted pack. A test runs every
  kind of query against private and unlisted packs built to match it and to
  sort first.
  - `q`: every word must be in the title or a tag, ignoring case. A word is
    tidied by `normalize_tag()` before it's matched against tags, and tags
    match through a subquery, so a pack is listed once.
  - `type`: one of the four kinds. It keeps packs holding at least one item
    of that kind.
  - `sort`: `newest` (the default, `created_at`; there's no "made public at")
    or `items` (`item_count`, then newest). Both end on newest, then id.
  - `clean_gallery_params()` never fails. An unknown type is no filter, an
    unknown sort is `newest`, and a bad page is 1. A page past the end is
    the last page. `GalleryParams.url()` is the tidy URL, defaults left out,
    so the whole gallery is plain `/`.
- **Cards:** each pack is prefetched with its owner, tags and
  `gallery_items` (every item in position order, with its Asset), so a
  page of cards costs a fixed number of queries. `gallery_card(pack)` gives
  a `GalleryCard`:
  - `mosaic`: the Assets of the first 4 items by position
  - `blanks`: how many empty tiles fill the rest
  - `summary`: `type_summary()` of every item's kind, for example "3
    textures · 1 HDRI · 2 sounds". It uses Discover's order, singular or
    plural, leaves out types with no items, and an empty pack reads "No
    items yet"

  Nothing comes from anyone's library.
- **`HomeView`** (everyone) answers the gallery's HTMX requests (not
  boosted, not a history restore) with `packs/partials/gallery_results.html`
  and `HX-Push-Url`, as `LibraryView` does. Any other request gets the whole
  page in the same state, with the orbit hero. It sets `panel_start = "collapsed"` (see
  FRONTEND.md, "Main page").
- **The orbit hero** *(Phase 12)*: `packs/hero.py`, `hero_orbit(rng=None)`,
  gives a `HeroOrbit` (its `OrbitRing`s innermost first, each holding
  `OrbitThumb`s; `is_fallback`; `asset_count` and `pack_count` for the note).
  - **Only public packs:** the distinct Assets held by items of
    `Pack.objects.public()` packs, so a private or unlisted pack's asset never
    gets in, and each tile links to the **newest public pack** holding its
    asset (`_newest_public_packs()`, which also reads only public packs), so a
    private or unlisted pack is never the link either.
  - **The pick:** up to `HERO_SIZE` (18), taken from each kind in turn in
    Discover's order, each kind's assets shuffled, so a library of textures
    can't crowd out the rest: a kind runs short only when it has no more.
    Pass a seeded `random.Random` for a repeatable pick.
  - **The rings:** one per kind with tiles, ordered by how many tiles it holds
    (the busiest outermost, ties in Discover's order), `RING_STEP` (14 %) steps
    up to `OUTER_RING` (86 %) of the orbit, alternating directions, each with its
    `tile_rem` (bigger further out); tiles evenly spaced from a random start.
    `RING_CLASSES` holds the `border-<kind>` classes in full for Tailwind.
    `OrbitThumb.is_cutout` marks textures and models with an image
    (`CUTOUT_KINDS`), whose renders sit on a transparent background, so the
    page shows them with no tile behind.
  - **The fallback:** with fewer than `HERO_MINIMUM` (6) distinct assets, four
    rings, one type-icon tile each, opening Discover for that type
    (`discover_url()`).
  - It reads Pack, PackItem and Asset rows only: nothing from anyone's
    library (notes, ratings, statuses). The gallery's HTMX swaps don't build it.

## Demo data

*(Phase 9.)* `packs/demo.py`, two management commands, and the committed
snapshot `packs/demo_assets.json`.

- **The definitions:**
  - `DEMO_USERS`: `demo_mira`, `demo_otto` and `demo_juno`, all with the
    password `DEMO_PASSWORD` (`toolbox-demo`, obviously a demo value; the
    README lists it).
  - `DEMO_PACKS`: six themed public packs and one private pack, each item
    naming its asset and an optional import path.
  - `REVIEWS` and `REVIEW_CYCLE`: the reviews of each member's pack
    entries, so every status and a range of ratings appear.
  - `DEMO_SAVES`: more entries outside each member's own packs, so several
    members rate the same assets.
  - `demo_entries(username)` and `demo_asset_refs()` derive each library
    and the 43 assets.
- **`capture_demo_assets`** (run once, by hand, online) calls each
  provider's `fetch_record()` for every demo asset, spacing out Openverse's
  calls. It writes the snapshot (`write_snapshot()`, each `AssetRecord` as
  JSON, `record_to_json()`) only if every fetch worked.
- **`seed_demo`** calls `seed_demo()`, in one transaction:
  1. It checks the snapshot holds every asset the demo needs. A gap is a
     `ValueError` before anything is written.
  2. It gets or creates the users and resets their passwords.
  3. It stores each Asset with `Asset.objects.from_record()`.
  4. It saves each entry with `save_to_library()`. The Asset is stored, so
     no provider is called, and the first status is recorded as on the
     website.
  5. It finds each pack by owner and title (or `create_pack()`), restores
     its description, tags and visibility, then `add_to_pack()`s each item
     and sets its position and import path.

  A second run creates nothing, which a row-count test over every table
  checks. Entries a member already has are left as they are.

## Downloads

*(User request, 2026-11-05.)* `packs/downloads.py`. The Toolbox never
downloads, hosts or proxies a file. `pack_download()` and `item_download()`
only list the providers' URLs, each with its path in the zip, for
`static/js/bundle-download.js` to fetch and zip in the browser (as the
library's bundle does).

- **Paths:** each item's chosen variant's files (from `manifest_item()`, so
  the same files as the export) go under its import path, run through
  `safe_path()`; a repeated name gets `-2`, `-3`…. Unzipped at the top of a
  project, every file lands where the manifest says.
- **The pack:** always a zip, `<slug>.zip`, with `CREDITS.txt` and
  `<slug>.axcenity-pack.json` (`manifest_for()`) at the top.
- **One item:** a single file is saved as it is (`zip: false`); several are
  zipped with the item's own CREDITS.txt in its folder.
- **Limits:** no files, or over `BUNDLE_MAX_BYTES` (2 GB), returns
  `{"error": …}`, which the page shows.
- **Who:** `PackFilesView` reads through `visible_to()` and
  `PackSharedFilesView` through `shared_by_link()` (noindex), like the page
  and its manifest.

## Licenses and credits

*(User request, 2026-11-05.)*

- `catalog/licenses.py`: `license_key()` reads a license as the providers
  write it ("CC0 1.0", "CC BY-NC-SA 3.0", "Public Domain Mark", "CC
  SAMPLING+ 1.0"…, ignoring case, spacing, "CC" and the version) and
  `license_info()` returns its `LicenseInfo`: name, plain summary, credit
  (`required`, `listed` for the Public Domain Mark, or `optional` for CC0),
  commercial use and changes (yes, no, or `None` for partly or unknown),
  share-alike, the steps to meet it, and the deed URL. Anything else is
  `unknown`. `Asset.license_info` reads it. Not legal advice; each card
  links to the deed.
- `packs/credits.py`: `pack_credits(items)` groups a pack's items by license
  (those needing credit first), with `required` exactly the manifest's
  `credits`, `optional` thank-you lines for CC0 items, and warnings for
  non-commercial, no-changes, share-alike, Sampling+ and unknown licenses.
  It reads only PackItems and Assets (anything with `.asset` works, so a
  library entry gets the same treatment).
- **The notice** (user request, 2026-11-05: formal, for everyone):
  `PackCredits.notice(subject, *, compiled_by, source_url, prepared)` is the
  Attribution and License Notice, wrapped at 78 columns: who it covers and
  who compiled it, a statement that the assets belong to their creators,
  then 1. Required attribution, 2. License terms (per license: the deed, the
  items it applies to, and `LicenseInfo.permits`, `.requires` and
  `.prohibits` as You may / You must / You may not), 3. Restrictions in
  force (the warnings), 4. Optional acknowledgements, and a disclaimer. It's
  the CREDITS.txt in every download and the text the attribution pages
  offer to copy; `pack_notice(pack, credits, source_url)` fills it in for a
  pack. `credit_lines()` is the short version for a credits screen.
- **Uses and compatibility** (user request, 2026-11-05): `USES` is
  commercial, personal and internal. `LicenseInfo.use_status(use)` returns
  (`ok`, `caution` or `blocked`, a note): non-commercial licenses block
  commercial use and limit internal use to private testing, ND and SA add
  conditions, Sampling+ allows commercial use only remixed, and an unknown
  license blocks both public uses. `.uses` lists the three `UseVerdict`s and
  `.symbols` the license's `SYMBOLS` (icon, name, meaning).
  `packs.credits.compatibility(groups)` gives a pack's `UseCheck` per use:
  the most restrictive status (`worse()`) and one reason per limiting
  license, blocking ones first; `PackCredits.compatibility`,
  `.blocked_uses` and `.has_conditions` read it, and the notice's section 3,
  "Permitted uses", states it. The builder's item list carries the pack's
  credits, so the check follows every add, move or remove.
- **The Attribution center** (`packs/attribution.py`, its own views module):
  - `AttributionGuideView` (`/attribution/`, everyone): the license guide.
  - `AttributionPacksView` (members): `pack_credits()` for each of their own
    packs (`owned_by()`).
  - `PackAttributionView` (`/attribution/packs/<slug>/`): one pack's
    attribution through `visible_to()`, the pack page's reader rule;
    `SharedPackAttributionView` serves it by share link (noindex; a public
    pack's link redirects).
  - `AttributionAssetsView` (members): their library through
    `filter_library(..., licenses=license_filter(user, keys, credits))`.
    `license_filter()` turns the chosen license types and credit rules into
    the license strings in that library that match both (None when nothing is
    chosen); `license_choices()` gives the chips with counts;
    `clean_license_params()` drops unknown values. All in
    `catalog/library.py`.
  - `AssetAttributionView` (`/attribution/assets/<id>/`): the member's own
    entry only, a **404** otherwise.

## Export manifest

*(Phase 8.)* `packs/manifest.py`. `build_manifest(pack, *, source_url,
exported_at=None)` is the one builder; `packs.views.manifest_for(request,
pack)` calls it with the absolute URL of the pack's page, for the website
download and the API export alike, so both return the same document. The
shape is the PRD's Option A, locked by `tests/golden/pack_manifest.json`.

- **Top level:** `format` (`"axcenity-pack"`), `version` (1), `exported_at`
  (ISO 8601, UTC, to the second), `pack` (`title`, `slug`, `author` the
  owner's username, `description`, `tags` A–Z, `source_url`), `items` in
  position order, and `credits`.
- **Each item** (`manifest_item()`): `name`, `kind`, `provider`,
  `external_id`, `variant`, `files` (each `url`, `filename`, `size`),
  `total_size`, `license`, `license_url`, `author`, `attribution`,
  `source_url` and `import_path` (the owner's, or `<kind>s/<external_id>/`).
- **The variant** (`chosen_variant()`): the item's `preferred_variant`
  looked up by its exact label in `Asset.variants`. A label the Asset doesn't
  list falls back to `default_variant()`. An asset with no variants gives
  `variant: null`, `files: []`, `total_size: null`. A size the provider
  didn't give stays `null`.
- **Credits:** every item whose license isn't CC0 (`is_cc0()`: it starts
  with "CC0", ignoring case) gives `credit_line()`: its attribution, or
  `"<title>" by <author>, <license>` when it has none. Each line appears once,
  in item order.

## Library API

`catalog/api.py` (DRF generic views) and `catalog/serializers.py`. The
views are thin: they call the same `filter_library()` and
`save_to_library()` as the pages.

- **List** (`GET /api/library/`): `filter_library(request.user,
  request.query_params)`, so the parameters, the fallbacks and the order are
  exactly the library page's, `tag` and `sort=community` included. The
  reply is `{count, page, num_pages, next, previous, results}`; `next` and
  `previous` are absolute API URLs built from the tidy parameters
  (`LibraryParams.query_string()`, which the page's `url()` also uses). A
  page past the end is the last page, as on the website.
- **Create** (`POST /api/library/`): `NewLibraryEntrySerializer` checks
  `provider` (one of the three), `external_id` (1 to 200 characters) and the
  optional `notes`, `rating` and `status` before any provider is called
  (a **400** with the field's error otherwise). Then `save_to_library()`:
  - the member already has it: **400** `{"detail": "Already in your library."}`,
    and the entry is untouched
  - a `ProviderError`: **502** `{"detail": <its message>}`, nothing stored
  - otherwise **201** with the new entry
- **One entry** (`/api/library/<id>/`): the queryset is
  `SavedAsset.objects.for_user(request.user)`, so another member's entry is
  a **404** for every method. PATCH and PUT change only `notes`, `rating`
  and `status`, writing just the fields sent (`update_fields`, like
  `ReviewForm`, so a script and the drawer's notes autosave never overwrite
  each other). Anything else in the body (the asset, `id`, `saved_at`,
  `community`) is ignored. DELETE is a **204**; it removes the entry from
  the member's packs too (the PackItems cascade), and the shared Asset
  stays. The view's docstring says so, and DRF serves it as the
  `OPTIONS` description.
- **The owner serializer** (`LibraryEntrySerializer`): `id`, the nested
  read-only `asset` (`AssetSerializer`: Asset fields only, tags as names),
  `notes`, `rating`, `status`, `saved_at` and `community`
  (`{average, count}` or null), plus `status_change` (`{status, by, via,
  reason, changed_at}` for the record behind the current status, or null)
  and the write-only `status_reason`. A PATCH or PUT that changes the status
  records it with the caller and `via: "api"`, the reason on that change; a
  `status_reason` alone explains the current status. Create passes it to
  `save_to_library()` for the first record. Its rules match `ReviewForm`: notes up to
  10,000 characters, kept as typed with line breaks stored as LF; rating 1
  to 5 or null; one of the four statuses. The pack API's public serializers
  reuse `AssetSerializer`, which holds no member's fields.

## Pack API

*(Phase 8.)* `packs/api.py` and `packs/serializers.py`. Read-only: each view
defines only GET, so POST, PUT, PATCH and DELETE are a **405** (packs are
made and changed on the website only). Each sets `permission_classes =
[AllowAny]` over the project's sign-in-by-default, and reads packs through
`visible_to()`.

- **List** (`GET /api/packs/`): public packs plus the caller's own, newest
  change first, 12 to a page, in the library API's shape (`count`, `page`,
  `num_pages`, `next`, `previous`, `results`; a bad page is the first, one
  past the end the last). `?mine=1` (or `true`, `yes`) lists only the
  caller's and keeps itself in the page links; signed out it's a **401**
  (`NotAuthenticated`, `WWW-Authenticate: Token`).
- **Detail** (`GET /api/packs/<id>/`): the list's fields plus `items`.
- **Export** (`GET /api/packs/<id>/export/`): the manifest.
- **The public serializers:** `PackSerializer` (`id`, `slug`, `title`,
  `author`, `description`, `tags`, `visibility`, `item_count`, `created_at`,
  `updated_at`, and the absolute `url`, `export_url` and `page_url`).
  `PackDetailSerializer` adds `items`, each a `PackItemSerializer` (`id`,
  `position`, `preferred_variant`, `import_path`, `default_import_path` and
  the nested `asset`, `catalog.serializers.AssetSerializer`). Only Pack,
  PackItem and Asset fields: nothing from a library entry, and no community
  rating.

## Authentication

- Django's `LoginView` and `LogoutView`. `LogoutView` accepts only POST,
  so a GET returns 405.
- `accounts.views.SignUpView` is built on `UserCreationForm`. It signs the
  new member in and honours a same-site `next`.
- `LOGIN_URL = "accounts:login"`. `LoginRequiredMixin` adds `?next=` so the
  member comes back after signing in.
- `LOGIN_REDIRECT_URL` and `LOGOUT_REDIRECT_URL` both point to `packs:home`.
- The API uses DRF's `TokenAuthentication` (`Authorization: Token <key>`,
  no CSRF) and then `SessionAuthentication` (the browser session; writes
  must pass CSRF). Token comes first, so a signed-out API request is a
  **401** with `WWW-Authenticate: Token`. Every API view needs sign-in
  (`IsAuthenticated`), and replies are JSON only: DRF's browsable API is
  off, since its Bootstrap colours sit outside the `axcenity` palette.
- **The token page** (`accounts.views.TokenView`, `/accounts/token/`):
  `Token.objects.get_or_create()` on each visit, so the first visit creates
  the token. It's sent `Cache-Control: no-store` (`never_cache`). The
  Account pages share one side panel
  (`accounts/partials/account_pages.html`): Profile, Settings and API
  token. There's no way to regenerate a token yet; the PRD doesn't ask
  for one.

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
the API. All are built:

| Function | Purpose |
|---|---|
| `normalize_tag()` | Built (Phase 3), `catalog/tags.py`. The one way to tidy tag names: lowercase, trimmed, single spaces; number-only tags dropped; a plural "s" stripped from the last word unless it ends in "ss". Returns `None` for a dropped tag |
| `filter_library(user, params)` | Built (Phase 4), `catalog/library.py`. Library search (title, tags, notes), filters (type, provider, status, tags, minimum rating), sorts and pages of 12, for the caller's own entries only (see "Library and saving") |
| `filter_public_packs(params)` | Built (Phase 9), `packs/gallery.py`. The gallery's search (title and tags), type filter, sorts (newest, most items) and pages of 12, over public packs only (see "Main page and gallery") |
| `seed_demo(snapshot=None)` | Built (Phase 9), `packs/demo.py`. The demo members, libraries and packs from the committed snapshot, offline and safe to run again (see "Demo data") |
| `pack_credits(items)` | Built (user request, 2026-11-05), `packs/credits.py`. A pack's licenses, required and optional credits and warnings, and the formal notice (see "Licenses and credits") |
| `license_info(name)` | Built (user request, 2026-11-05), `catalog/licenses.py`. What a license allows and asks |
| `hero_orbit(rng=None)` | Built (Phase 12), `packs/hero.py`. The main page's orbit: up to 18 distinct assets from public packs only, from each type in turn, on one ring per type (the busiest outermost), each linking to the newest public pack holding it; the type-icon tiles below 6 (see "Main page and gallery") |
| `suggest_assets(pack, limit)` | Built (Phase 10), `packs/suggestions.py`. Stored Assets ranked by shared tags with the pack, ties by title then id, never the pack's own (see "Packs") |
| `copy_pack(pack, user)` | Built (Phase 11), `packs/services.py`. A private copy for `user` in one transaction: title, `copied_from`, tags, and each item's variant, import path and position, on the copier's own entries (missing ones To review, theirs untouched) (see "Packs") |
| `add_to_pack(pack, saved_asset)` | Built (Phase 7), `packs/services.py`. Adds an item at the end on the default variant, once per entry, and refuses another member's entry (see "Packs") |
| `build_manifest(pack, *, source_url, exported_at=None)` | Built (Phase 8), `packs/manifest.py`. The Option A export, locked by a golden file (see "Export manifest") |
| `search_records()` | Built (Phase 2a). Returns `AssetRecord`s (`providers/records.py`), next to the console's `search()`. Openverse's also takes `licenses=` (user request, 2026-11-06) |
| `load_shelf(provider, kind, query, page, filters)` | Built (Phase 2a; filters 2026-11-06), `catalog/discover.py`. One page of one shelf, cached, with the license filters applied (see "Discover") |
| `asset_preview(provider_key, external_id)` | Built (user request, 2026-11-06), `catalog/preview.py`. One Discover result in full for its drawer, from the stored Asset or a cached `fetch_record()`; never stores anything |
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
- **Filtered searches** (Openverse with license filters) are cached apart,
  the allowed licenses added to the key. A CC0-only provider's search is the
  same with or without filters, so it shares the unfiltered entry.
- **Discover's drawer** caches each fetched record for 1 h
  (`preview.PREVIEW_CACHE_SECONDS`, `preview_cache_key()`). A stored Asset
  needs no cache.
- **Provider status** is kept for 1 h (see Discover).
- **Failures are never cached:** a `ProviderError` returns before anything
  is stored, so Retry always reaches the provider again.

Tests clear the cache around every test.
