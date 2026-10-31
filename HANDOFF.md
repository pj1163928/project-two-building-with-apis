# Handoff — Write the PRD for Axcenity Toolbox

**Date:** 2026-10-30
**Next session's focus:** run `/to-prd` and write `prd/axcenity-toolbox.md`.
That skill doesn't interview the user; it synthesizes what's already known,
and this file is everything known. All of the design below was agreed in a
`/grill-me` session (29 questions plus one UI prototype). **Don't re-ask
any of it.** Don't write code yet.

## Context

- **Assignment:** CIDM 3312 Project 2 ("Building With APIs"). The
  requirements, which the PRD must trace back to:
  - **Stack:** Django, DRF, SQLite, uv, Ruff, Tailwind CSS with DaisyUI,
    HTMX and Pytest.
  - One cohesive purpose.
  - Users find items through an external API.
  - Users save items, with enough stored locally to survive the API being
    down.
  - Users add and edit their own info.
  - Users browse saved items with **search, filter, sort and pagination**
    on local data.
  - Sign-in is required to manage data, with access rules enforced on
    **both the site and the API**.
  - The app's own API does list, create, update and delete on saved
    entries.
  - The app shows useful messages when the provider fails.
- **What already exists:**
  - A finished console script, [asset_search.py](asset_search.py), plus
    the [providers/](providers/) package: ambientCG, Poly Haven and
    Openverse, with no API keys.
  - `get_json()` and `ProviderError` live in
    [providers/http.py](providers/http.py).
  - The walkthrough is in
    [docs/code-walkthrough.md](docs/code-walkthrough.md), the provider
    research in
    [docs/research/game-asset-apis.md](docs/research/game-asset-apis.md),
    and the session history in [PROMPTS.md](PROMPTS.md).
  - The previous handoff (for the console script) is in git history at
    commit `48548a6`.
- **The user:** a beginner. They built the **Axcenity** game engine (Rust +
  Lua, VSCode-inspired egui editor) at `C:\Users\Paul Janota\Desktop\Axcenity Engine`.
  The website borrows its branding and palette from there:
  - `assets/branding/` (mark, wordmark, icon tile, favicon). Its README
    says: "identity is black, white and gray only".
  - `crates/editor/src/theme.rs` (palette and accents).
  - `assets/fonts/` (Inter and JetBrains Mono).
- **Prototypes (throwaway, kept for reference):**
  - [prototypes/discover-branded.html](prototypes/discover-branded.html) is
    **the chosen Discover design**. Its header comment records the
    decision. Open the file directly in a browser.
  - [prototypes/discover.html](prototypes/discover.html) holds the three
    rejected layouts (split editor, gallery, search + preview).
- **Untracked files:** `plan.md` (empty, created by the user; leave it
  alone) and `prototypes/`. Nothing from this session is committed.

## Agreed product design

**Purpose:** Axcenity Toolbox is an asset catalog and pack creator for the
Axcenity engine. Users find free CC0/CC assets (textures, HDRIs, models and
sounds) and save them to a private library with their own notes. They
build **packs**, which are tagged project kits, and can share them
publicly. Packs export as a JSON manifest the engine can load, and the
site suggests assets that fit a pack.

### Data model (Q1–Q5, Q10, Q22, Q23)

- **`Asset`** is a shared cache, unique on `(provider, external_id)`. It
  stores:
  - `kind` (texture, hdri, model or sound)
  - title, author, thumbnail URL, tags (M2M to `Tag`)
  - license, license_url, attribution, source_url
  - `variants`: a JSON list of `{label, files: [{url, filename, size}], total_size}`
  - `fetched_at`

  It's filled by calling `fetch_record()` when an asset is first saved.
  Users **never delete** `Asset` rows.
- **`SavedAsset`** links a user to an `Asset` and holds `notes`, `rating`
  (optional, 1–5) and `status`: To review (the default), Testing, Approved
  or Rejected. It's unique per user and asset.
- **`Pack`** has:
  - an owner, title, slug, description ("intended use")
  - tags (M2M to `Tag`)
  - `is_public` (default False)
  - `copied_from` (nullable FK to `Pack`)
  - timestamps
- **`PackItem`** links a pack to the owner's `SavedAsset` and holds
  `preferred_variant` (the default is a 2K JPG, or MP3 for sounds, when
  one exists), `import_path` and `position`. Variant and import path live
  here, not on `SavedAsset`, so the same asset can differ per pack and
  private notes can never leak through a pack.
- **`Tag`** is a unique, normalized name. Every tag goes through
  `normalize_tag()`, which:
  - lowercases, trims and collapses spaces
  - drops pure numbers
  - strips a simple plural "s", except for words ending in "ss"

  Pack owners enter tags as comma-separated text.
- **Thumbnails:** we store the provider's URL and link to it directly. If
  the image fails to load, a placeholder icon for the type replaces it.
  Copies are never downloaded: Poly Haven's renders are not CC0.
- **Deleting a `SavedAsset`** cascades to its `PackItem`s:
  - **Site:** an HTMX confirm dialog lists the packs it will be removed
    from.
  - **API:** cascades, and this is documented.
  - There's no soft delete.

### Providers (Q9, Q13, Q21, Q24)

- **Type to provider:**

  | Type | Providers | ambientCG filter | Poly Haven filter |
  |---|---|---|---|
  | Textures | ambientCG + Poly Haven | `material` | `textures` |
  | HDRIs | ambientCG + Poly Haven | `hdri` | `hdris` |
  | Models | ambientCG + Poly Haven | `3d-model` | `models` |
  | Sounds | Openverse Audio | — | — |
- **Code changes:** add an `AssetRecord` dataclass plus
  `search_records(query, kind, limit=12)` and `fetch_record(external_id)`
  to each provider, **next to** the existing `search()` and
  `get_details()`. `asset_search.py` must keep working unchanged.
  - Poly Haven's current `get_details()` throws away file URLs, so the new
    code must keep them.
  - ambientCG returned only one model for "wood", so uneven results are
    normal.
- **Caching** (Django `LocMemCache`): successful search results per
  `(provider, kind, normalized query)` for 1 h, and Poly Haven
  `/info/{slug}` for 12 h. **Failures are never cached.**

### Pages (Q4, Q9, Q11, Q12, Q15–Q17, Q25, Q27)

- **Discover:**
  - Four type tiles, and a command-bar search (`/` focuses it).
  - Each provider gets its own **shelf**, which loads in a separate HTMX
    request (`hx-trigger="load"`). A failed provider shows a DaisyUI
    alert with its `ProviderError` message and a Retry button; the other
    shelf still works.
  - 12 results per provider, with no paging.
  - Each card has **Save to library**, which becomes "In library".
  - Provider credits are shown: "Powered by Poly Haven", "Made with
    Openverse", "Assets from ambientCG · CC0".
- **Library:** private, in a card grid. Filters sit in the collapsible
  side panel.
  - **Search** covers the title, tags and the user's notes.
  - **Filters:** type, provider, status, minimum rating.
  - **Sorts:** newest saved (the default), oldest, title A–Z, rating high
    to low.
  - **Pagination:** 12 per page.
  - One shared `filter_library(user, params)` serves both the page and
    the API. HTMX refreshes the results, and `hx-push-url` keeps the URLs
    bookmarkable.
  - Clicking a card opens a **slide-over drawer** at `/library/<id>/` with
    autosave:
    - status and stars save immediately; notes save after a debounce
    - it lists the packs the asset is in
    - it has Delete (with the cascade confirmation)
  - Opened directly, the same view returns a full page (via
    `request.htmx`). The card behind the drawer updates through
    out-of-band swaps.
- **Pack builder** (owner view of a pack):
  - **Items:** each has a variant dropdown, an import path and Remove, and
    each control saves on change through HTMX.
  - **Add from my library:** search-as-you-type.
  - **Suggested for this pack:** assets in the local `Asset` table ranked
    by tag overlap (`annotate(Count)`), excluding ones already in the
    pack. Adding one that isn't in the library creates a `SavedAsset`
    with status To review.
  - **Find more from providers:** a button that searches using the pack's
    tags.
  - Library cards also get an **"Add to pack" dropdown**. Both paths call
    one `add_to_pack(pack, saved_asset)` function.
- **Public pack page:**
  - Anyone can view and export it.
  - Signed-in users can **save single items** or **Copy pack**. Copying:
    - creates a private copy titled "(copy)" with `copied_from` set
    - adds missing assets to the library as To review, and leaves
      existing `SavedAsset`s as they are
    - runs in one transaction
    - is **website-only**
- **Main page** (`/`):
  - An **orbit hero**: about 18 random thumbnails from assets in **public**
    packs float on orbit rings coloured by type, and clicking one opens
    its pack. With fewer than 6 assets it shows type-icon tiles instead.
  - Signed-out visitors also see the steps "01 Discover · 02 Save · 03
    Pack · 04 Export" and Sign up / Sign in buttons.
  - Then the **public pack gallery**:
    - each card has a cover mosaic (the first 4 thumbnails), title,
      owner, tags and a summary like "3 textures · 1 HDRI · 2 sounds"
    - search covers title and tags
    - a filter for packs containing a given type
    - sorts: newest, or most items
    - 12 per page, through `filter_public_packs()`

### Access, auth and API (Q7, Q8, Q13, Q14, Q28)

- **Access rules:**
  - The library is owner-only. Requests for someone else's item get a
    **404**.
  - Packs are private by default. Public packs are visible to everyone,
    including signed-out visitors, but only the owner can edit them.
  - Public views and the export show only `PackItem` and `Asset` data,
    **never** notes, rating or status. That means separate owner and
    public serializers.
- **Auth:** Django's `LoginView`/`LogoutView`, a sign-up page using
  `UserCreationForm`, and DRF `SessionAuthentication` +
  `TokenAuthentication` (`rest_framework.authtoken`), with an API token
  page on the user's profile.
- **API:**
  - `GET/POST /api/library/` (filtered and paginated through
    `filter_library`), `GET/PATCH/PUT/DELETE /api/library/{id}/`.
  - **Create:** the request body is
    `{provider, external_id, notes?, rating?, status?}`. The server
    reuses the local `Asset` or calls `fetch_record()`.
    - A `ProviderError` returns **502** `{"detail": <friendly message>}`.
    - A duplicate returns **400** "Already in your library."
  - `GET /api/packs/` lists public packs plus your own (`?mine=1` for only
    yours). `GET /api/packs/{id}/` and `GET /api/packs/{id}/export/` are
    read-only. Packs are created and edited only on the website.
- **Export manifest:** **Option A as agreed, verbatim**:
  - Top-level fields: `format: "axcenity-pack"`, `version: 1`,
    `exported_at`, and a `pack` object with title, slug, author,
    description, tags and source_url.
  - Each item in `items[]` has: name, kind, provider, external_id,
    variant, import_path, `files[]` (`url`, `filename`, `size`),
    total_size, license, license_url, author, attribution and source_url.
  - `credits` collects the attribution of every non-CC0 item.
  - A blank `import_path` defaults to `<kind>s/<external_id>/`.
  - A golden-file test locks the shape.

### Visual design (Q16–Q17 plus the prototype)

- The shell is VSCode-style:
  - a title bar with the wordmark and "TOOLBOX"
  - an activity bar whose top item is the app icon tile (Home), then
    Discover, Library, Packs, Account and Settings
  - a collapsible side panel (it collapses on the main page)
  - a monochrome status bar showing provider status and the saved count
- **Monochrome chrome:** white primary buttons with dark text. **Colour
  only ever means asset type.** The type colours are four of the editor's
  accents: textures `#F2A15A`, HDRIs `#6C8CFF`, models `#4CC38A`, sounds
  `#A48AFF`.
- **Palette:** taken from `theme.rs` (dark): app `#171717`, panel
  `#1E1E1E`, surface `#242424`, border `#303030`, text `#E8E8EA`. It's
  set up as a custom DaisyUI theme `axcenity`.
- **Fonts:**
  - **Plus Jakarta Sans** for headings, ExtraBold. This is a best guess at
    the wordmark's font; it lives in one `--display` CSS variable.
  - **Inter** for body text.
  - **JetBrains Mono** for uppercase micro-labels.
- **Logo use:**
  - the wordmark wipes in and gets a periodic shine sweep
  - the tile cuts in on load
  - a giant watermark mark with parallax sits behind the content
  - the mark (with a light sweep) is the loader, replacing spinners
  - the "In library" badge carries the mark
  - empty states show a ghost mark
  - the footer has a giant cropped wordmark
  - the favicon is `favicon-32.png`

  The logo is **never** placed on provider thumbnails, to avoid implying
  endorsement. Logo files are copied into `static/branding/`.
- **Motion:**
  - a cursor spotlight on cards and tiles
  - staggered blur-up entry for cards
  - View Transitions on HTMX swaps
  - a right-edge scroll ruler plus a section index (on the main page and
    Discover)
  - all CSS plus a little plain JS; `prefers-reduced-motion` is respected
- **Inspiration:** the user likes getartcraft.com (screenshot discussed:
  orbit thumbnails, right-edge ruler, mono micro-labels). The design must
  stay **its own**: patterns, not copies.

### Tooling and structure (Q18–Q20, Q26)

- **Dependencies (uv only, no pip or Node):** `django`,
  `djangorestframework`, `django-tailwind-cli` (Tailwind standalone CLI
  with DaisyUI; **check its current docs for the DaisyUI setting**), and
  `django-htmx`. Dev dependencies: `ruff` (lint and format, configured in
  `[tool.ruff]`), `pytest`, `pytest-django`, `responses`, `pytest-cov`.
- **Layout:** `config/`, `providers/` (existing), `catalog/` (Asset, Tag,
  SavedAsset, Discover, library, library API), `packs/` (Pack, PackItem,
  gallery, builder, suggestions, copy, export, pack API), `accounts/`,
  `templates/` (`base.html` + `partials/`), `static/`, `fixtures/`, and
  `tests/` at the top level with one `conftest.py`.
- **Tests:**
  - App tests use `monkeypatch` on `search_records`/`fetch_record`.
  - Provider tests use `responses` to fake: timeout, connection error,
    429, Openverse's 500 with an HTML body, Poly Haven's 404, and
    `keywordMatches == 0`.
  - A fixture clears the cache.
  - No live API calls.
- **Demo data:** `uv run manage.py seed_demo` loads a committed snapshot,
  `fixtures/demo_assets.json`, of about 40 real assets across the four
  types. A one-time capture script produces it. The command creates:
  - 3 demo users
  - about 6 themed public packs (for example "Medieval Village", "Sci-fi
    Corridor", "Forest Ambience")
  - library entries with varied statuses and ratings

  It's safe to run repeatedly and works offline. Document the demo
  credentials in the README; don't invent real-looking secrets.

### Build tiers (Q29), for the PRD's scope and priorities

1. **Tier 1, essential (every graded requirement):**
   1. Scaffold plus the branded `base.html` shell (palette, fonts, logos,
      no motion yet)
   2. Providers: `AssetRecord` + error tests
   3. Models + `normalize_tag`
   4. Accounts and the token page
   5. Discover + caching
   6. Library filters, drawer and delete
   7. API + permission tests
   8. Packs: builder, "Add to pack", public/private, export
   9. Main-page gallery
   10. `seed_demo` + README
2. **Tier 2, signature features:**
   1. Suggestions + "Find more from providers"
   2. Copy pack and per-item save
   3. Orbit hero + scroll ruler
   4. Branding motion
3. **Tier 3, stretch:**
   1. "Popular assets" row
   2. Discover "Load more"
   3. Light theme
   4. A sample Rust or Lua manifest loader in `docs/`

## Next steps

1. Run **`/to-prd`** and save it to **`prd/axcenity-toolbox.md`** (the
   `implement` skill expects `prd/<feature>.md` and `plans/<feature>.md`
   with matching names).
   - Trace each graded requirement to user stories.
   - Mark the tiers as scope and priority.
   - Put the manifest contract and the access rules in as explicit
     acceptance criteria.
2. Show the PRD to the user for review. Commit only if the user asks.
3. Afterwards, `/prd-to-plan` turns the PRD into
   `plans/axcenity-toolbox.md`, with phases that follow the tiers.
4. Log the session in `PROMPTS.md` **only when the user asks** (see the
   rules at the top of that file). This design session hasn't been logged
   yet.

## Suggested skills

- **`to-prd`** (repo skill): the main task for the next session.
- **`prd-to-plan`** (repo skill): the step after the PRD is approved.
- **`prototype`**: only if a new UI question comes up (for example the
  library drawer or the pack builder). Follow the conventions of
  `prototypes/discover-branded.html`.
- **`implement`** / **`tdd`**: later, once the PRD and plan exist.
- **`grill-me`**: only if the user wants to reopen a decision.
