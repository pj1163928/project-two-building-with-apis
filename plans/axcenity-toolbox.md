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

- [ ] Each type shows exactly the providers in the PRD mapping, and
  passes each provider the right filter.
- [ ] The Discover page renders without waiting for any provider. Each
  shelf loads through its own request.
- [ ] Each result shows a thumbnail, title, author and license, with at
  most 12 per shelf. Uneven counts between providers display as returned.
- [ ] A Poly Haven search with `keywordMatches == 0` shows an empty shelf
  with a "no matches" message, not an error.
- [ ] A failed shelf shows the friendly `ProviderError` message, never a
  raw response body or traceback, plus a Retry button. Retry re-requests
  only that shelf's URL.
- [ ] Pressing `/` focuses the search unless the cursor is already in a
  text field.
- [ ] An unknown type or provider in a shelf URL is rejected without
  calling any provider.
- [ ] **Provider client tests:** `responses` tests cover each provider's
  `search_records()` on a normal response. They check that every
  `AssetRecord` field is filled in.
- [ ] **Application tests:** tests replace `search_records` with
  `monkeypatch` for a normal shelf, an empty shelf and a `ProviderError`
  shelf.
- [ ] **HTMX mixed shelves:** a test makes one provider raise
  `ProviderError` and the other succeed for the same search. The failed
  shelf's fragment contains the alert and the Retry button, the other
  shelf's fragment contains its results, and neither request affects the
  other.

### Completion gate

- [ ] Standard gate (see top). Access rules: Discover and its shelf URLs
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

- [ ] A repeated identical search within the hour calls the provider
  once. Searches that differ only in case or whitespace share one cache
  entry.
- [ ] A failed search followed by Retry calls the provider again, and a
  success on Retry is shown and cached.
- [ ] Poly Haven info is cached for 12 hours, wherever it's fetched.
- [ ] Each shelf shows its provider's credit line.
- [ ] A result with no thumbnail URL shows the type icon. A thumbnail
  that fails to load is swapped for the type icon, and the logo never
  appears on a thumbnail.
- [ ] After a shelf succeeds or fails, the status bar shows that
  provider's status. Providers not yet used show as unknown.
- [ ] **Provider client tests (`responses`):** each of these gives its
  own friendly `ProviderError` message, and none leaks HTML or exception
  text:
  - a timeout
  - a connection error
  - a 429
  - Openverse's 500 with an HTML body
  - Poly Haven's 404
  - Poly Haven's `keywordMatches == 0`, which counts as no results, not
    an error
- [ ] **Application tests (`monkeypatch`):** each failure message reaches
  the shelf alert unchanged, and failures never reach the cache.
- [ ] **HTMX mixed shelves:** the Phase 2a test runs once for each failure
  type. In every case one shelf shows the alert and Retry while the other
  shows its results.

### Completion gate

- [ ] Standard gate (see top). Access rules: Discover is still open to
  signed-out visitors, and the status bar shows no member data to them.

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

- [ ] The first save of an asset calls `fetch_record()` and creates one
  Asset with its tags normalized. A second user saving the same asset
  reuses the Asset and doesn't call `fetch_record()`.
- [ ] Saving an asset the member already has creates no second
  SavedAsset, and the result shows "In library".
- [ ] If `fetch_record()` raises `ProviderError`, the friendly message
  replaces the button and nothing is saved.
- [ ] A new SavedAsset starts as To review with no rating.
- [ ] `normalize_tag()` unit tests cover each rule:
  - case and surrounding whitespace
  - collapsed inner whitespace
  - number-only tags dropped
  - a simple plural "s" removed
  - words ending in "ss" kept
- [ ] Deleting a SavedAsset leaves the shared Asset in place (model-level
  test).
- [ ] The library grid renders from local data while every provider
  function is patched to raise.
- [ ] Thumbnails link to the provider URL and are never downloaded.
- [ ] `responses` tests cover each provider's `fetch_record()`, including
  the variants and the Poly Haven file URLs.

### Completion gate

- [ ] Standard gate (see top). Access rules:
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

- [ ] Unit tests cover `filter_library()` for each search field, each
  filter, each sort, pagination and combinations of these.
- [ ] `filter_library()` never returns another user's entries, whatever
  the parameters.
- [ ] Sorting by rating puts unrated entries last. Unknown sort or filter
  values fall back to the defaults instead of failing.
- [ ] An HTMX request returns only the results fragment. A normal request
  for the same query string returns the full page in the same state.
- [ ] The pushed URL holds the search, filters, sort and page.
- [ ] An empty library links to Discover. No matches offers to clear the
  filters.

### Completion gate

- [ ] Standard gate (see top). Access rules: the library and its fragment
  URL send signed-out visitors to sign in. Filter parameters can't expose
  another member's entries.

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

### Acceptance criteria

- [ ] An HTMX request for `/library/<id>/` returns the drawer fragment,
  and a direct visit returns a full page.
- [ ] Changing the status saves at once and updates the card behind the
  drawer through an out-of-band swap.
- [ ] Setting or clearing the rating saves at once and updates the card.
  Values outside 1–5 are rejected.
- [ ] Notes save after the debounce with no Save button, and the saved
  text survives a reload.
- [ ] The drawer renders from local data while every provider function is
  patched to raise.

### Completion gate

- [ ] Standard gate (see top). Access rules:
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
  and pages of 12.
- **Create:** takes the provider and external_id, plus optional notes,
  rating and status. It reuses the local Asset or calls `fetch_record()`.
- **Read and update:** read one entry, or update its notes, rating and
  status with PATCH or PUT. Asset fields are read-only.
- **Delete:** its documentation says the entry is also removed from the
  member's packs.

The owner serializer includes notes, rating and status.

### Acceptance criteria

- [ ] The list returns the same entries in the same order as the website
  for the same parameters.
- [ ] Create with a known Asset doesn't call `fetch_record()`. Create with
  a new Asset calls it once.
- [ ] Create returns these errors:
  - a duplicate: **400** with "Already in your library."
  - a `ProviderError`: **502** with `{"detail": <friendly message>}`
  - an unknown provider: **400**
- [ ] PATCH and PUT change only notes, rating and status. Asset fields in
  the request are ignored or rejected.
- [ ] DELETE removes the entry and leaves the shared Asset. The endpoint's
  documentation says the entry also leaves the member's packs.
- [ ] The token page shows the member's token. The token signs requests
  through `Authorization: Token <key>`.

### Completion gate

- [ ] Standard gate (see top). Access rules:
  - Unauthenticated requests are refused with 401 or 403.
  - Another user's entry returns **404** for GET, PATCH, PUT and DELETE.
  - The list only ever holds the caller's entries.
  - A session POST, PATCH or DELETE without a CSRF token is refused. The
    test client enforces CSRF checks for this test.
  - The same request signed with a token succeeds without a CSRF token.
  - The token page sends signed-out visitors to sign in.

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

### Acceptance criteria

- [ ] Typing tags "Rocks, rock, 2048,  Mossy  Stones" stores the tags
  `rock`, `mossy stone`.
- [ ] A new pack is private. The public/private switch saves at once.
- [ ] `add_to_pack()`:
  - adds an item at the end with the default variant
  - adding the same SavedAsset twice to one pack leaves a single item
  - refuses a SavedAsset that the pack's owner doesn't own
- [ ] The default variant rule is tested for a 2K JPG, an MP3, and the
  fallback to the first variant.
- [ ] One SavedAsset can sit in two packs with a different variant and
  import path in each.
- [ ] Changing a variant, an import path or the order saves through HTMX
  with no Save button.
- [ ] Remove deletes only the PackItem. The SavedAsset and the Asset
  stay.
- [ ] Deleting a SavedAsset first shows the packs it's in. Confirming
  removes its PackItems from those packs and leaves the shared Asset and
  the packs' other items alone.
- [ ] Deleting a pack removes its PackItems but none of the owner's
  SavedAssets.
- [ ] The library card's "Add to pack" dropdown lists only the member's
  own packs.

### Completion gate

- [ ] Standard gate (see top). Access rules:
  - The builder and every pack edit URL return **404** to another member
    and send signed-out visitors to sign in.
  - Adding another member's SavedAsset to your pack is refused, through
    `add_to_pack()` and through the HTMX URLs.
  - Adding your SavedAsset to another member's pack returns **404**.
  - Every pack write needs a valid CSRF token.

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

- [ ] A golden-file test locks the manifest's shape. It freezes
  `exported_at` and compares the whole document field for field.
- [ ] The manifest:
  - lists each item's chosen variant's files with `url`, `filename` and
    `size`, plus `total_size`
  - puts every non-CC0 item's attribution in `credits` exactly once, and
    leaves CC0 items out of `credits`
  - gives a blank import path the `<kind>s/<external_id>/` default
- [ ] The website download and the API export return the same manifest.
- [ ] A sentinel test puts known text in the owner's notes and sets a
  rating and status. That text and those values never appear in the
  public page, the API detail, the API list or the export.
- [ ] A non-owner viewing a public pack sees no edit controls.
- [ ] POST, PUT, PATCH and DELETE on the pack API return 405.

### Completion gate

- [ ] Standard gate (see top). Access rules: every pack row of the PRD's
  access table is tested on the website and the API.
  - A private pack's page, detail and export return **404** to signed-out
    visitors and to other members, and work for the owner.
  - A public pack's page, detail and export work for everyone.
  - The API list never includes another member's private packs.
  - `?mine=1` is refused when signed out.

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

- [ ] Signed-out visitors see the four steps and both buttons. Members
  don't see the sign-up prompt.
- [ ] Unit tests cover `filter_public_packs()` for search, the type
  filter, both sorts and pagination.
- [ ] The gallery never shows a private pack.
- [ ] The mosaic uses the first 4 items by position. The type count reads
  correctly for singular and plural, and for types with no items.
- [ ] `seed_demo` runs under the network guard without touching it.
- [ ] Running `seed_demo` twice leaves the same row counts as running it
  once.
- [ ] The demo credentials are obviously demo values and match the
  README.
- [ ] Every Tier 1 feature can be tried against the seeded data with all
  providers offline. The only exception is Discover, which shows its
  error alerts.
- [ ] Following the README from a fresh clone, through setup, seeding,
  the server and the tests, works without extra steps.

### Completion gate

- [ ] Standard gate (see top). Access rules: the main page and the
  gallery work signed out. Gallery parameters can't surface private
  packs.
- [ ] Tier 1 sign-off: every acceptance criterion from Phases 1–9 still
  holds.

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

- [ ] Suggestions are ranked by shared-tag count, highest first. Assets
  with no shared tags and assets already in the pack are left out.
- [ ] Ties on shared-tag count break by title A–Z, then by id, so the
  order is stable. The ranking test checks the groups of equal count in
  order, not the order inside a group.
- [ ] Adding a suggestion the owner hasn't saved creates a To review
  SavedAsset. Adding one they have saved reuses it untouched.
- [ ] "Find more" builds its query from the pack's tags. A pack with no
  tags shows a hint instead of an empty search.

### Completion gate

- [ ] Standard gate (see top). Access rules: suggestions and their add
  URLs return **404** for another member's pack and send signed-out
  visitors to sign in. Adding a suggestion needs a valid CSRF token.

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

- [ ] Saving a single item creates a To review SavedAsset, or shows "In
  library" if the member already has it.
- [ ] The copy is private, has the right title and `copied_from`, and
  matches the original's items, variants, import paths and order.
- [ ] Copying never changes the copier's existing SavedAssets.
- [ ] If a failure is forced partway through, the copy leaves no pack, no
  items and no new SavedAssets behind (transaction test).
- [ ] The API has no copy URL.

### Completion gate

- [ ] Standard gate (see top). Access rules:
  - Saving an item or copying a pack sends signed-out visitors to sign
    in.
  - Copying another member's private pack returns **404**.
  - Both actions need a valid CSRF token.

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

- [ ] Hero thumbnails come only from assets in public packs, and each one
  links to a public pack that contains it.
- [ ] With fewer than 6 such assets, the type-icon tiles show instead.
- [ ] Ring colours use only the four type colours. The logo never sits on
  a thumbnail.
- [ ] The ruler's section index jumps to each section on the main page
  and on Discover.

### Completion gate

- [ ] Standard gate (see top). Access rules: a test proves that no asset
  from a private pack can reach the hero.

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

- [ ] Every HTMX loading state uses the logo loader, and no spinner
  classes are left.
- [ ] With reduced motion on, no animation or transition runs, and the
  content still appears in its final state.
- [ ] Motion works in a current browser and degrades cleanly where View
  Transitions aren't supported.
- [ ] Every page from earlier phases still renders, and the HTMX tests
  still pass.

### Completion gate

- [ ] Standard gate (see top). Access rules: no access rule changes, and
  every earlier access test passes untouched.
