# Plan: Axcenity Toolbox

> Source PRD: [prd/axcenity-toolbox.md](../prd/axcenity-toolbox.md) (2026-10-30)

## Architectural decisions

These decisions apply to every phase:

- **Apps:**
  - `config` holds the settings and the root URLs.
  - `providers` is the existing package of provider clients.
  - `catalog` holds Asset, Tag and SavedAsset, Discover, the library pages
    and the library API.
  - `packs` holds Pack and PackItem, the builder, the public pages and
    gallery, export, suggestions, copying and the pack API.
  - `accounts` holds sign-up, sign-in, sign-out and the profile with its
    API token page.
- **URLs:** each app gets its own URL namespace.
  - `/` is the main page and the public gallery.
  - `/discover/` is Discover. It takes the type and query in the query
    string, and each provider shelf has its own fragment URL.
  - `/library/` is the library. Single entries are at `/library/<id>/`
    and use the pk.
  - Packs have owner pages for creating, listing and the builder. The
    public page is at `/packs/<slug>/`, and slugs are unique across the
    whole site.
  - Sign-up, sign-in, sign-out and the token page sit under the
    `accounts` namespace.
  - The API is `/api/library/`, `/api/library/{id}/`, `/api/packs/`,
    `/api/packs/{id}/` and `/api/packs/{id}/export/`.
- **Models:**
  - `Asset` is unique on (provider, external_id) and has a many-to-many
    link to `Tag`.
  - `SavedAsset` links a user to an Asset and is unique on (user, asset).
  - `Pack` has an owner and a many-to-many link to `Tag`. `copied_from`
    is a nullable link to another `Pack`.
  - `PackItem` links a Pack to a SavedAsset and holds
    `preferred_variant`, `import_path` and `position`.
  - Every tag name goes through `normalize_tag()`.
- **Shared and per-user records:**
  - Asset records are shared and reused for every user. The first save by
    anyone calls `fetch_record()`, and later saves reuse the row.
  - SavedAsset records are unique per (user, asset).
  - Deleting a SavedAsset cascades to its PackItems but never deletes the
    shared Asset.
  - A PackItem can only point to a SavedAsset owned by the pack's owner.
    `add_to_pack()` enforces this, and tests prove it.
- **Access:**
  - Any pk or slug the caller doesn't own returns **404**, including
    private packs.
  - Signed-out visitors are sent to sign in on the website. The API
    refuses them with DRF's 401 or 403.
- **Authentication and CSRF:**
  - The website uses Django's `LoginView`, `LogoutView` and
    `UserCreationForm`.
  - Every website form and HTMX write uses Django's CSRF protection. The
    base layout sends the CSRF token as a header on every HTMX request.
  - The API uses DRF `SessionAuthentication` and `TokenAuthentication`.
  - API write requests that use a session must pass CSRF validation.
  - API requests that use a token send `Authorization: Token <key>` and
    don't need a CSRF token.
- **Providers:**
  - `search_records()`, `fetch_record()` and `AssetRecord` sit next to the
    existing `search()` and `get_details()`, which stay as they are.
  - All requests go through `get_json()`, and every failure is a
    `ProviderError` with a message that's safe to show users.
  - Caching uses Django's local-memory cache. Searches are cached for 1 h
    and Poly Haven info for 12 h. Failures are never cached.
- **Frontend:**
  - Tailwind and DaisyUI run through django-tailwind-cli's standalone
    binary, so no Node is needed.
  - The custom DaisyUI theme is `axcenity`.
  - HTMX runs through django-htmx. A view checks `request.htmx` to choose
    between returning a fragment and a full page.
  - Navigation is boosted (`hx-boost` on `<body>`, added in the Phase 1
    polish). A boosted request also carries `HX-Request`, so a view that
    returns fragments checks `request.htmx and not request.htmx.boosted`.
    See docs/FRONTEND.md.
- **Testing:**
  - All tests live in one top-level test folder with one shared conftest.
  - An autouse fixture clears the cache before each test.
  - An autouse network guard makes any unmocked outbound HTTP request
    fail the test.
  - App tests replace provider functions with `monkeypatch`, and provider
    tests use `responses`.

## Completion gate

Every phase ends with this gate. A phase isn't done until every box is
ticked. Each phase lists the access rules that its own gate must cover.

- [ ] **Tests:** `uv run pytest` passes, including every test from earlier
  phases.
- [ ] **No live calls:** no test reaches a live provider API. The network
  guard is active and no test turns it off.
- [ ] **Existing features:** everything built before still works. That
  includes the console script's regression tests and the earlier phases'
  tests.
- [ ] **Access rules:** every access rule this phase touches is tested.
  That means the website and the API wherever both exist, plus the CSRF
  rules for any new write.
- [ ] **Ruff:** `uv run ruff check .` and `uv run ruff format --check .`
  pass.

---

# Tier 1: Essential

## Phase 1: Branded shell and accounts

**User stories:** 1, 2, 3, 72, 74, 75, 76, 85, 86

### What to build

The Django project with the `catalog`, `packs` and `accounts` apps
registered, built with uv, Tailwind and DaisyUI (the `axcenity` theme),
HTMX and Ruff. Every page uses the editor-style shell:

- a title bar with the wordmark and "TOOLBOX"
- an activity bar: the Home icon tile, then Discover, Library, Packs,
  Account and Settings
- a collapsible side panel
- a monochrome status bar, holding placeholders for now

The branding is copied from the engine repo: the wordmark, the icon tile,
the 32 px favicon, the three fonts and the palette. The four type colours
are design tokens, used only for asset type.

A visitor can sign up and then sign in and out. Opening a members-only
page while signed out goes to sign-in and comes back to that page
afterwards.

This phase also sets up the test folder, the shared conftest, the
cache-clearing fixture, the network guard and the regression tests for
the console script.

### Acceptance criteria

- [x] A visitor can sign up with a username and password and ends up
  signed in.
- [x] A member can sign in and sign out. Sign-out is a POST that's
  protected by CSRF.
- [x] A signed-out visitor who opens a members-only page is sent to
  sign-in with `next` set, and returns to that page after signing in.
- [x] Every page renders inside the shell, and the side panel can be
  collapsed.
- [x] The fonts, logos and favicon load from static files. The chrome is
  monochrome, primary buttons are white with dark text, and type colour
  appears nowhere yet.
- [x] The theme picks up no Tailwind or DaisyUI colours outside the
  `axcenity` palette.
- [x] A test proves that the network guard fails any unmocked request.
- [x] The console script's regression tests, using `responses`, pass
  against the unchanged `search()` and `get_details()` in each provider.
- [x] Ruff is configured in `pyproject.toml` and the repo is clean
  against it.

### Completion gate

- [x] Standard gate (see top). Access rules: the members-only page
  redirects signed-out visitors to sign-in. Sign-up, sign-in and sign-out
  forms reject requests without a CSRF token.

---

## Phase 2a: Discover with provider shelves and error handling

**User stories:** 7, 8, 9, 10, 11, 12

### What to build

Each provider gets an `AssetRecord` and `search_records(query, kind,
limit=12)`, using the PRD's mapping from type to provider and filter. The
existing `search()` and `get_details()` stay untouched.

`/discover/` shows four type tiles and a command-bar search, and pressing
`/` focuses the search. The page is open to signed-out visitors.

> **Already in place (Phase 1 polish):** the home page's hero search
> already sends `/discover/?q=<query>`. Read the query from `q` so it
> lands in the command bar.

Each matching provider's shelf is its own HTMX request, fired on page
load, so the page appears before any shelf finishes:

- Textures, HDRIs and models get an ambientCG shelf and a Poly Haven
  shelf.
- Sounds get only an Openverse shelf.

A shelf shows up to 12 results, each with a thumbnail, title, author and
license. A failed shelf shows a DaisyUI alert with the `ProviderError`
message and a Retry button that re-requests only that shelf. The other
shelf keeps working.

### Acceptance criteria

- [x] Each type shows exactly the providers in the PRD mapping, and
  passes each provider the right filter.
- [x] The Discover page renders without waiting for any provider. Each
  shelf loads through its own request.
- [x] Each result shows a thumbnail, title, author and license, with at
  most 12 per shelf. Uneven counts between providers display as returned.
- [x] A Poly Haven search with `keywordMatches == 0` shows an empty shelf
  with a "no matches" message, not an error.
- [x] A failed shelf shows the friendly `ProviderError` message, never a
  raw response body or traceback, plus a Retry button. Retry re-requests
  only that shelf's URL.
- [x] Pressing `/` focuses the search unless the cursor is already in a
  text field.
- [x] An unknown type or provider in a shelf URL is rejected without
  calling any provider.
- [x] A shelf URL is validated (kind, provider, the provider serving that
  kind, and a non-blank query) before the view checks for HTMX, so a bad
  shelf URL always gets a **404** or **400**, never a redirect.
- [x] Poly Haven cuts its search hits to the limit before fetching
  `/info`, so a search makes at most 12 `/info` requests.
- [x] Every `ProviderError` message is safe to show: it never contains raw
  exception text or response details. The details are written to the
  server-side log instead. (Added to 2a from 2b, because the shelf shows
  the message directly.)
- [x] **Provider client tests:** `responses` tests cover each provider's
  `search_records()` on a normal response. They check that every
  `AssetRecord` field is filled in.
- [x] **Application tests:** tests replace `search_records` with
  `monkeypatch` for a normal shelf, an empty shelf and a `ProviderError`
  shelf.
- [x] **HTMX mixed shelves:** a test makes one provider raise
  `ProviderError` and the other succeed for the same search. The failed
  shelf's fragment contains the alert and the Retry button, the other
  shelf's fragment contains its results, and neither request affects the
  other.

### Completion gate

- [x] Standard gate (see top). Access rules: Discover and its shelf URLs
  work for signed-out visitors. The console script's regression tests
  still pass after the provider modules gain the new functions.

---

## Phase 2b: Caching, provider credits, fallback icons, status bar and failure tests

**User stories:** 15, 16, 17, 73 (provider status), 83

### What to build

- **Caching:** successful shelf results are cached for 1 hour per
  (provider, kind, normalized query), and Poly Haven asset info for 12
  hours. Failures are never cached, so Retry always sends a fresh
  request.
- **Credits:** each shelf credits its provider ("Assets from ambientCG ·
  CC0", "Powered by Poly Haven", "Made with Openverse").
- **Fallback icons:** a missing or broken thumbnail is replaced by an
  icon for the asset's type, so a broken image never shows.
- **Status bar:** it shows each provider's last known status (OK, error
  or unknown). Shelf outcomes record that status in the cache, so it needs
  no extra health-check requests.
- **Failure tests:** the full suite for story 83, at all three levels.

### Acceptance criteria

- [x] A repeated identical search within the hour calls the provider
  once. Searches that differ only in case or whitespace share one cache
  entry.
- [x] A failed search followed by Retry calls the provider again, and a
  success on Retry is shown and cached.
- [x] Poly Haven info is cached for 12 hours, wherever it's fetched.
- [x] Each shelf shows its provider's credit line.
- [x] A result with no thumbnail URL shows the type icon. A thumbnail
  that fails to load is swapped for the type icon, and the logo never
  appears on a thumbnail.
- [x] After a shelf succeeds or fails, the status bar shows that
  provider's status. Providers not yet used show as unknown.
- [x] **Provider client tests (`responses`):** each of these gives its
  own friendly `ProviderError` message, and none leaks HTML or exception
  text (Phase 2a makes the messages safe; this phase proves it for each
  failure):
  - a timeout
  - a connection error
  - a 429
  - Openverse's 500 with an HTML body
  - Poly Haven's 404
  - Poly Haven's `keywordMatches == 0`, which counts as no results, not
    an error
- [x] **Application tests (`monkeypatch`):** each failure message reaches
  the shelf alert unchanged, and failures never reach the cache.
- [x] **HTMX mixed shelves:** the Phase 2a test runs once for each failure
  type. In every case one shelf shows the alert and Retry while the other
  shows its results.

### Completion gate

- [x] Standard gate (see top). Access rules: Discover is still open to
  signed-out visitors, and the status bar shows no member data to them.

### Phase 2b polish (2026-11-04, at the user's request)

Added after the phase, ahead of the PRD's Tier 3. The PRD now records it
under Discover.

- [x] **Sound previews:** a sound result plays its Openverse audio in the
  page (`AssetRecord.preview_url`, streamed, never copied). One plays at a
  time, and it stops when its card leaves the page.
- [x] **Load more:** a full shelf ends with "Load 12 more", which appends
  the next page up to page 20 (240 results). A failed page shows Retry in
  place and keeps the cards already shown. Each page is cached on its own,
  and a bad `page` is a **400** before any provider call.
- [x] **Card details:** a long author list ends in an ellipsis inside the
  card. Hover or focus shows the full title, author, license, source and
  tags.
- [x] **Random pick:** with no query, Discover searches a random featured
  term for the type, with Shuffle. The command bar stays empty.

---

## Phase 3: Save to library

**User stories:** 4, 13, 14, 18, 19, 73 (saved count)

### What to build

This phase adds the Asset, Tag and SavedAsset models with their
migrations, and `normalize_tag()`. Each provider gains
`fetch_record(external_id)`, which returns the full asset details,
including `variants`. Poly Haven's version keeps the file download URLs
that the current details code throws away.

Each Discover result gets "Save to library":

- The first save of an asset by anyone creates the shared Asset, and
  later saves reuse it.
- The button swaps itself for an "In library" badge with the logo mark.
- Results the member has already saved render as "In library".
- A signed-out visitor who clicks Save is sent to sign in and back to
  Discover.

`/library/` shows a private card grid with each asset's thumbnail, type,
title, status and rating. The status bar shows the member's saved count.

### Acceptance criteria

- [x] The first save of an asset calls `fetch_record()` and creates one
  Asset with its tags normalized. A second user saving the same asset
  reuses the Asset and doesn't call `fetch_record()`.
- [x] Saving an asset the member already has creates no second
  SavedAsset, and the result shows "In library".
- [x] If `fetch_record()` raises `ProviderError`, the friendly message
  replaces the button and nothing is saved.
- [x] A new SavedAsset starts as To review with no rating.
- [x] `normalize_tag()` unit tests cover each rule:
  - case and surrounding whitespace
  - collapsed inner whitespace
  - number-only tags dropped
  - a simple plural "s" removed
  - words ending in "ss" kept
- [x] Deleting a SavedAsset leaves the shared Asset in place (model-level
  test).
- [x] The library grid renders from local data while every provider
  function is patched to raise.
- [x] Thumbnails link to the provider URL and are never downloaded.
- [x] `responses` tests cover each provider's `fetch_record()`, including
  the variants and the Poly Haven file URLs.

### Completion gate

- [x] Standard gate (see top). Access rules:
  - `/library/` sends signed-out visitors to sign in.
  - A member sees only their own entries.
  - Saving needs sign-in and a valid CSRF token.
  - The saved count only ever counts the current member's entries.

---

## Phase 4: Library browsing

**User stories:** 20, 21, 22, 23, 24, 33

### What to build

One shared `filter_library(user, params)` handles everything the library
does:

- **Search:** title, tags and the member's own notes.
- **Filters:** type, provider, status and minimum rating.
- **Sorts:** newest saved (the default), oldest, title A–Z, and rating
  high to low.
- **Pages:** 12 entries per page.

The filters live in the side panel. HTMX swaps only the results, and
`hx-push-url` keeps the address bar in step. Loading the same URL
directly renders the same view as a full page, and Back works. An empty
library and an empty result each say what to do next.

> **Already in place (Phase 1 polish):** `catalog/library.html` already
> renders the controls, disabled:
>
> - `#library-toolbar` holds the search (`q`), the sort select with the
>   four sorts, and a grid/list view toggle.
> - `#library-filters` in the side panel holds the type, provider, status
>   and minimum-rating chips.
> - `#library-results` holds the empty state.
>
> Wire these up rather than adding new ones, and keep them disabled while
> the library is empty. The view toggle isn't in the PRD, which describes
> only a card grid: either build a list view or remove the toggle.

### Acceptance criteria

- [x] Unit tests cover `filter_library()` for each search field, each
  filter, each sort, pagination and combinations of these.
- [x] `filter_library()` never returns another user's entries, whatever
  the parameters.
- [x] Sorting by rating puts unrated entries last. Unknown sort or filter
  values fall back to the defaults instead of failing.
- [x] An HTMX request returns only the results fragment. A normal request
  for the same query string returns the full page in the same state.
- [x] The pushed URL holds the search, filters, sort and page.
- [x] An empty library links to Discover. No matches offers to clear the
  filters.

### Completion gate

- [x] Standard gate (see top). Access rules: the library and its fragment
  URL send signed-out visitors to sign in. Filter parameters can't expose
  another member's entries.

### Phase 4 polish (2026-11-05, at the user's request)

Added after the phase. The PRD records it as stories 87–92 and under
Discover and Library. Add to pack works in Phase 7; only its interface is
built here. (Collections were first planned too, as Phase 7b, then
dropped the same day at the user's request: everything centres on packs.)

- [x] **Whole texture thumbnails:** a texture's card frame is square with
  `object-fit: contain`, so the tile is no longer cut at the top and
  bottom. Other kinds keep the 4:3 cover frame.
- [x] **Details only while hovered:** the details panel shows on hover or
  on keyboard focus (`:has(:focus-visible)`), no longer on
  `:focus-within`, so it goes once the pointer leaves after a click or a
  save. A **Details** button keeps it open until it's pressed again or
  Escape is pressed. While kept open it scrolls, and it lists every tag.
- [x] **Corner actions:** small buttons in each card's top-right corner
  replace the full-width Save row.
  - Discover: Save (then a filled "In library" check with no logo mark, as
    the corner sits on the thumbnail), Add to pack and Details.
  - Library: Add to pack, Details and Remove.
  - A visitor's Save and Add to pack sign in and come back.
- [x] **Add to pack picker:** the interface only. One `<dialog>` per page
  (`catalog/partials/pack_picker.html`) shows the asset's title, "You
  don't have any packs yet.", Go to Packs, and a note that packs are on
  the way.
- [x] **Tag filter:** `tag` (repeatable) in `filter_library()` keeps
  entries with every chosen tag. Tags are normalized, so a tag joins all
  three providers. The side panel lists the member's own top 24 tags with
  counts, plus any chosen tag beyond those. `Tag.objects.in_library()`
  never counts another member's entries.
- [x] **Remove from library:** `POST /library/<id>/remove/`
  (`catalog:remove`) works for the owner only (otherwise **404**), with
  CSRF, after the browser's confirm. The shared Asset stays. HTMX gets the
  results for the same view back, with the saved count out of band and
  `HX-Replace-Url` when the page shrinks away.
- [x] **Fixed on the way:** library stars used the class `.rating`, which
  DaisyUI's rating component painted as grey blocks. It's now
  `.star-rating`.
- [x] Standard gate (see top). Access rules: Remove sends a visitor to
  sign in and removes nothing, returns 404 for another member's entry,
  and rejects a POST without CSRF. The tag filter and the tag chips never
  show another member's entries or tags.

---

## Phase 5: Library drawer

**User stories:** 5, 25 (without the pack list, which comes in Phase 7), 26, 27, 28, 29, 30

### What to build

Clicking a card opens a slide-over drawer at `/library/<id>/`. Opening
the same URL directly shows it as a full page. The drawer shows:

- the asset's details
- its license and attribution
- the source link
- its file variants

Status and stars save at once, and the rating can be cleared. Notes save
on their own after a short debounce. Out-of-band swaps keep the card
behind the drawer in step with any change.

> **Already in place (Phase 4 polish, 2026-11-05):** library cards have
> corner actions (Add to pack, Details, Remove) and a details panel. The card's title still opens the provider's page. Make
> the title open the drawer, keep the corner actions above the stretched
> link, and give the drawer the same Remove (`catalog:remove`) as its
> Delete.

### Acceptance criteria

- [x] An HTMX request for `/library/<id>/` returns the drawer fragment,
  and a direct visit returns a full page.
- [x] Changing the status saves at once and updates the card behind the
  drawer through an out-of-band swap.
- [x] Setting or clearing the rating saves at once and updates the card.
  Values outside 1–5 are rejected.
- [x] Notes save after the debounce with no Save button, and the saved
  text survives a reload.
- [x] The drawer renders from local data while every provider function is
  patched to raise.
- [x] *(Added 2026-11-05 at the user's request.)* A failed notes save
  never loses the text. The reply replaces only the status line, which
  shows the error and Try again. The text is kept in the browser until a
  save succeeds and comes back when the entry reopens. Leaving with
  unsaved notes asks first. A signed-out save gets a 401 with a sign-in
  link (new tab) instead of a redirect.

### Phase 5 polish (2026-11-05, at the user's request)

Added after the phase. The PRD records it as stories 93 and 94.

- [x] **No drawer flicker:** the drawer's swaps (opening it, saves and its
  Remove) leave the page transition out (`transition:false`). Before, the
  content behind faded out and in, so the drawer appeared, vanished and
  reappeared.
- [x] **Community rating:** each member's rating stays private, but library
  cards, the drawer and Discover results show the average of every
  member's rating with how many rated (never who). The library sorts by it
  ("Community rating", unrated assets last). For the API (Phase 6): add
  the same `community` sort to the list; for Phase 8, keep community
  ratings off public pack pages or allow for them in the sentinel test.
- [x] **One-column sidebar:** the activity bar and the side panel are one
  column. Expanded, each icon sits beside its label, with the page's own
  panel below; collapsed, it's the icon strip with tooltips.
- [x] Standard gate (see top). Access rules: the community rating never
  shows another member's name, notes or status, on the library, the
  drawer or Discover.

> **For Phase 7:** the drawer's Remove (`entry_remove.html`) still uses
> `hx-confirm`; give it the same packs dialog as the card. The drawer's
> pack list goes in `entry_detail.html`, after "License and credit".

### Completion gate

- [x] Standard gate (see top). Access rules:
  - Another member's `/library/<id>/` returns 404, for viewing and for
    every update URL.
  - Signed-out visitors are sent to sign in.
  - Every update needs a valid CSRF token.

---

## Phase 6: Library API and token page

**User stories:** 6, 61, 62, 63, 64, 65, 66, 67, 68

### What to build

DRF is set up with session and token authentication. A token page on the
member's profile shows their API token and creates it on the first visit.

`/api/library/` is built as the PRD's API table sets out:

- **List:** goes through `filter_library()`, with the same parameters
  and pages of 12. That includes `tag` (Phase 4 polish), which may
  repeat.
- **Create:** takes the provider and external_id, plus optional notes,
  rating and status. It reuses the local Asset or calls `fetch_record()`.
- **Read and update:** read one entry, or update its notes, rating and
  status with PATCH or PUT. Asset fields are read-only.
- **Delete:** its documentation says the entry is also removed from the
  member's packs. The website's Remove (`catalog:remove`, Phase 4
  polish) already deletes the same way.

The owner serializer includes notes, rating and status.

### Acceptance criteria

- [x] The list returns the same entries in the same order as the website
  for the same parameters.
- [x] Create with a known Asset doesn't call `fetch_record()`. Create with
  a new Asset calls it once.
- [x] Create returns these errors:
  - a duplicate: **400** with "Already in your library."
  - a `ProviderError`: **502** with `{"detail": <friendly message>}`
  - an unknown provider: **400**
- [x] PATCH and PUT change only notes, rating and status. Asset fields in
  the request are ignored or rejected.
- [x] DELETE removes the entry and leaves the shared Asset. The endpoint's
  documentation says the entry also leaves the member's packs.
- [x] The token page shows the member's token. The token signs requests
  through `Authorization: Token <key>`.

### Completion gate

- [x] Standard gate (see top). Access rules:
  - Unauthenticated requests are refused with 401 or 403.
  - Another user's entry returns **404** for GET, PATCH, PUT and DELETE.
  - The list only ever holds the caller's entries.
  - A session POST, PATCH or DELETE without a CSRF token is refused. The
    test client enforces CSRF checks for this test.
  - The same request signed with a token succeeds without a CSRF token.
  - The token page sends signed-out visitors to sign in.

> **For Phase 8:** the pack API can reuse `catalog.serializers.AssetSerializer`
> (Asset fields only) in its public serializer. The API is JSON only and
> needs sign-in by default (`REST_FRAMEWORK` in settings), so the public
> pack views must set `permission_classes` to allow signed-out reads, and a
> signed-out `?mine=1` will get the 401 that token authentication gives.

---

## Phase 7: Pack builder

**User stories:** 25 (pack list in the drawer), 31, 32, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43

### What to build

This phase adds the Pack and PackItem models with their migrations, and
the shared `add_to_pack(pack, saved_asset)`.

A member can create a pack with a title, a description of its intended
use, and comma-separated tags. The tags go through `normalize_tag()`.
New packs are private, and the owner can switch them public and back.
The owner can also edit or delete a pack, and the activity bar's Packs
entry lists the member's packs.

The builder:

- "Add from my library" filters as the owner types and calls
  `add_to_pack()`.
- Each item has a variant dropdown. It defaults to a 2K JPG (or MP3 for
  sounds) when one exists, otherwise the first variant.
- Each item has an import path field. When it's blank, the field shows
  the default path.
- Each item has a Remove button.
- Every control saves on its own through HTMX.

Library cards get an "Add to pack" dropdown that also calls
`add_to_pack()`. The drawer lists the packs an asset is in. Delete opens
an HTMX confirm dialog that lists the packs the item will be removed
from.

> **Already in place (Phase 4 polish, 2026-11-05):**
>
> - Library cards and Discover results have an Add to pack corner button
>   (`data-picker="pack-picker"`). It opens
>   `catalog/partials/pack_picker.html`, which shows "You don't have any
>   packs yet." and Go to Packs. Wire it up rather than adding a separate
>   dropdown. Load the list of the member's own packs through HTMX when
>   the picker opens, so it's always current, and make choosing one call
>   `add_to_pack()`.
> - On Discover, choosing a pack for a result that isn't in the library
>   saves it first (`save_to_library()`, To review), then adds it. A
>   `ProviderError` shows its message, and nothing is saved or added.
> - The card's Remove (`catalog:remove`) uses the browser's confirm
>   (`hx-confirm`). Replace that with the HTMX dialog that lists the packs
>   the entry will leave.

### Acceptance criteria

- [x] Typing tags "Rocks, rock, 2048,  Mossy  Stones" stores the tags
  `rock`, `mossy stone`.
- [x] A new pack is private. The public/private switch saves at once.
- [x] `add_to_pack()`:
  - adds an item at the end with the default variant
  - adding the same SavedAsset twice to one pack leaves a single item
  - refuses a SavedAsset that the pack's owner doesn't own
- [x] The default variant rule is tested for a 2K JPG, an MP3, and the
  fallback to the first variant.
- [x] One SavedAsset can sit in two packs with a different variant and
  import path in each.
- [x] Changing a variant, an import path or the order saves through HTMX
  with no Save button.
- [x] Remove deletes only the PackItem. The SavedAsset and the Asset
  stay.
- [x] Deleting a SavedAsset first shows the packs it's in. Confirming
  removes its PackItems from those packs and leaves the shared Asset and
  the packs' other items alone.
- [x] Deleting a pack removes its PackItems but none of the owner's
  SavedAssets.
- [x] The library card's "Add to pack" dropdown lists only the member's
  own packs.
- [x] Adding a Discover result to a pack saves it to the library first
  when needed (To review) and reuses an existing entry untouched. A
  `ProviderError` saves and adds nothing.

### Completion gate

- [x] Standard gate (see top). Access rules:
  - The builder and every pack edit URL return **404** to another member
    and send signed-out visitors to sign in.
  - Adding another member's SavedAsset to your pack is refused, through
    `add_to_pack()` and through the HTMX URLs.
  - Adding your SavedAsset to another member's pack returns **404**.
  - Every pack write needs a valid CSRF token.

> **Built as (2026-11-05):** the owner's pages use the pk
> (`/packs/<id>/edit/`), leaving `/packs/<slug>/` for Phase 8's public page.
> The slug is set once at creation and survives a rename. The order is
> changed with Move up and Move down, not drag and drop. Pack creation,
> adding an item, Discover's save-then-add and reordering each run in one
> transaction (user request).
>
> **For Phase 8:**
>
> - `PackItem.preferred_variant` is the variant's label exactly as the
>   provider wrote it, so the export can find it in `Asset.variants`. It's
>   blank for an asset with no variants.
> - `PackItem.default_import_path` already gives `<kind>s/<external_id>/`.
> - `Pack.ordered_items()` gives items in position order with their Assets.
> - The builder needs a link to the public page once it exists, and the
>   pack list's cards could link there too.
> - Found while building: after Add to pack on Discover saves a result, the
>   card's Save corner still says Save until the next search; the saved
>   count does update.

### Phase 7 polish (2026-11-05, at the user's request)

Added after the phase, out of plan order, because the user asked for it.
The PRD records it as stories 95–104. Built and tested; see
docs/ARCHITECTURE.md ("Status history", "Files and bundles", "Around an
entry") and docs/FRONTEND.md.

- [x] **Files told apart:** `catalog/files.py` gives each variant its
  resolution, format and package, and each file its map type. The drawer
  badges them and filters by resolution and format in the page.
- [x] **Download defaults:** `DownloadPreferences` (resolution, a format per
  kind, the texture maps) on the Settings page, each group saving on change.
- [x] **Download bundle:** `pick_bundle()` chooses the files. One file is a
  plain link; several are fetched and zipped by the browser with a
  CREDITS.txt. The Toolbox never touches a file, so the PRD's Out of Scope
  holds. Checked by hand against real Poly Haven files (CORS `*`): the zip's
  CRCs verify.
- [x] **Centred full page** with Similar in your library, Featured in public
  packs and Find more on Discover (also after the entry in the drawer).
- [x] **Status history:** `StatusChange` records who set each status, when,
  via the website or the API, and an optional reason, shown under the
  status chips with the history. The API reads and writes it too.
- [x] **Folding Tags:** the first 8 show, the rest fold behind "Show N more",
  remembered in the browser and opened by a chosen tag.
- [x] **The mark on every page**, above the glow, and in the drawer.
- [x] **Ambient glow:** random organic blobs through the whole page in place
  of the symmetrical hero and footer glows.
- [x] **Fixed on the way:** the page could scroll past the shell into empty
  space. Side-panel chips now hold their hidden inputs.
- [x] **Water drops** (second request the same day): the glow's blobs are
  460–980 px drops that sink and rise slowly and wobble like water, with two
  shells following a beat behind.
- [x] **No giant watermark:** the footer's full-width wordmark is removed.
  Pinned in view, it was cut off behind the content, so the user's fallback
  (remove it) applied.
- [x] **Lava lamp** (third request): bigger (620–1300 px), looser and
  faster drops that rise and fall a long way, stretching tall as they travel
  and squashing wide as they turn.
- [x] **Fixed:** the Appearance chips seemed to do nothing because the
  browser ran a cached `shell.js`. The stylesheet and scripts now carry
  `?v=<last change>`. The Account pages are centred.
- [x] **Light and dark by hand:** System, Light or Dark from the title bar's
  switch or Settings, kept in the `ax-theme` cookie (`accounts:theme` without
  JavaScript). Tested: CSRF, POST only, unknown choices refused, and the
  return address kept on this site.
- [x] Standard gate (see top). Access rules: the download defaults need
  sign-in and CSRF and never touch another member's; a status reason is a
  404 on another member's entry and needs CSRF; similar entries never come
  from another library, and featuring packs are never private.

> **For Phase 8:** "Featured in public packs" lists pack titles without
> links, because `/packs/<slug>/` doesn't exist yet. Link each one to its
> public page. The pack export could also offer the member's default
> variant (`pick_bundle()`), but the PRD's manifest uses each item's
> `preferred_variant`, so leave that as it is unless the user asks.

---

## Phase 8: Public pack page, export and pack API

**User stories:** 44, 51, 52, 53, 57, 58, 59, 60, 69, 70, 71

### What to build

**Public page.** The page at `/packs/<slug>/` lists a pack's items with
their licenses and attribution. Anyone can read a public pack, including
signed-out visitors. Other members see it read-only, and the owner also
gets a link to the builder. A private pack returns 404 to everyone except
its owner.

**Export.** One manifest builder makes the Option A manifest as the PRD
specifies:

- `format: "axcenity-pack"` and `version: 1`
- the pack object, the items in `position` order, and `credits` for
  every item that isn't CC0
- `<kind>s/<external_id>/` as the default import path

The pack page downloads the manifest as a JSON file.

**Pack API:**

- `GET /api/packs/` lists public packs plus the caller's own. `?mine=1`
  lists only the caller's and needs sign-in.
- `GET /api/packs/{id}/` returns read-only pack detail.
- `GET /api/packs/{id}/export/` returns the manifest.

The public serializer carries only PackItem and Asset fields.

### Acceptance criteria

- [x] A golden-file test locks the manifest's shape. It freezes
  `exported_at` and compares the whole document field for field.
- [x] The manifest:
  - lists each item's chosen variant's files with `url`, `filename` and
    `size`, plus `total_size`
  - puts every non-CC0 item's attribution in `credits` exactly once, and
    leaves CC0 items out of `credits`
  - gives a blank import path the `<kind>s/<external_id>/` default
- [x] The website download and the API export return the same manifest.
- [x] A sentinel test puts known text in the owner's notes and sets a
  rating and status. That text and those values never appear in the
  public page, the API detail, the API list or the export.
- [x] A non-owner viewing a public pack sees no edit controls.
- [x] POST, PUT, PATCH and DELETE on the pack API return 405.

### Completion gate

- [x] Standard gate (see top). Access rules: every pack row of the PRD's
  access table is tested on the website and the API.
  - A private pack's page, detail and export return **404** to signed-out
    visitors and to other members, and work for the owner.
  - A public pack's page, detail and export work for everyone.
  - The API list never includes another member's private packs.
  - `?mine=1` is refused when signed out.
  - *(User request, 2026-11-05.)* An explicit test: a private pack's export,
    on the website and the API, is a **404** to a signed-out visitor and to
    another member, and works for the owner.

> **Built as (2026-11-05):** `Pack.objects.visible_to(user)` is the one
> reader rule, and `build_manifest()` (`packs/manifest.py`) the one export,
> through `manifest_for()` for the page's download and the API alike. The
> website download is `/packs/<slug>/export/` (`<slug>.axcenity-pack.json`).
> A stored variant label the Asset doesn't list falls back to the default
> variant; an asset with no variants exports `variant: null`. A non-CC0 item
> with no attribution is credited as `"<title>" by <author>, <license>`. The
> API list pages by 12 in the library API's shape. `new` and `picker` are
> never given as slugs. The builder, the pack cards and "Featured in public
> packs" link to the pack page. The pack page keeps the community rating off.
>
> **For Phase 9:** the gallery's cards can link to `pack.get_public_url()`,
> and `filter_public_packs()` should start from `Pack.objects.public()`
> (not `visible_to()`, which adds the member's own private packs). Still open
> from Phase 7: after Add to pack on Discover saves a result, its Save corner
> still says Save until the next search.

### Phase 8 polish (2026-11-05, at the user's request)

Added after the phase. The PRD records it as stories 105 and 106, a
`visibility` field in place of `is_public`, and three rows of the access
table.

- [x] **Unlisted packs:** a pack is Private, Unlisted or Public (three chips in
  the builder; `Pack.visibility`, migration `0002` keeps public packs public).
  Unlisting a pack the first time makes its share link,
  `/packs/link/<token>/` (128 random bits, `secrets.token_urlsafe`), with its
  download at `…/export/`. Anyone holding the link can view and export it,
  signed in or not. The link is kept through later visibility changes.
- [x] **Never listed:** for everyone but the owner, an unlisted pack is a 404 by
  slug and id (the pack page, its download, the API detail and export), and
  the API list, "Featured in public packs" and `Pack.objects.public()` never
  hold it. The manifest's `source_url` and the API's `page_url` are the share
  link. Share pages say `X-Robots-Tag: noindex, nofollow`, and the site's
  `Referrer-Policy: same-origin` keeps the token from leaving in a Referer.
- [x] **New link:** the builder shows the link with Copy link and New link. New
  link asks first, then replaces the token (`rotate_share_token()`), so every
  older link is a 404 at once. Owner only (404 otherwise), POST, CSRF.
- [x] A private pack's link is a 404, even for the owner; a public pack's link
  goes to its page. `link` joins the reserved slugs.
- [x] Standard gate (see top). Access rules: every new row of the PRD's access
  table, on the website and the API; New link in the Phase 7 pack-write checks
  (sign-in, 404, CSRF); a sentinel over the share link's page and download.

> **For Phase 9:** the gallery starts from `Pack.objects.public()`, which never
> holds an unlisted pack. **For Phase 11:** decide whether Copy pack works from
> an unlisted pack's share link; the PRD says "copy a public pack".
> **For Phase 12:** the hero's thumbnails come from `public()` packs only.

### Phase 8 polish, second request (2026-11-05, at the user's request)

Added after the phase, out of plan order. The PRD records it as stories
107–113. See docs/ARCHITECTURE.md ("Packs", "Downloads", "Licenses and
credits") and docs/FRONTEND.md ("Packs", "Attribution center").

- [x] **Add from my library:** entries already in the pack are hidden by
  default ("N already in this pack are hidden."), with "Show ones already in
  this pack" to bring them back marked "In pack". Hidden entries are left out
  before paging (`filter_library(..., exclude_entries=)`). Previous and Next
  arrows page through 12 at a time, keeping the page across an Add. Each row
  has the asset's thumbnail (a bigger preview on hover), type, provider and
  license.
- [x] **Drag and drop:** each item has a grip; dropping posts the new order to
  `packs:items_reorder` (`reorder_items()`, one transaction). An order that
  doesn't name every item exactly once (a stale page) is a 400 that changes
  nothing. Move up and Move down stay for the keyboard.
- [x] **Auto sort:** Type, Title A–Z, Provider or License (no credit needed
  first), `packs:items_sort` (`sort_items()`, one transaction, ties by title
  then id).
- [x] **Variant dropdown styled:** `.ax-select` (no native arrow, the chevron
  icon, options on the panel colours), each option with its file count and
  size.
- [x] **Download files:** the whole pack in one zip, each file under its
  item's import path, with CREDITS.txt and the manifest at the top; and
  **Download** for one item (a plain link when it's one file). The Toolbox
  serves only the providers' URLs (`packs:files`, `packs:shared_files`, the
  pack page's reader rule); the browser fetches and zips them, as story 97's
  bundle does, so the PRD's Out of Scope holds. Over 2 GB, or no files, says
  so instead.
- [x] **Credits explained:** the pack page groups items by license
  (`pack_credits()`), each with what it allows, "How to meet it", its items
  and their credit lines; warnings for non-commercial, no-changes,
  share-alike and unknown licenses; the text to paste with Copy (the same as
  CREDITS.txt); and optional thank-you lines for CC0 items. The required
  lines are exactly the manifest's `credits`; the manifest is unchanged.
- [x] **Attribution center** (`/attribution/`, a new sidebar tab): every
  license in plain words (`catalog/licenses.py`), a table at a glance, how to
  credit and optional credits, for everyone; for members, the licenses in
  each of their packs and a lookup over their own library. Its own drop
  colours. The drawer's License links to the license's card.
- [x] **Import path explained:** "What's an import path?" with an example
  project tree on the builder and the pack page, and a hint under each
  item's field.
- [x] Standard gate (see top). Access rules: reorder and sort join the pack
  writes (sign-in, 404 for another member's pack, CSRF); a private pack's
  files are a 404 to anyone but the owner, an unlisted pack's come only
  through its share link (noindex); an item from another pack is a 404; the
  files never carry the owner's notes, rating or status; the lookup needs
  sign-in and lists only the member's own entries, and the center only their
  own packs.

> **Not checked in a browser this session:** dragging, the zips and the hover
> preview are covered by the server-side tests and a JavaScript parse, not by
> driving a real browser. Try them by hand before Phase 9.

**Third request, the same day** (PRD stories 114–116):

- [x] **Separate pages:** the Attribution center is the license guide
  (`/attribution/`, everyone), Pack attribution (the member's packs) with a
  page per pack (`/attribution/packs/<slug>/`, the pack page's reader rule,
  and `/packs/link/<token>/attribution/` by share link), and Asset
  attribution (the member's library) with a page per asset
  (`/attribution/assets/<id>/`, own entries only). Views in
  `packs/attribution.py`. The pack page's credits are now a summary linking
  to the pack's attribution.
- [x] **A formal notice:** `PackCredits.notice()`, the Attribution and License
  Notice: who owns the assets, the required attribution, each license's terms
  as You may / You must / You may not (`LicenseInfo.permits`, `.requires`,
  `.prohibits`), the restrictions in force, optional acknowledgements and a
  disclaimer. It's CREDITS.txt in every download and the text to copy, beside
  the credit lines alone for a credits screen. Every license card shows the
  same three lists.
- [x] **Filters:** Asset attribution filters by license type and credit
  requirement (chips with counts, both must match, with the search), kept in
  the address and across pages (`filter_library(licenses=)`,
  `license_filter()`, `license_choices()`).
- [x] Standard gate (see top). Access rules: a pack's attribution follows the
  pack page (a private pack a 404 to anyone else, an unlisted one only by
  link, noindex), never shows the owner's review, and links to asset pages
  for the owner only; the pack and asset lists need sign-in and hold only the
  member's own; another member's asset page is a 404.

**Fourth request, the same day** (PRD stories 117–119):

- [x] **License compatibility:** `LicenseInfo.use_status()` and `.uses` give a
  verdict (usable, with conditions, not usable) for commercial, personal and
  internal use; `PackCredits.compatibility` takes the most restrictive per use,
  with the items that limit it, and `blocked_uses` drives the warning ("This
  pack may not be usable for commercial use."), which tells the owner to edit
  the pack and anyone else to contact the owner. On the pack page, the pack's
  attribution, the builder (rechecked with every change to the list) and the
  pack attribution list; the notice gains "3. Permitted uses".
- [x] **Iconography:** a symbol per license element (`SYMBOLS`, `lic-*` icons),
  a legend, the three use icons, and a check, warning sign or cross for each
  verdict, always with the words beside it (monochrome).
- [x] **Layout:** one license per row in the guide, its table showing each
  use's verdict; every Attribution page centred.
- [x] Standard gate (see top). Access rules: unchanged; the warning names the
  owner's username only, as the pack page already does.

### Phase 8 polish, third request (2026-11-06, at the user's request)

Added after the phase, out of plan order. The PRD records it as stories
120–125. See docs/FRONTEND.md ("Page widths", "Packs", "Discover",
"Attribution center") and docs/ARCHITECTURE.md ("Discover's drawer and
filters").

- [x] **Consistent layout:** the pack page, New pack and the Remove confirm are
  centred columns like the entry, Attribution and Account pages; the rule is
  written down in docs/FRONTEND.md ("Page widths") for every page to come.
  Thumbnails sit in the middle of their rows on the pack page, the builder
  and Asset attribution, as in the other thumbnail lists, with whole frames
  (the grip beside its thumbnail, no empty status band).
- [x] **License guide:** the verdict key's "Not usable" sits on one line like
  the others; "On this page" folds the eleven licenses into one "Licenses" row
  (remembered); every side-panel row and filter group has an icon.
- [x] **Discover licenses:** each card shows its license's symbols and, in its
  details, whether commercial use is allowed. The side panel filters by
  license and by commercial use (`DiscoverFilters`, `clean_filters()`),
  carried on every shelf, tile and Shuffle link and cached apart. CC0-only
  providers (`LICENSES = ("cc0",)`) are kept or dropped with no request;
  Openverse is asked for the allowed licenses (`search_records(licenses=)`).
- [x] **Discover drawer:** a result's title opens `catalog:discover_asset` in a
  drawer (a page without HTMX): View on <provider> as the primary action,
  Save (`slot=drawer`), Add to pack, the license with "Can I use it?", tags
  and the provider's downloads. It reads the stored Asset when anyone saved it,
  else `fetch_record()` cached for an hour (`catalog/preview.py`), and saves
  nothing. Each card also keeps View on <provider> in its corner.
- [x] **Packs as a list:** a Grid / List switch on Your packs, remembered in
  the session (`pack_layout()`).
- [x] **Sounds everywhere:** library cards, the library drawer, builder items
  and pack page items play a sound's first stored file (`Asset.preview_url`),
  through the same player as Discover (`[data-sound-card]`).
- [x] Standard gate (see top). Access rules: the drawer is open to visitors
  like Discover, a bad provider or ID is a 400 before any provider call, it
  never writes, and "In your library" reflects only the caller's own library.

---

## Phase 9: Main page, public gallery and demo data

**User stories:** 48, 49, 50, 80, 81

### What to build

**Main page.** `/` explains the site to signed-out visitors in four
steps (01 Discover · 02 Save · 03 Pack · 04 Export), with Sign up and
Sign in buttons. The side panel starts collapsed on this page.

**Gallery.** `filter_public_packs()` serves the gallery of public packs:

- search by title and tags
- filter to packs containing a type
- sort by newest or most items
- 12 per page

It uses the same HTMX swaps and `hx-push-url` as the library. Each card
shows a mosaic of the first 4 thumbnails, the title, the owner, the tags
and a count by type, such as "3 textures · 1 HDRI · 2 sounds".

**Demo data:**

- A capture script, run once by hand, saves about 40 real assets across
  the four types as a committed snapshot.
- `seed_demo` loads that snapshot offline. It creates 3 demo users,
  about 6 themed public packs, and library entries with varied statuses
  and ratings. It's safe to run repeatedly.

**README.** It covers setup, running (including the Tailwind build),
testing, Ruff, the demo sign-in details, and using the API with a token.

### Acceptance criteria

- [x] Signed-out visitors see the four steps and both buttons. Members
  don't see the sign-up prompt.
- [x] Unit tests cover `filter_public_packs()` for search, the type
  filter, both sorts and pagination.
- [x] The gallery never shows a private pack.
- [x] The mosaic uses the first 4 items by position. The type count reads
  correctly for singular and plural, and for types with no items.
- [x] `seed_demo` runs under the network guard without touching it.
- [x] Running `seed_demo` twice leaves the same row counts as running it
  once.
- [x] The demo credentials are obviously demo values and match the
  README.
- [x] Every Tier 1 feature can be tried against the seeded data with all
  providers offline. The only exception is Discover, which shows its
  error alerts.
- [x] Following the README from a fresh clone, through setup, seeding,
  the server and the tests, works without extra steps.

### Completion gate

- [x] Standard gate (see top). Access rules: the main page and the
  gallery work signed out. Gallery parameters can't surface private
  packs.
- [x] Tier 1 sign-off: every acceptance criterion from Phases 1–9 still
  holds.

> **Built as (2026-11-06):** the gallery is on `/` (`packs:home`) with its
> controls in the page's toolbar (search, one type, Newest or Most items),
> because the side panel starts collapsed there; `HomeView` sets
> `panel_start`, which `base.html` and `shell.js` read, and every other page
> keeps the member's own choice. "Newest" is `created_at` (no "made public
> at" field). The four steps show to visitors only, and the hero's Sign up
> and Sign in stay the page's buttons. The demo is 43 real assets (captured
> live by `capture_demo_assets`, committed as `packs/demo_assets.json`),
> `demo_mira`, `demo_otto` and `demo_juno` (password `toolbox-demo`), six
> public packs and one private one; `seed_demo` restores the demo packs on a
> second run and keeps members' own entry edits. The README was followed in
> a fresh copy of the working tree (sync, migrate, seed twice, Tailwind
> build, the tests, the server); a `git clone` can't be tried until it's
> committed. The headless screenshot showed the type icons, not the
> thumbnails (lazy images load after it's taken); the URLs answer, so check
> the thumbnails by hand.
>
> **For Phase 10:** "Find more from providers" can reuse
> `catalog.discover.discover_url()`, as the entry page's Find more does.
> **For Phase 11:** the demo packs are a ready source for Copy pack.
> **For Phase 12:** the hero's thumbnails can come from `gallery_items` of
> `Pack.objects.public()` packs. **Still open from Phase 7:** after Add to
> pack on Discover saves a result, its Save corner still says Save until the
> next search.

---

# Tier 2: Signature

## Phase 10: Suggestions and "Find more from providers"

**User stories:** 45, 46, 47

### What to build

The builder shows "Suggested for this pack": local Assets ranked by how
many tags they share with the pack, leaving out assets already in it.
Adding a suggestion that isn't in the owner's library first saves it
there as To review, then calls `add_to_pack()`. "Find more from
providers" opens Discover with a search built from the pack's tags.

### Acceptance criteria

- [x] Suggestions are ranked by shared-tag count, highest first. Assets
  with no shared tags and assets already in the pack are left out.
- [x] Ties on shared-tag count break by title A–Z, then by id, so the
  order is stable. The ranking test checks the groups of equal count in
  order, not the order inside a group.
- [x] Adding a suggestion the owner hasn't saved creates a To review
  SavedAsset. Adding one they have saved reuses it untouched.
- [x] "Find more" builds its query from the pack's tags. A pack with no
  tags shows a hint instead of an empty search.

### Completion gate

- [x] Standard gate (see top). Access rules: suggestions and their add
  URLs return **404** for another member's pack and send signed-out
  visitors to sign in. Adding a suggestion needs a valid CSRF token.

> **Built as (2026-11-06):** `packs/suggestions.py` holds `suggest_assets()`
> (the top 8, reading only Asset and Tag rows) and `find_more()`;
> `add_suggestion()` is in `packs/services.py`. At the user's request, adding a
> suggestion never calls a provider: `catalog.library.save_asset()` (now shared
> by `save_to_library()`) creates or reuses the entry from the stored Asset,
> and `add_to_pack()` follows in the same transaction. The saved count goes
> out of band only when a new entry was made. A tags save sends
> `packTagsChanged`, item changes `packItemsChanged`, kept separate; the
> suggestions listen for both. The section sits under the items, so Add from
> my library keeps the sticky right column. Find more searches up to 2 of the
> pack's tags (the most used across stored assets first, then A–Z, as the
> entry page does) for the pack's main type (textures when empty). In the
> demo data, Castle Siege and Golden Hour Skies have no matching assets, so
> they show "No other assets share this pack's tags yet."

---

## Phase 11: Save single items and Copy pack

**User stories:** 55, 56

### What to build

On a public pack page, signed-in members can save single items to their
library, using the same "In library" behaviour as Discover. "Copy pack"
runs in one database transaction and:

- creates a private pack titled "<original title> (copy)" with
  `copied_from` set
- copies the tags
- adds missing assets to the copier's library as To review
- leaves existing SavedAssets untouched
- copies each item's variant, import path and position

Copying is website-only.

### Acceptance criteria

- [x] Saving a single item creates a To review SavedAsset, or shows "In
  library" if the member already has it.
- [x] The copy is private, has the right title and `copied_from`, and
  matches the original's items, variants, import paths and order.
- [x] Copying never changes the copier's existing SavedAssets.
- [x] If a failure is forced partway through, the copy leaves no pack, no
  items and no new SavedAssets behind (transaction test).
- [x] The API has no copy URL.

### Completion gate

- [x] Standard gate (see top). Access rules:
  - Saving an item or copying a pack sends signed-out visitors to sign
    in.
  - Copying another member's private pack returns **404**.
  - Both actions need a valid CSRF token.

> **Built as (2026-11-06):** `copy_pack()` and `copy_title()` are in
> `packs/services.py`; Save is `catalog.library.save_asset()` on the item's
> stored Asset, so neither ever calls a provider. Both use the pack page's
> reader rule (`PackReaderWriteMixin`): anyone signed in who can read the pack,
> the owner included. At the user's request, an unlisted pack's readers save
> and copy through its share link (`packs:shared_save_item`,
> `packs:shared_copy`); by slug it stays a 404. The copy also keeps the
> intended use, gets no share token, and the title is shortened to fit
> " (copy)". Copy pack confirms first, saying how many assets would join the
> library, then opens the copy's builder, which says "Copied from …" (linked
> only when the original is readable by slug). The pack page's "read-only"
> tests now allow these two forms and no other control.
>
> **Still open from Phase 7:** after Add to pack on Discover saves a result,
> its Save corner still says Save until the next search.

---

## Phase 12: Orbit hero and scroll ruler

**User stories:** 54, 78

### What to build

The main page gets an animated hero: about 18 random thumbnails from
assets in public packs, orbiting on rings coloured by type. Clicking one
opens its pack. With fewer than 6 such assets, type-icon tiles show
instead.

The main page and Discover also get a right-edge scroll ruler with a
section index.

### Acceptance criteria

- [x] Hero thumbnails come only from assets in public packs, and each one
  links to a public pack that contains it.
- [x] With fewer than 6 such assets, the type-icon tiles show instead.
- [x] Ring colours use only the four type colours. The logo never sits on
  a thumbnail.
- [x] The ruler's section index jumps to each section on the main page
  and on Discover.

### Completion gate

- [x] Standard gate (see top). Access rules: a test proves that no asset
  from a private pack can reach the hero.

> **Built as (2026-11-06):** `packs/hero.py`'s `hero_orbit()` reads the distinct
> Assets of `Pack.objects.public()` packs only (unlisted ones are left out too),
> and each tile links to the newest public pack holding its asset. At the
> user's request the 18 are picked from each type in turn (so textures can't
> crowd out the rest), the busiest ring is outermost, nothing in the orbit is a
> logo (a panel-coloured disc hides the page's faint mark behind the rings),
> hover and keyboard focus pause it, reduced motion stills it, the ruler works
> through plain `#anchors` without JavaScript, and it shows only from 80 rem
> (`xl`), where ruler pages get a 6 rem right gutter. The fallback is four
> rings, one type-icon tile each, opening Discover for that type. The orbit's
> counts sit in a note under the legend (in the centre they collided with the
> inner ring). Checked in headless Firefox, light and dark, at 1600, 1100 and
> 420 px against a scratch copy of the seeded demo.

### Phase 12 polish (2026-11-06, at the user's request)

Added after the phase. It goes beyond the PRD's ruler on "the main page and
Discover".

- [x] **Ruler on every page:** the ruler is in `base.html`, a full-height scale
  after Artcraft's (minor ticks, numbered majors, a cursor), with each page's
  section index in `{% block ruler_sections %}` (Top and End by default). The
  content and footer keep a 6 rem gutter from 80 rem.
- [x] **Hero after Artcraft's:** the text centred in front, the rings big behind
  it (grey guide rings for depth, the type rings 44–86 %), bigger tiles further
  out, faded at the top and bottom and cropped at the page's sides.
- [x] **Textures with no background:** textures and models float as cut-outs
  (their transparent renders, no tile, a shadow that follows the shape); HDRIs
  stay framed.
- [x] The page's faint mark stays on the main page but moves below the hero, so
  it never sits among the thumbnails (the 2026-11-05 "mark on every page" test
  still holds).
- [x] Standard gate (see top). Access rules: unchanged; the ruler is chrome and
  shows nothing from anyone's library.

**Second request, the same day:**

- [x] **Textures only:** the hero shows only textures from public packs (they
  look the best), up to 18 on up to three texture rings (`ring_counts()`, the
  busiest outermost); the fallback is six texture-icon tiles opening Discover's
  textures. This replaces the first request's "spread across every type".
- [x] **A cover:** the hero fills the first screen (the window less the title and
  status bars); the rings are faint (40 % lines), and the orbit fades into the
  page down its lower half.
- [x] **No caption:** the legend and the count line are gone.
- [x] **Fixed on the way:** a texture in two public packs was counted twice
  (PackItem's default ordering defeated `DISTINCT`), which could tip the 6-texture
  threshold; caught by the TDD 3 test.
- [x] Standard gate (see top). Access rules: unchanged; a test still proves no
  private or unlisted pack's texture reaches the hero.

> **For Phase 13:** the orbit and the ruler already turn their motion off under
> reduced motion; Phase 13's sweep should keep them in its list. **Still open
> from Phase 7:** after Add to pack on Discover saves a result, its Save corner
> still says Save until the next search.

---

## Phase 13: Branding motion and reduced motion

**User stories:** 77, 79

### What to build

The site gets its motion, all in CSS plus a little plain JavaScript:

- the wordmark wipes in and gets a periodic shine sweep
- the tile cuts in on load
- a parallax watermark sits behind the content
- the logo-mark loader replaces spinners as the HTMX indicator
- a cursor spotlight on cards and tiles
- staggered blur-up entry for cards
- View Transitions on HTMX swaps

> **Already in place (Phase 1 polish, 2026-10-31):** boosted swaps already
> run as View Transitions. The content fades and rises, and the current-page
> marks glide between items, with reduced motion turning it off (see
> docs/FRONTEND.md, "Page transitions"). This phase only needs to extend
> them to HTMX fragment swaps.

When the system asks for reduced motion (`prefers-reduced-motion`), all
of it is turned off.

### Acceptance criteria

- [x] Every HTMX loading state uses the logo loader, and no spinner
  classes are left.
- [x] With reduced motion on, no animation or transition runs, and the
  content still appears in its final state.
- [ ] Motion works in a current browser and degrades cleanly where View
  Transitions aren't supported.
- [x] Every page from earlier phases still renders, and the HTMX tests
  still pass.

### Completion gate

- [x] Standard gate (see top). Access rules: no access rule changes, and
  every earlier access test passes untouched.

> **Built as (2026-11-06):** CSS ("Motion" in `styles/source.css`) plus
> `static/js/motion.js`; see docs/FRONTEND.md, "Motion". Two PRD items met
> later user requests, so they were adapted: the icon tile that "cuts in" left
> the activity bar, so the page's faint mark cuts in instead; and the "giant
> parallax watermark" would undo story 104, so the parallax moves that same
> mark (CSS scroll-driven, behind `@supports`). The intros play on a full load
> only (`data-booted`). The loader is `partials/loader.html`: the status bar's
> mark sweeps while any htmx request runs (after 150 ms), and a pending shelf,
> Load more, the pack picker and the drawer's Saving show it in place. A card's
> corner squares keep their pulse, because they sit on the provider's thumbnail,
> where the logo never goes. Fragment swaps, which already ran the page's drop
> and rise, now crossfade in place (`html[data-swap="fragment"]`); boosted
> navigation keeps the rise. Reduced motion is one blanket rule on top of the
> old list, and every entry animation ends on the element's resting style.
> Checked in headless Firefox (1600 px, light) with and without
> `ui.prefersReducedMotion`: the gallery's cards, the wordmark and the mark end
> in place, with nothing covering the content.
>
> **Left unticked:** "Motion works in a current browser". The fallbacks are
> covered by tests, but a headless screenshot only shows the end state, so the
> moving parts (the wipe, the shine, the spotlight, the stagger, the crossfade,
> the parallax in Chrome) need a look in a real browser.
>
> **Still open from Phase 7:** after Add to pack on Discover saves a result,
> its Save corner still says Save until the next search.
