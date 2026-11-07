# PROMPTS.md — AI Usage Log

This file is the record of AI use on this codebase. At the end of every
agent session, direct the agent to write the session log with this prompt:

> Append a session log to PROMPTS.md at the repo root, under today's date,
> newest entry at the top. Record every prompt I gave you this session, in
> order, including any corrections. End the entry with a short summary:
> the outcome, any places where I deviated from a recommended answer or
> asked follow-up questions, and anything that went sideways.

Two rules:

- Entries are added only by that prompt, never unprompted.
- New entries go at the top. Never rewrite or delete an old entry — the
  log is part of your work, and an honest log of a session that went
  sideways is worth more than a tidy one.

Each entry has this shape:

    ## YYYY-MM-DD — <one-line summary>

    ### Prompts
    1. ...

    ### Summary
    - **Outcome:** what was built and what was kept
    - **Deviations:** recommendations overridden, follow-up questions asked
    - **Sideways:** failures, wrong turns, and how they were caught

## 2026-11-06 — Docs split into short indexes and topic files for progressive disclosure

### Prompts

1. Alright the Docs pages are far too long and likely should be cut down to
   optimize AI usage and progressive disclosure please read through all docs
   files seperate and reformat as neccesary updating CLAUDE.md as necessary.
   After all changes have completed please post changes in PROMPTS.md
   according to sounrce formatting, please include changes in CLAUDE.md to
   seperate and keep and organized codebase going forward.

### Summary

- **Outcome:** `docs/ARCHITECTURE.md` (947 lines), `docs/FRONTEND.md`
  (1,509) and `docs/TESTING.md` (136, with one-paragraph table rows) are now
  short indexes of 98, 94 and 87 lines. Each index keeps only the rules
  that apply everywhere, plus a "read this file before you touch…" table.
  Detail moved into one file per area:
  - `docs/architecture/`: `urls`, `providers`, `discover`, `library`,
    `packs`, `exports`, `home-and-demo`, `api`
  - `docs/frontend/`: `theme`, `shell`, `htmx`, `motion`, `discover`,
    `library`, `packs`, `attribution`, `home`, `accounts`
  - `docs/testing/test-files.md`: the per-file catalogue, grouped by area

  Across all three, the text went from about 27,800 words to 19,100. One
  task now reads an index plus one topic file: a template change loads
  about 1,600 words where it used to load 14,000. The topic files cut dated
  provenance, "used to" history and phase markers, and keep every
  identifier, rule, status code and the short reasons that guard against
  known regressions. The indexes keep their paths, so every link from code
  comments, tests, the README and the plan still works.

  `CLAUDE.md`'s "Read before…" table now says to read the index, then only
  the topic file it points to. A new "Keeping the docs organized" section
  sets the rules for later work:
  - indexes stay about 150 lines at most, and a topic file splits past
    about 200
  - docs describe what the code does now; history lives in PROMPTS.md and
    git
  - docs are updated in the same change as the code (new URL, shared
    function or test file: its listing)
  - each fact is said once
  - research files and the walkthrough are left as dated records

  The `/implement` skill reads indexes then topic files and updates the
  docs per those rules. Two README pointers were updated.
  `code-walkthrough.md` and `research/game-asset-apis.md` are unchanged.
- **Deviations:** none asked for. Kept on my own judgement:
  - the three index paths, so existing links don't break
  - the research doc and the walkthrough, both dated, cited records
  - `plans/axcenity-toolbox.md`, which still names old section headings
    such as "Status history". Its phases are a historical record, so it
    wasn't rewritten.
- **Sideways:** a first draft of the test catalogue put
  `test_token_page.py` and `test_api_library.py` under "Main page and
  demo data". It was moved to its own "APIs and tokens" section. A
  scripted check confirmed every `tests/test_*.py` file has a row and every
  relative link in the docs resolves. Its one flagged link was a code
  sample in the walkthrough. Two summarised signatures (`save_to_library`,
  `copied_from`) were checked against the code before they went in. Only
  Markdown changed: the README test passes and Ruff is clean. The full
  suite wasn't rerun.

## 2026-11-06 — A library client script for the Toolbox's own API, replaceable API tokens, and console script docs

### Prompts

1. Can you do the following (pasted: an earlier review's finding that the
   repo had no script calling its own Django API, with a proposal for
   `library_client.py`: read the token and server address, list
   `GET /api/library/` as a numbered list, pick an entry and a new value
   for one field, print it before and after `PATCH /api/library/<id>/`,
   clear messages for a stopped server, a wrong token, an empty library or
   a rejected update, using `requests`, with tests that don't reach the
   network).
2. Ok what I would like you to do is include this in a the README, as well
   as in PROMPTS.md, then add a way for the users to cycle their API token
   if they would like. Detail all useful and relevant commands for both
   Python scripts and how to use them effectively and to their fullest
   potential.

### Summary

- **Outcome:** `library_client.py` sits next to `asset_search.py`. It
  reads the server (default `http://127.0.0.1:8000`, or `TOOLBOX_URL`) and
  the token (typed without echo, or `TOOLBOX_TOKEN`), lists every library
  page, and changes one entry's status (with an optional reason), rating
  (or clears it) or notes, showing the entry before and after the PATCH.
  Every failure is one `Error:` line and exit code 1.
  `tests/test_library_client.py` (11 tests) uses `responses`, plus two
  end-to-end tests that hand each request to Django's test client so the
  script runs against the real API views offline. The API token page
  gained **Copy token** and **New token**: a confirm dialog (the same
  `[data-dialog-open]` pattern as a pack's New link) posts to
  `accounts:rotate_token`, which calls the new `rotate_token()`
  (`accounts/tokens.py`, one transaction) and goes back to the page with
  a one-time message. The old key is a 401 at once; 8 new tests in
  `test_token_page.py` cover that, the message, a first token, other
  members untouched, POST only, CSRF and sign-in. The README gained a
  token-replacement section, a side-by-side of both scripts and how they
  work together, a full library client section (prompts, environment
  variables for sh and PowerShell, piped answers, a sample run, every
  error and its fix, its tests), tips for `asset_search.py` (ID lookups,
  type filters, piped answers, saving output, Openverse's limits), and new
  Troubleshooting rows. ARCHITECTURE.md and TESTING.md list the new URL,
  function and tests. 1,302 tests pass and Ruff is clean.
- **Deviations:** none. The token page also gained a short "From the
  console" note pointing at `library_client.py`, and the README's test
  count went from about 1,260 to about 1,300.
- **Sideways:** a live run of the client against the dev server would
  have needed one of the user's real tokens; reading it from the database
  was refused, so the live check covered only the "server not running"
  message, and the real-API path is proven by the end-to-end tests. A
  first README draft said notes are capped at 2,000 characters; checking
  `NOTES_MAX_LENGTH` showed 10,000, so the README and a test's canned
  message were fixed. An unverified claim about how each provider matches
  phrases was dropped. A long shell heredoc for the README patch failed
  on quoting and was rerun as a script file. The piped `asset_search.py`
  example was checked live against ambientCG before it went in.

## 2026-11-06 — Post-phase polish: prototype loader and hover, section icons, an all-cover main page, a storm-grey light theme

### Prompts

1. Ok I like the custom loading and hover features from the prototype can those
   be added (a screenshot of the prototype's pending Poly Haven shelf: skeleton
   cards under a "Searching Poly Haven" badge).
2. Ok another thing I noticed is the text on the overview seems to be merging
   together a bit (sent while the first request was running, with a screenshot
   of a card's details panel where "Commercial" ran into "Usable. No
   conditions.").
3. Ok I noticed the axcenity logo on the bottom of the home page cuts off
   abruptly at the top and leaves blank space when scrolling at the bottom can
   this be fixed (a screenshot of the home page's gallery and footer).
4. Ok I think it would be cool to add watermark icons similar to the axcenity
   logo found it the background of other tabs for different menus and pages as
   well as expand the header. Please adjust the site in a way you feel would
   make it look graphically appealing in that regard.
5. Ok the animated icons look cool I was wondering if you can have these place
   to the left of the actual text and for the sidebar menu icon to be in full
   view. For the home page I would like to make it to where only the cover is
   shown not the top or the side unless I have over them treat all other pages
   the same. I would like to have the texture Icons move based on my scrolling
   as well
6. Ok for the sidebar menu icon I actually like the look of when it was in the
   bottom right corner, I still would like to see the icon. As for the home
   menu I want all the menus to appear when I scroll passed the cover and some
   seamless transitions to occur when they appear.
7. Ok the light theme to me is a bit too bright I would like it to be more grey
   almostly like a light storm grey
8. Go ahead and update PROMPTS.md according to source formatting

### Summary

- **Outcome:**
  - A pending Discover shelf shows the prototype's look: six skeleton cards (a
    thumbnail and two lines, fading along the row) under a square, frosted
    badge with the logo loader and "Searching <provider>".
  - Result, library, gallery and pack cards lift 4 px onto a soft shadow on
    hover, and a result's thumbnail zooms in 7 %. A 4 px strip under a lifted
    card stops it jittering at its bottom edge.
  - A card's details panel no longer overlaps: its labels sit in one
    `max-content` column, so "Commercial" fits.
  - The main page's faint mark no longer stretches the page into blank space
    below the footer, and no longer shows a hard cut across its top.
  - Each section has its sidebar icon as a line drawing that draws itself in:
    a framed column to the left of the page header's text, and a faint
    watermark in the open sidebar's bottom-right corner. The header's label row
    gained a hairline that runs out to the content's right edge.
  - With a mouse, the main page opens on its cover alone. The title bar and
    sidebar come in once the cover is scrolled past (or while an edge is
    hovered, or focus is inside), the bars first and then their items one after
    another, and leave on the way back up. The content after the cover keeps
    the sidebar's room, so nothing shifts.
  - The orbit's rings turn further and the orbit eases in closer as the cover
    scrolls away; each texture counter-turns to stay upright.
  - The light theme is a light storm grey instead of near-white, with darker
    text, lines and status colours, and dark rather than white shadows.
  - 1,283 tests pass (1,261 before). `ruff check` and `ruff format` are clean,
    and `tailwind build` succeeds. Nothing has been committed.
- **Changes:**
  - `styles/source.css`: the skeleton and loader badge, the card lift, the
    details-list grid, `.content-stage { overflow-y: clip }` and the main
    page's mark fade, the section icons (`.page-hero-glyph`,
    `.side-watermark`, `watermark-draw`) and the kicker's rule, the all-cover
    block (`--cover-offset`, `--side-reserve`, `--chrome-i`), the orbit's
    scroll animations in the parallax's `@supports` block, and the storm-grey
    light palette.
  - `catalog/.../shelf.html`: the skeleton cards and the badge.
  - `templates/partials/page_header.html`: two columns, the icon then the text.
  - `templates/base.html`: the sidebar watermark.
  - `catalog/templatetags/shell_tags.py`: `PAGE_ICONS` and the `page_icon`
    filter.
  - `static/js/motion.js`: sets `<html data-cover="past">` past the cover.
  - Tests: `test_motion.py`, `test_discover.py`, `test_shell.py`,
    `test_home_hero.py` and `test_theme.py`, updated and extended.
  - `docs/FRONTEND.md`: the loader badge, the card lift, the mark's clip,
    section icons, the page header, the all-cover main page, the orbit's scroll
    and the light theme.
- **Decisions:**
  - The prototype's type-coloured hover edge and glow were left out, and its
    rounded loader box made square, to keep the monochrome, square chrome.
  - "Expand the header" was read as the page header, not the title bar. Its
    headline sizes were kept, because an earlier request made them smaller.
  - "Only the cover … not the top or the side" was read as tucking the title bar
    and sidebar away on the main page, and "treat all other pages the same" as
    leaving the other pages as they were. Touch screens keep both bars.
  - The light theme no longer follows the engine's light palette; its test now
    checks the storm-grey values and that every text and status colour keeps
    4.5:1 contrast.
- **Deviations:**
  - The section icons went through three placements at the user's direction:
    a faint background watermark behind the header, then a column beside the
    text; in the sidebar, cropped in the corner, then centred and whole, then
    back in the corner with less of it cropped.
  - The main page's bars first appeared only on hover; the user then asked for
    them to come in past the cover, with a smoother entrance.
- **Sideways:**
  - The loader badge's overrides were first written inside the components
    layer, where the unlayered loader rules would beat them; moved out before
    testing.
  - A new `:root` block became the last one in the file and broke the loader
    test, which reads the last `:root`; the variable moved to `html`.
  - A light-mode override placed before the main light block broke 24 theme
    tests, which read the first such block; its selector became
    `:root[data-scheme="light"]`.
  - The sidebar watermark's icon was counted as a sidebar row icon; that test
    now leaves it out.
  - A second scroll-timeline `@supports` block failed the degrade test, which
    checks only the first; the orbit's rules were merged into it.
  - A Python heredoc turned escaped newlines in new tests into real ones; fixed
    by hand with the editor.
  - The light palette's comment claimed 12:1 body-text contrast; measuring gave
    10:1, and three colours (weak text, error, warning) were under 4.5:1 on the
    darker bars. Those were darkened and a contrast test added.
  - Nothing was checked in a browser this session, and Node isn't installed, so
    `motion.js` wasn't syntax-checked; the user was asked to look at each change.

## 2026-11-06 — Axcenity Toolbox: Phase 13/13, Branding motion and reduced motion

### Prompts

1. The `/implement` skill, given `axcenity-toolbox phase 13`.
2. Go ahead and start development (approving the brief).

### Summary

- **Outcome:** the site has its branding motion, and none of it runs under
  reduced motion.
  - The wordmark wipes in on a full load and shines every 12 s. The page's
    faint mark cuts in diagonally, and its layer drifts as a parallax
    watermark as the page scrolls.
  - The logo loader (the mark with a light band sweeping across it) is the only
    loading indicator. The status bar's mark sweeps while any htmx request
    runs, and the loader shows in place in a pending shelf, Load more, the pack
    picker and the drawer's Saving.
  - A cursor spotlight lights cards and tiles, and cards blur up into place
    with a stagger.
  - htmx fragment swaps crossfade in place instead of dropping and lifting the
    whole page; boosted navigation keeps its rise.
  - 1,261 tests pass (1,236 before; 25 new). `ruff check` and `ruff format`
    are clean.
- **Changes:**
  - `styles/source.css`: the "Motion" section (wipe, cut-in, shine, parallax
    behind `@supports`, the loader, the spotlight, the card entry), the
    fragment-swap crossfade, and the blanket reduced-motion rule, with the
    loader's still state after the section; Load more's busy label is
    `inline-flex`.
  - `static/js/motion.js` (new): the `data-booted` flag, the busy count
    (`htmx:beforeSend` to `loadend`, shown after 150 ms, `aria-busy` on the
    content), `data-swap` on `htmx:beforeTransition`, and the spotlight.
  - `templates/partials/loader.html` (new): the logo loader.
  - `templates/base.html`: loads `motion.js`, adds `.brand-shine` to the
    wordmark link, and makes the status bar's mark the loader
    (`#status-loader`, `.status-mark`).
  - `catalog/.../shelf.html` and `load_more.html`: the loader for
    "Searching" and "Loading…".
  - `static/js/card-actions.js` and `entry-drawer.js`: the loader's mark in
    "Loading your packs…" and "Saving…".
  - `tests/test_motion.py` (new).
  - `docs/FRONTEND.md` (a "Motion" section, fragment swaps under "Page
    transitions", the script list, the pending shelf) and `docs/TESTING.md`.
  - `plans/axcenity-toolbox.md`: Phase 13 ticked (one criterion left open),
    with a "Built as" note.
- **TDD:** skipped. The phase is motion, styling and markup, with no
  permissions, rules or data; ordinary tests cover each criterion.
- **Decisions:**
  - The PRD's icon tile that "cuts in" left the activity bar at the user's
    request, so the page's faint mark cuts in instead.
  - The "giant parallax watermark" would undo story 104, so the parallax
    moves that same mark (CSS scroll-driven, at 0.4× over the first 60 rem).
  - The intros play on a full load only, not on each boosted swap.
  - A card's corner squares keep their pulse while saving, because they sit
    on the provider's thumbnail and the logo never goes there; the status
    bar's loader shows instead.
  - Fragment swaps already ran the page's drop and rise (global View
    Transitions), so they now crossfade the content in place; swaps marked
    `transition:false` are unchanged.
  - The spotlight covers result and library cards, Discover's type tiles,
    gallery cards, pack cards and pack rows. The blur-up covers the same
    cards (not the tiles), staggered within each 12, so a Load more batch
    staggers too.
  - Reduced motion is one blanket rule on top of the existing list. Every
    entry animation ends on the element's resting style, and the loader holds
    still in grey.
- **Deviations:** none. The brief was approved as written.
- **Sideways:**
  - The reduced-motion colour for the loader was first written into the old
    reduced-motion block, before the Motion section, where the loader's own
    later rule would have beaten it at equal specificity. It was caught in
    review before any test and moved after the section, and a test checks
    the order.
  - The first run of the new tests had five failures, all in the test helpers:
    keyframes indented inside a layer, selectors that appear more than once
    (the first match was the reduced-motion copy), and checks for
    `startViewTransition` and `animation-timeline` that matched a comment and
    the `@supports` condition. Each was fixed in the test, not the code.
  - Headless Firefox screenshots (1600 px, light, against a scratch copy of
    the database) with and without `ui.prefersReducedMotion` showed the
    gallery's cards, the wordmark and the mark ending in place. A screenshot
    shows only the end state, so the moving parts weren't watched; "Motion
    works in a current browser" stays unticked until they're checked by hand.

## 2026-11-06 — Phase 12 polish, second request: a textures-only cover hero

### Prompts

1. Ok I cannot see the textures that are spinning also please keep it to just
   textures not other asset types as they look the best. Also please blend the
   orbital rings into the rest of the page and make it fill up the entire page
   as a cover until you scroll down. Remove (pasted: the legend's Textures,
   HDRIs, Models, Sounds, and "Public packs will orbit here. Once they hold six
   assets, their thumbnails circle here; for now each type opens Discover.").
2. I still am not getting any textures this is all I am getting (a screenshot
   of the hero showing two texture-icon tiles).
3. Run seed_demo now (chosen from: run it, add textures by hand, or lower the
   minimum).

### Summary

- **Outcome:**
  - The hero shows textures only, up to 18 on up to three texture rings, the
    busiest outermost.
  - It fills the first screen as a cover. The rings are faint and fade into the
    page, and the legend and note are gone.
  - The user's database had only 1 texture in public packs, so they saw the
    fallback; `seed_demo` now gives it 15.
  - 1,236 tests pass. `ruff check` and `ruff format` are clean.
- **Changes:**
  - `packs/hero.py`: textures only (`HERO_KIND`), `RING_SIZES`, `RING_SPINS`,
    `ring_counts()`, a texture-icon fallback (`FALLBACK_TILES`). The per-type
    pick, the counts and `CUTOUT_KINDS` are gone.
  - `packs/partials/hero_orbit.html`: no caption, new guide rings.
  - `styles/source.css`: the cover height, the blended rings (40 % `::before`
    lines), the fade down the lower half, the bigger stage, and the mark moved
    below the cover.
  - `tests/test_home_hero.py` (rewritten for textures only) and
    `tests/test_shell.py` (the orbit's type colour is texture only).
  - `docs/FRONTEND.md`, `docs/ARCHITECTURE.md`, `docs/TESTING.md` and the plan.
  - The local `db.sqlite3` (git-ignored): `seed_demo` run, at the user's choice.
- **TDD:** the three approved behaviours (public packs only; links to a public
  pack; the 6 threshold and the 18 cap) were kept and their tests rewritten for
  textures only. The user's request changed what the hero shows, not those
  rules.
- **Decisions:**
  - The fallback is six texture-icon tiles on the outer ring (the PRD's
    "type-icon tiles", for the one type left).
  - The rings fill from the outside in: one ring per 6 tiles, shared by size.
- **Deviations:**
  - The user's earlier requirement to spread thumbnails across every type was
    replaced by "just textures".
  - Lowering the 6-texture minimum was offered and not chosen.
- **Sideways:**
  - The new tests caught a real bug: a texture in two public packs was counted
    twice, because PackItem's default ordering defeated `DISTINCT`. The old code
    hid it by building a dict. Fixed with `.order_by()`.
  - The user's "I can't see textures" was missing data, not code: their one
    public pack held one texture.

## 2026-11-06 — Phase 12 polish: the ruler on every page, an Artcraft-style hero, textures as cut-outs

### Prompts

1. Ok so a few things the rule does not show up in all tabs it only shows up
   in the home tab can we have it accross all pages, additionally the main hero
   does not look very detailes and does not show actual textures. wehn showing
   textures please make sure that the background is removed. I want the text to
   be in the front and the spinning wheel in the back similar to artcraft
   (with a screenshot of Artcraft's hero and its right-edge ruler).

### Summary

- **Outcome:**
  - The scroll ruler is on every page from 80 rem: a full-height scale like
    Artcraft's (minor ticks, numbered majors, a cursor and ink fill), with the
    page's own section index. Pages without one get Top and End.
  - The main page's hero follows Artcraft's: the text centred in front, the
    rings large behind it, with grey guide rings for depth, bigger tiles further
    out, faded at the top and bottom and cropped at the page's sides.
  - Textures and models float as cut-outs (their transparent renders with no
    tile behind them, a shadow following the shape). HDRIs stay framed.
  - 1,230 tests pass. `ruff check` and `ruff format` are clean.
- **Changes:**
  - `templates/base.html`: the ruler (`nav#scroll-ruler` with `{% block
    ruler_sections %}`), `#page-top` and `.content-gutter` on the content and
    footer wrappers.
  - `templates/partials/ruler_entry.html` and `ruler_scale.html` (new);
    `partials/scroll_ruler.html` removed.
  - `ruler_sections` blocks in the main page, Discover, the library, an entry's
    page, Your packs, the builder, a pack's page, the license guide, a pack's
    and an asset's attribution, and Settings; `#entry-related` on the entry
    page's aside.
  - `packs/views.py` and `catalog/discover.py`/`views.py`: the view-level
    ruler section functions removed (templates own them now).
  - `packs/hero.py`: `OUTER_RING`, `RING_STEP`, `CUTOUT_KINDS`,
    `OrbitRing.tile_rem` and `OrbitThumb.is_cutout`.
  - `packs/partials/hero_orbit.html` and `packs/home.html`: guide rings,
    cut-out tiles, the caption at the hero's foot, the text centred in front.
  - `static/js/scroll-ruler.js`: entries placed level with their sections,
    missing ones hidden.
  - `styles/source.css`: the new hero and ruler styles.
  - `tests/test_scroll_ruler.py` (rewritten for every page) and
    `tests/test_home_hero.py` (cut-outs, the new pause selector, ring sizes).
  - `docs/FRONTEND.md`, `docs/ARCHITECTURE.md`, `docs/TESTING.md` and the
    plan's "Phase 12 polish".
- **Decisions:**
  - "Background removed" was read as: the providers' texture and model
    renders already have transparent backgrounds, so drop the tile behind them.
    Showing the flat colour map instead would mean a 0.5 MB+ file per tile.
  - Each template declares its own ruler entries beside its sections, under
    the same conditions, so no entry points at a missing section.
  - The page's faint mark stays on the main page (the "mark on every page"
    test from 2026-11-05) but moves below the hero, so the orbit stays free of
    logos.
- **Deviations:** the PRD puts the ruler on the main page and Discover only;
  the user asked for every page.
- **Sideways:**
  - A `{% block %}` inside an included partial can't be overridden, so the
    ruler's markup moved into `base.html` itself.
  - First tries, caught by headless Firefox screenshots (scratch database):
    - hiding the mark broke the mark-on-every-page test
    - the hero's negative top margin was reset by Tailwind's `space-y-8`
      (fixed with an unlayered rule)
    - the hero overflowed at phone width
    - the fade mask clipped tiles at the hero's sides, because a mask paints
      only inside its own box (the layer now reaches past them)
    - the ruler's numbers were faint over the glow
  - Two palette tests refused a mask written with `#000` and then `black`; it
    uses `ink`.
  - `test_shell`'s regex reads the first `.hero-atmosphere {` rule, so the new
    rule moved below the original.
  - Not checked in a real browser: dragging the pointer over tiles to pause,
    and the ruler's placement while scrolling.

## 2026-11-06 — Axcenity Toolbox: Phase 12/13, Orbit hero and scroll ruler

### Prompts

1. The `/implement` skill, given `axcenity-toolbox phase 12`.
2. Looks good just keep in mind these requirements (approving the brief, and
   pasting eight requirements: keep the four types distinct in their colours;
   spread thumbnails across types so textures don't dominate; the most
   populated ring outside; no logos in the orbit; pause on hover and keyboard
   focus; respect reduced motion; the ruler working through plain anchors
   without JavaScript; the ruler on wide screens only).
3. Ok looks good move to next test (approving TDD 1's red test).
4. Looks good move to next (approving TDD 2's red test).
5. Looks good move to building (approving TDD 3's red test).

### Summary

- **Outcome:** the main page has an animated orbit hero and both the main page
  and Discover have a right-edge scroll ruler.
  - Up to 18 random thumbnails from public packs circle on one ring per type,
    each ring in its type colour, the busiest outermost. Each opens the newest
    public pack holding it. Hover or focus pauses it; reduced motion stills it.
  - Below 6 assets in public packs, four rings with one type-icon tile each
    (opening Discover for that type) show instead.
  - The ruler's numbered index jumps to each section (plain `#anchors`), marks
    the one in view and fills as the page scrolls, from 80 rem only.
  - 1,227 tests pass (1,196 before; 31 new). `ruff check` and `ruff format`
    are clean.
- **Changes:**
  - `packs/hero.py` (new): `hero_orbit()` with `HeroOrbit`, `OrbitRing`,
    `OrbitThumb`, the pick, the rings and the fallback.
  - `packs/views.py`: `HomeView` adds the hero and the ruler on full pages
    only; `home_ruler_sections()`.
  - `catalog/discover.py`: `discover_ruler_sections()`; `catalog/views.py`
    passes it to Discover.
  - Templates:
    - `packs/partials/hero_orbit.html` (new): rings, tiles, legend and note
    - `partials/scroll_ruler.html` (new)
    - `packs/home.html`: `#home-hero` in two columns with the orbit, and the
      ruler
    - `catalog/discover.html`: the ruler
    - `base.html`: loads `scroll-ruler.js`; the content wrapper gains a
      `content-body` class
  - `static/js/scroll-ruler.js` (new): progress fill, the section in view,
    smooth (or instant) jumps.
  - `styles/source.css`: the orbit and ruler styles, the ruler pages' 6 rem
    gutter (unlayered), scroll margins, and both in the reduced-motion block.
  - `tests/test_home_hero.py` and `tests/test_scroll_ruler.py` (new).
  - `tests/test_home.py` and `tests/test_shell.py`: the main page's
    type-colour checks now allow the orbit (all four types in its fallback)
    and nothing else.
  - `docs/ARCHITECTURE.md`, `docs/FRONTEND.md` and `docs/TESTING.md`: the
    hero, the ruler, the type-colour list and the new test files.
  - `plans/axcenity-toolbox.md`: Phase 12 ticked, with a "Built as" note.
- **TDD:** three behaviours, each red on an assertion before green:
  1. Assets only in private or unlisted packs never reach the hero, and their
     type gets no ring.
  2. Each thumbnail links to a public pack that holds it: the newest, never a
     newer private or unlisted pack holding the same asset.
  3. 5 distinct assets give the fallback and 6 the thumbnails; with many
     more, exactly 18 distinct, each on its own type's ring.
- **Decisions:**
  - Rings exist only for types with thumbnails; the fallback always has four.
  - The pick takes from each type in turn (the user's "don't let textures
    dominate"), and the rings are ordered by tile count, busiest outermost.
  - A thumbnail links to the newest public pack holding it.
  - The fallback's tiles open Discover for their type.
  - Counts ("42 assets from 6 public packs") go in the note under the legend.
  - The ruler's sections: Toolbox, How it works (visitors only), Public
    packs; on Discover, Search, Types and each shelf.
  - Hero thumbnails load eagerly, as the hero is above the fold.
- **Deviations:** none. The user's eight requirements matched the brief and
  were built as given.
- **Sideways:**
  - TDD 2's first run errored (`AttributeError` on `None.is_public`), not an
    assertion; `assert thumb.pack is not None` was added first, a mechanical
    fix reported at the time.
  - A Python re-indent of `home.html` duplicated two lines and didn't take;
    it was repaired with the Edit tool.
  - Headless Firefox screenshots (light and dark, 1600, 1100 and 420 px,
    against a scratch copy of the seeded demo, so the local database was
    untouched) caught four layout bugs the tests couldn't: the counts in the
    orbit's centre collided with the inner ring; the page's faint mark showed
    through inside the rings (now hidden by a panel-coloured disc); on
    Discover the ruler ran over the tiles, because the gutter rule sat in the
    components layer and `lg:px-12` beat it (moved out of the layers); and at
    phone width the one-column grid grew to the search bar's width, cutting
    off the headline.
  - The scratch server ran with `--noreload`, so it served cached templates
    until it was restarted.
  - Not checked in a real browser: the smooth jump and the "in view" marker
    while scrolling (screenshots can't scroll), and pausing on hover. Check
    them by hand with the guide.

## 2026-11-06 — Axcenity Toolbox: Phase 11/13, Save single items and Copy pack

### Prompts

1. The `/implement` skill, given `axcenity-toolbox phase 11`.
2. Looks good move on to tests (approving the brief, including the
   recommendation that an unlisted pack's share link allows Save and Copy).
3. Looks good move to next test (approving TDD 1's red test).
4. Looks good move to next (approving TDD 2's test).
5. Looks good move to building (approving TDD 3's red test).

### Summary

- **Outcome:** a pack's page now has **Save to library** on each item and
  **Copy pack** for signed-in readers.
  - Save makes a To review entry from the stored Asset, or shows "In your
    library" for one the reader has, linking to it.
  - Copy pack confirms first (saying how many assets would join the
    library), then makes a private "<title> (copy)" with `copied_from`, the
    intended use, the tags, and each item's variant, import path and
    position, all in one transaction. Missing assets go into the copier's
    library as To review, and their own entries stay untouched.
  - The copy's builder says where it came from. The API has no copy URL.
  - 1,196 tests pass (1,169 before; 27 new). `ruff check` and
    `ruff format` are clean.
- **Changes:**
  - `packs/services.py`: `copy_pack()` and `copy_title()`.
  - `packs/views.py`:
    - `PackReaderWriteMixin` (members only; the pack page's reader rule; a
      visitor goes to sign in and back to the page)
    - `PackItemSaveView` and `PackCopyView`
    - the pack page's context: each item's save URL and the reader's own
      entry, the copy URL, and the confirm's count
    - `_copied_from()` for the builder
  - `packs/urls.py`: `packs:save_item`, `packs:copy`,
    `packs:shared_save_item` and `packs:shared_copy`.
  - Templates:
    - `packs/partials/item_save.html` (new)
    - `pack_page.html`: Save in each item's row, Copy pack and its confirm
      dialog, and Sign in links for visitors
    - `builder.html`: "Copied from …"
  - `templates/partials/icon.html`: a `copy` icon.
  - `styles/source.css`: `.item-save`, with "In your library" inverted.
  - `tests/test_pack_copy.py` (new).
  - `tests/test_pack_public.py`: the "read-only" checks now allow only the
    Save and Copy forms, with no edit controls.
  - `docs/ARCHITECTURE.md`, `docs/FRONTEND.md` and `docs/TESTING.md`: the
    new URLs, `copy_pack()`, the page's buttons and the test file.
  - `plans/axcenity-toolbox.md`: Phase 11 ticked, with a "Built as" note.
- **TDD:** three behaviours, each red before green:
  1. Copying saves missing assets as To review and leaves the copier's own
     entries (and the owner's) untouched, never calling a provider.
  2. A copy that fails partway leaves no pack, item, entry or status record.
  3. Save and Copy follow the pack page's reader rule. Another member's
     private pack, an unlisted one by slug, and a private pack's link are a
     404 that writes nothing. A visitor goes to sign in and back.
- **Decisions:**
  - Save and Copy are open to anyone signed in who can read the pack, the
    owner included (copying your own pack duplicates it).
  - An unlisted pack's readers use its share link. The plan left this open;
    the user approved it.
  - Neither action ever calls a provider (`save_asset()` on the stored
    Asset).
  - The copy keeps the intended use, has no share token, and its title is
    shortened to fit " (copy)". Positions are copied exactly.
  - Copy pack confirms first and lands in the copy's builder. "Copied from"
    links to the original only when it's readable by slug, so an unlisted
    original's link is never shown.
- **Deviations:** none. Every recommendation was approved as given.
- **Sideways:**
  - TDD 2 couldn't go red on its own: `transaction.atomic()` was already
    written while making TDD 1 pass. It was shown red by temporarily
    removing `atomic()` (2 packs where 1 was expected), then green with it
    restored. The change was reverted and checked.
  - Phase 8's pack-page tests asserted "no `<form>` at all" and failed once
    Save and Copy existed. As planned, they were narrowed to "no edit
    controls; only Save and Copy forms".
  - Two first-draft test bugs were fixed in the tests:
    - "Sign in to save" was counted twice per item, because of the
      `aria-label`.
    - Django's `urlencode` keeps `/`, so the expected `next` was wrong.
  - Not driven in a real browser this session: the dialog, the swaps and the
    styles. Check them by hand with the guide.

## 2026-11-06 — Axcenity Toolbox: Phase 10/13, Suggestions and "Find more from providers"

### Prompts

1. The `/implement` skill, given `axcenity-toolbox phase 10`.
2. Looks good just make sure that query stored asset records and not
   anothers users saved information. Adding a sugggestion to be atomic;
   create or reuse the library entry and add it to the pack. never call a
   provicer when adding a suggestion. Only update the saved count when a new
   library entry is created. Enforce pack ownership on both suggestion
   endpoints. keep the two HTMX refresh events independent: packItemsChange
   and packTagsChanged.
3. Looks good move to next test (approving TDD 1's red test).
4. Looks good move to next (approving TDD 2's red test).
5. Looks good continue to building (approving TDD 3's red test).

### Summary

- **Outcome:** Tier 2 has begun.
  - The builder shows "Suggested for this pack": up to 8 stored Assets
    ranked by how many tags they share with the pack, ties by title A–Z then
    id, never one already in it. Each row shows its shared-tag count and "In
    your library" when the owner has it, with Add.
  - Adding a suggestion saves it to the owner's library as To review when
    needed and adds it, in one transaction and without calling a provider.
  - "Find more from providers" opens Discover with the pack's tags for its
    main type; a pack with no tags shows hints instead.
  - 1,169 tests pass (1,139 before; 30 new, and both suggestion URLs joined
    the existing pack access lists). `ruff check` and `ruff format` are
    clean.
- **Changes:**
  - `packs/suggestions.py` (new): `suggest_assets()`, `SUGGESTION_LIMIT`,
    `FindMore` and `find_more()`.
  - `packs/services.py`: `add_suggestion()`, returning `(entry,
    entry_created, item)` so the view knows when to update the saved count.
  - `catalog/library.py`: `save_asset(user, asset)`, the create-or-reuse
    step pulled out of `save_to_library()`, which now calls it. It never
    contacts a provider.
  - `packs/views.py`: `PackSuggestionsView` and `PackSuggestionAddView`
    (both through `OwnPackMixin`), `_suggestions_context()`, the builder's
    context, and `packTagsChanged` from a tags save in `PackDetailsView`.
  - `packs/urls.py`: `packs:suggestions` and `packs:suggestion_add`.
  - Templates: `packs/partials/suggestions.html` (new); `builder.html` (the
    section under the items); `items.html` (the saved count out of band when
    asked).
  - `styles/source.css`: `.pack-suggestions` (two rows to a line from
    48 rem) and `.pack-find-more`.
  - `tests/test_pack_suggestions.py` (new); `tests/test_access_control.py`
    (both URLs added to `_pack_gets()` and `_pack_writes()`).
  - Docs: ARCHITECTURE (URLs, "Suggestions and Find more", shared
    functions), FRONTEND (the builder's section), TESTING (the new file);
    the plan's Phase 10 ticked with a "Built as" note.
- **TDD:** three behaviors, each RED on an assertion, approved, then GREEN:
  1. `suggest_assets()` returns shared-tag groups highest first, leaving out
     assets with no shared tags and the pack's own (checked as groups).
  2. Equal counts go by title A–Z ignoring case, then id.
  3. `add_suggestion()` makes a To review entry or reuses the member's
     untouched, with every provider function failing the test if called.
- **Decisions:**
  - The section sits under the items in the left column, so Add from my
    library keeps the sticky right column; its rows have no hover preview,
    which would open over the side panel there.
  - Find more uses up to 2 of the pack's tags (the most used across stored
    assets first, then A–Z, like the entry page's Find more) and the type
    most of the pack's items have, ties in Discover's order, textures for an
    empty pack.
  - An unknown asset id is a 404; adding an asset already in the pack
    changes nothing.
- **Deviations:** the user's six conditions (prompt 2) were all adopted.
  "Never call a provider" changed the plan: `add_suggestion()` was going to
  reuse `add_from_provider()`, which can fetch, so `save_asset()` was pulled
  out of `save_to_library()` instead.
- **Sideways:**
  - TDD 3's first run failed with `DoesNotExist`, not an assertion; the test
    was repaired to read the entry with `.first()` (what it asserts was
    unchanged) and rerun RED.
  - The builder's context first passed `pack` through two `**` expansions,
    a `TypeError` caught by the access tests.
  - The event tests expected `null` details; django-htmx sends `{}`, so they
    compare the event names only.
  - The new tests' import block missed on the first edit (TDD 3 had
    already changed it) and was redone.
  - Checked against the seeded demo data in a throwaway test database:
    Castle Siege and Golden Hour Skies have no matching assets, so they show
    "No other assets share this pack's tags yet."

## 2026-11-06 — Axcenity Toolbox: Phase 9/13, Main page, public gallery and demo data

### Prompts

1. The `/implement` skill, given `axcenity-toolbox phase 9`.
2. Ok looks good just make sure that gallery privacy tests include a private
   or unlisted pack whose titel and tags would otherwise match the search
   query. Preventing accidental filtering pagination or other query
   operations.
3. Looks good move to next (approving TDD 1's red test).
4. Go ahead and move to next test just look at red phases for each test
   (after TDD 1 went green: stop only at each red from then on).
5. Looks good move to next (approving TDD 2's red test).
6. Looks good move to building (approving TDD 3's red test).

### Summary

- **Outcome:** Tier 1 is finished.
  - The main page explains the Toolbox to visitors in four steps (01
    Discover · 02 Save · 03 Pack · 04 Export), with the hero's Sign up and
    Sign in. Members see neither.
  - The side panel starts collapsed there.
  - The public gallery searches titles and tags, filters by type, sorts by
    newest or most items and pages by 12. It swaps only its results through
    HTMX and pushes the URL.
  - Each card has a mosaic of the first four thumbnails, the title, owner,
    tags and a count by type.
  - `seed_demo` loads three demo members, 43 real assets, 53 library entries,
    six public packs and one private pack, offline. It's safe to run again.
  - The README is rewritten for the Toolbox.
  - 1,139 tests pass (1,074 before; 65 new). `ruff check` and `ruff format`
    are clean.
- **Changes:**
  - `packs/gallery.py` (new): `filter_public_packs()`, `GalleryParams`,
    `GalleryPage`, `clean_gallery_params()`, `GalleryCard`/`gallery_card()`
    and `type_summary()`.
  - `packs/views.py`: `HomeView` serves the gallery (the fragment for HTMX,
    with `HX-Push-Url`) and sets `panel_start`.
  - Templates:
    - `packs/templates/packs/home.html`: the four steps and the gallery
      toolbar
    - `packs/partials/gallery_results.html` and `gallery_card.html` (new)
  - `templates/base.html` and `static/js/shell.js`: `data-panel-start` on
    `<html>` and `#app`. The head script and `applyPanelStart()` (after
    each boosted swap) use it ahead of the saved choice.
  - `styles/source.css`: `.home-steps`/`.home-step`, `.gallery-grid`,
    `.gallery-card`, `.gallery-mosaic`/`.gallery-tile`; the card's
    transition joins the reduced-motion list.
  - `packs/demo.py` (new): the demo users, packs, reviews and extra saves,
    the snapshot's JSON reader and writer, and `seed_demo()`.
  - `packs/management/commands/` (new): `seed_demo` and
    `capture_demo_assets`.
  - `packs/demo_assets.json` (new): the snapshot, captured live this
    session.
  - `README.md`: setup, running with Tailwind, the demo sign-ins, tests and
    Ruff, the API with a token, the snapshot, the layout. The console
    script's section is kept.
  - Tests (new): `tests/test_gallery.py`, `tests/test_home.py` and
    `tests/test_seed_demo.py`.
  - Docs:
    - `ARCHITECTURE.md`: new "Main page and gallery" and "Demo data"
      sections, the URL row and the shared functions
    - `FRONTEND.md`: "Main page" in place of "Home hero"; the gallery tiles
      join the type-colour list
    - `TESTING.md`: the new files and the demo accounts
  - Plan: Phase 9 ticked, with "Built as" notes and notes for Phases 10–12.
- **TDD:** three behaviours, each red on an assertion first.
  1. The gallery never lists a private or unlisted pack. Following the
     user's note, the test's private and unlisted packs match every query:
     - their titles and tags match the search
     - they hold every type
     - they have the most items, and they're the newest
     There are 13 public packs, so a second page exists. Ten queries
     (search by title, by tag, by both, type, both sorts, page 2,
     combinations) are each walked over every page. It was red against a
     scaffold that started from every pack.
  2. `type_summary()`: Discover's order, singular or plural ("1 HDRI",
     "2 HDRIs"), types with no items left out, and "No items yet". It was
     red against a stub returning "".
  3. Running `seed_demo` twice leaves every table's row count (many-to-many
     tables included) as one run does, under the network guard with every
     provider function failing. The test also checks what the first run
     made, so a seed that does nothing can't pass. It was red against a
     stub that seeded nothing.
- **Decisions:**
  - The gallery's controls sit in the page, because the side panel starts
    collapsed there.
  - The type filter takes one type.
  - "Newest" is `created_at`; there's no "made public at" field, and none
    was added.
  - Search works like the library's: every word is in the title or a tag
    (tidied like a tag).
  - Empty public packs are listed, reading "No items yet".
  - The collapsed start doesn't overwrite the member's saved panel choice.
  - Demo accounts are `demo_mira`, `demo_otto` and `demo_juno`, with the
    password `toolbox-demo`.
  - 43 assets rather than exactly 40, because the themed packs share a few.
  - The demo includes one private pack, to show the 404 rule, and CC BY,
    CC BY-NC and Sampling+ sounds, so the credits and compatibility warnings
    have something to show.
  - A second seed run restores the demo packs but leaves members' own entry
    edits alone.
  - The snapshot and the seed live in `packs`, the app that depends on
    `catalog`.
- **Deviations:** the user asked for the privacy test's hidden packs to
  match every query (prompt 2), and it was built that way. After the first
  green, the user asked to stop only at reds.
- **Sideways:**
  - The first privacy test used the query "Castle Fortresses", which tidies
    to "fortresse" and would never match the tag "fortress". It was caught
    before the red was shown and changed to "Castle FORTRESS".
  - `{% for value, label in gallery_sorts.items %}` crashed, because the
    sort key `"items"` hid `dict.items()`. The view now passes the pairs as
    a list.
  - The existing hero test caught a second `btn-primary` ("Sign up free" in
    the steps) and an extra member link. Both were removed, keeping the
    hero's Search as the page's one primary action.
  - `rjust` would have drawn one blank tile when none was needed, so the
    card has `blank_tiles` instead.
  - The seed test first wrote its output to `/dev/null`, which doesn't
    exist on Windows. It uses `StringIO` now.
  - Killing the scratch server with `pkill -f` matched the shell running it
    (exit 144) until the pattern was bracketed.
  - The headless Firefox screenshot showed type icons instead of
    thumbnails, because lazy images load after the shot is taken. The URLs
    were checked with `curl`, and thumbnails are left to the manual test.
  - The README was checked in a fresh copy of the working tree, not a real
    `git clone`, because the files weren't committed yet.

## 2026-11-06 — Consistent layout, Discover license filters and drawer, packs as a list, sounds everywhere

### Prompts

1. Ok there are a few changes that I would like to make, the individual pack
   page is not centered like the rest of the pages, please ensure from this
   point forward all styling is kept consistent with current and future
   pages.
   On the license guide in the symbols section the Usable, With Conditions,
   Not Usable; the Not usable looks strange has the icon and the text are on
   two seperate lines please fix this to be like the other icon legends.
   The "On this page" section show the individual pages and their licenses
   can you collapse all of the licensesto clean up the sidebar menu a
   bit.Also use Iconography for the sidebar menus where appropriate for all
   menus.
   For the disccover menu can you show the license type in iconography and
   more specifically add a sort option to allow users t filter out results
   based on license type and whther commerical use is allowed or not.
   For the packs page currently packs are displayed as a grid, can you make
   it optional to have packs displayed vertically in a list.
   Currently audio assets have no way of being played except when in the
   discover menu can you please add a way for them to be played in the pack
   menu or library.
   For the discover menu can you please have the sidebar menu displayed such
   as in the library menu, but still offer a way to navigate to the website
   where it was sourced from.
   Following these changes please update PROMPTS.md according to source
   formatting
2. (Sent while the agent was working.) Ok the pack page and the pack editor
   have asset icons that are oddly alligned can you fix this to allign them
   more properly with the rest of the content

### Summary

- **Outcome:** every request built, recorded in the plan as "Phase 8 polish,
  third request" and in the PRD as stories 120–125. 1,073 tests pass (1,024
  before; 49 new across `test_discover_licenses.py`, `test_discover_drawer.py`,
  `test_sound_playback.py`, `test_pack_layout.py` and additions to
  `test_shell.py` and `test_attribution.py`); `ruff check` and `ruff format`
  are clean. Nothing was committed.
  - **Consistency:** the pack page, New pack and the Remove confirm are
    centred columns like the entry, Attribution and Account pages. A new
    "Page widths" section in docs/FRONTEND.md sets the rule for future
    pages (full width for browsing and working, otherwise a centred column,
    plus the shared components to reuse), and a test checks every column
    class.
  - **License guide:** the legend's stacked layout rule had caught the
    verdict key's last item, which is why "Not usable" broke onto two lines;
    it's scoped with `:not(.symbol-legend-key)` now. "On this page" folds the
    eleven licenses into one remembered "Licenses" row.
  - **Iconography:** every side-panel row (Account pages, Attribution center,
    each pack, On this page) and every filter group has an icon; new icons
    key, tag, globe, table, quote, shapes, external and coin.
  - **Discover:** each card shows its license as symbols and its commercial
    verdict. A side panel like the library's filters by license and by
    commercial use. CC0-only providers are kept or dropped with no request,
    and Openverse is asked for the allowed licenses. A result now opens in a
    drawer like the library's (`catalog:discover_asset`,
    `catalog/preview.py`), with View on <provider> as its primary action,
    Save, Add to pack, the license and its uses, and the downloads. Each
    card also keeps View on <provider> in its corner.
  - **Packs:** a Grid / List switch on Your packs, remembered in the session.
  - **Sounds:** library cards, the library drawer, builder items and pack
    page items play a sound's first stored file through Discover's player.
  - **Second prompt:** the builder's drag grip stretched the row and floated
    half way down, away from its thumbnail; the type line sat a few pixels
    below the thumbnail's top; and an empty status line left a band under
    each row. All three are fixed, with 24 px type icons in empty
    thumbnails.
- **Deviations:** no questions were asked. Two readings were the agent's
  own, reported for review. "Have the sidebar menu displayed such as in the
  library menu" was read two ways at once: a side-panel filter list like the
  library's, and the library's slide-in drawer for a result (keeping the
  source site one click away in the drawer and on the card). "A sort option"
  for license type was built as filters, since sorting by license wouldn't
  remove anything. The packs layout is kept in the session rather than the
  browser, so the server renders it with no flash.
- **Sideways:** twelve existing tests pinned the old card markup, sidebar
  icon sizes and row text; they were updated to the new markup on purpose.
  The first try at adding a play button to pack items failed on a comment
  anchor that didn't match, and was redone. The alignment fix was checked in
  headless Firefox, on a scratch copy of the database with a throwaway
  auto-sign-in settings file (the real database untouched), before and
  after. The drawer's opening, the autosubmitting chips and audio playback
  were not driven in a real browser (only server-side tests and static
  screenshots), so try them by hand.

## 2026-11-05 — Pack builder polish, pack and item downloads, credits and the Attribution center

### Prompts

1. Alright a few thinkgs I want to change the current pack builder is ok but
   I do want to make it a little better. In the add from library section I
   want to make it by default not show items taht I have already added. Also
   there is no arrow for me to view additional items. I would also like to
   see a thumbnail image view of the asset to let me get a visual on what I
   might be adding. For the pack itself I want to be able to downloa the raw
   files as well as the import manifest. I would also like some more
   information on the credits essentially what attribution is required and
   how to gain the attribution requiements for the specifc licenses as well
   as optional credits if desired. Additionally I think it would be cool if I
   can optionally download one asset. Next I would like to be able to drag
   and drop items as well as auto sort them. The variant dropdown menu is
   also not formatted in css. Please give site viewers a idea of what the
   import path means. You can also create a new tab for attribution center
   giving user an idea of hat each license type is and means and what
   licenses are on a specifc asset or what licenses are active on a pack and
   how to address them.
2. Ok for the attribution center can you seperate the pages based on guide
   and individaul attribution for each pack or asset. Also for the copy and
   paste section I would like to make it more formal and infomative to all
   viewers dictating specifically how they can and can not use it. For the
   lookup section I would also like it to have filters to license types and
   credit requirements.
3. Ok for the licenses I feel like it would be better to list them on row at
   a time also the license guide page and other attribution pages are not
   centered accross the page with their content. I also think some
   iconography would be nice here with some visual guides. For the actual
   packs I would like them to show license compatability when they can not
   be used for the project commericial personal or internal use. Essentially
   stating that this pack may not be usable due to these reasons edit the
   pack or contact the owner before using.
4. Go ahead and append this session to PROMPTS.md

### Summary

- **Outcome:** the builder, the pack page and a new Attribution center, built
  on top of the still-uncommitted Phase 8 polish. Recorded as a second Phase 8
  polish section in the plan (with a third and fourth request below it) and as
  PRD stories 107–119. 1,024 tests pass at the end (976 after the first
  request, 1,001 after the second); `ruff check` and `ruff format --check` are
  clean. Nothing was committed.
  - **Builder:** Add from my library hides what's already in the pack (a
    checkbox shows it again, and the hidden count is said), pages 12 at a
    time with Previous/Next arrows, and shows each asset's thumbnail with a
    bigger preview on hover. Items drag by a grip (`reorder_items()`; a stale
    order is a 400 that changes nothing) and auto sort by type, title,
    provider or license (`sort_items()`). The variant dropdown is styled
    (`.ax-select`) and shows each variant's file count and size.
  - **Downloads:** Download files zips the whole pack in the browser, each
    file under its item's import path, with CREDITS.txt and the manifest; each
    item can be downloaded alone. The Toolbox only lists the providers' URLs
    (`packs/downloads.py`, `packs:files`), so the PRD's Out of Scope holds.
  - **Import paths:** a "What's an import path?" explainer with an example
    project tree, and a hint under each item's field.
  - **Licenses and credits:** `catalog/licenses.py` reads every license as the
    providers write it and says what it allows; `packs/credits.py` groups a
    pack's items by license, with required credits equal to the manifest's
    (the manifest itself is unchanged).
  - **Attribution center** (a new sidebar tab), split by the second prompt
    into the license guide (everyone), pack attribution (a page per pack, on
    the pack page's reader rule, by share link for unlisted packs) and asset
    attribution (the member's library, filtered by license type and credit
    rule, with a page per asset).
  - **The notice:** a formal Attribution and License Notice (who owns the
    assets, required attribution, each license's You may / You must / You may
    not, permitted uses, restrictions, optional acknowledgements, a
    disclaimer). It's the CREDITS.txt in every download and the text to copy,
    with a short credit-lines version beside it.
  - **Third prompt:** one license per row, the Attribution pages centred,
    license symbols with a legend and a "Can I use it?" verdict (commercial,
    personal, internal), and each pack's license compatibility, with a
    warning that tells the owner to edit the pack and anyone else to contact
    the owner. It's on the pack page, the pack's attribution and the builder.
- **Deviations:** no recommendation was overridden, and no questions were
  asked. The agent chose these defaults and reported them for review: the
  Public Domain Mark is "credit recommended" (to match the manifest, which
  credits everything that isn't CC0), and the use rules (non-commercial
  blocks commercial use and limits internal use to private testing; share-
  alike and no-derivatives add conditions; an unknown license blocks both
  public uses). The second and third prompts reshaped the Attribution center
  the first one built.
- **Sideways:**
  - The Bash tool's wrapper broke on quotes in several heredoc edit scripts,
    so the edits moved to script files in the scratchpad. One of those failed
    with nothing written, and was redone with the Edit tool.
  - A duplicate `sort` icon was added and removed at once.
  - Several new tests were wrong at first and were fixed, not the code: a
    sound's default variant is its MP3, not its OGG; pages HTML-escape
    quotes; the notice's wrapping splits phrases; a pack's attribution page
    has more use cells than its compatibility box.
  - Ruff flagged the reused fixtures as redefinitions (F811), so they're bound
    as module attributes instead of imported.
  - The read-only pack page test caught a `<textarea>` for the credits text;
    it became a `<pre>`, and Copy learned to copy an element's text.
  - The sequential CSRF test ran Remove before the new reorder write, which
    then got a 400; the write list was reordered.
  - The notice's "Prepared" date comes from `timezone.localdate()`, and a
    sample printed 6 November while the session date was 5 November.
  - Nothing was driven in a real browser: the drag and drop, the zips, the
    hover preview, the filter chips, the Copy buttons and the new icons were
    checked only by server-side tests, a JavaScript parse and a Tailwind
    build.

## 2026-11-05 — Axcenity Toolbox: Phase 8/13, Public pack page, export and pack API

### Prompts

1. The `/implement` skill, given `axcenity-toolbox phase 8`.
2. Ok looks good go ahead and make sure to explicitly test that a private
   pack's export ednpoint returns in a 404 to a signed out visitor and
   another authenticated user, while still succeeding for the owner.
3. looks good move to next (approving TDD 1's test).
4. looks good move to next (approving TDD 2's test, after TDD 1 went green).
5. looks good move on (approving TDD 3's sentinel test and its mutation
   check).

### Summary

- **Outcome:** packs can be shared and exported.
  - Every pack has a page at `/packs/<slug>/`. A public pack's page is open
    to anyone, signed out included. A private pack's page is a 404 to
    everyone but its owner. The page is read-only and lists each item's
    license, credit, variant, files and import path. Only the owner gets
    Edit in builder.
  - **Download manifest** saves the PRD's Option A manifest as
    `<slug>.axcenity-pack.json`. The API's export returns the same
    document.
  - The read-only pack API: `/api/packs/` (public packs plus your own, and
    `?mine=1`), `/api/packs/<id>/` and `/api/packs/<id>/export/`. Writes are
    a 405.
  - The builder, the pack cards and "Featured in public packs" now link to
    the pack page.
  - 877 tests pass (820 before). `ruff check` and `ruff format --check` are
    clean.
- **Changes:**
  - `packs/models.py`: `Pack.objects.visible_to()` (the one rule for who may
    read a pack), `Pack.get_public_url()`, and `RESERVED_SLUGS` (`new` and
    `picker`) in `free_slug()`.
  - `packs/manifest.py` (new): `build_manifest()` with `chosen_variant()`,
    `manifest_item()`, `is_cc0()` and `credit_line()`.
  - `packs/views.py`: `PackPageView`, `PackExportView` and `manifest_for()`,
    which the API shares.
  - `packs/api.py` and `packs/serializers.py` (new): the pack API and its
    public serializers, which reuse `AssetSerializer`.
  - `packs/urls.py`: `packs:public`, `packs:export`, `packs:api_packs`,
    `packs:api_pack` and `packs:api_pack_export`.
  - `packs/templates/packs/pack_page.html` (new). `builder.html` gains View
    pack page, `pack_list.html` a View page link on each card, and
    `catalog/partials/entry_related.html` links each featured pack.
  - `styles/source.css`: the read-only item rows (`.pack-item-read`,
    `.pack-item-facts`), `.pack-page` and `.pack-card-page`.
  - Tests:
    - new: `tests/test_pack_public.py`, `tests/test_api_packs.py` and the
      golden file `tests/golden/pack_manifest.json`
    - `tests/test_shell.py`: type colour on the pack page, signed in and
      out
  - Docs:
    - `ARCHITECTURE.md`: the URLs, `visible_to()`, the pack page, and new
      "Export manifest" and "Pack API" sections
    - `FRONTEND.md`: the pack page and the new links
    - `TESTING.md`: the new files
  - Plan: Phase 8 ticked, with "Built as" notes and notes for Phase 9.
- **TDD:** three behaviours.
  1. `visible_to()` returns public packs plus the caller's own, and public
     packs only for a visitor. It was red on an assertion against a stub
     that returned every pack.
  2. `build_manifest()` matches a hand-written golden file field for field,
     with `exported_at` frozen. The test pack has five items, arranged out
     of creation order:
     - a two-file 2K JPG
     - a `null` size
     - MP3 picked over OGG
     - a WAV-only sound
     - an asset with no variants
     - a blank and a custom import path
     - two items sharing one credit
     - a built credit line
     - CC0 left out of the credits
     It was red against a stub that returned `{}`.
  3. The sentinel: the owner's notes, rating and status, and another
     member's rating, never appear on the pack page, in either export, in
     the API list or in the API detail. It covers a visitor, the owner, and
     another member by token and by session. It was never red: the page
     and API had to exist before it could run, and they were built safe.
     Instead, four planted leaks (one at a time, each restored) proved it
     fails when it should.
- **Decisions:**
  - `visible_to()` is the one reader rule. `owned_by()` still decides who
    may change a pack.
  - The manifest looks up `preferred_variant` by its exact label. An unknown
    label falls back to `default_variant()`. An asset with no variants
    exports `variant: null`, `files: []` and `total_size: null`.
  - CC0 means the license starts with "CC0". A non-CC0 item with no
    attribution is credited as `"<title>" by <author>, <license>`. Each
    credit line appears once, in item order.
  - `exported_at` is in UTC to the second. Pack tags are listed A–Z, and
    `source_url` is the absolute URL of the pack's page.
  - The API list pages by 12, in the library API's shape. A signed-out
    `?mine=1` is a 401.
  - `new` and `picker` are reserved slugs, so a pack's page can never hide
    behind `/packs/new/` or `/packs/picker/`.
  - The pack page shows no community rating. A visitor's side panel gets
    "Shared pack" with Sign up. The download link isn't boosted, because a
    boosted link would swap the JSON into the page.
- **Deviations:** at the user's request, one named test checks both export
  endpoints (the website and the API): a private pack's export is a 404 for
  a signed-out visitor and for another member, and works for the owner.
- **Sideways:**
  - The sentinel's first version missed a leak of the notes on the page.
    The sentinel text held an apostrophe, which Django escapes, so the
    search never matched. The mutation check caught it. The sentinel is
    now plain characters, and the test also searches for the escaped form.
  - A Python heredoc mis-encoded `·` on Windows, so one replacement in a
    test silently didn't apply. It was redone with the Edit tool, and the
    changed files were checked for mangled characters.
  - `_text()` in the page tests turns a non-breaking space into a plain
    one, so the size assertion was corrected to match (a mechanical fix).

## 2026-11-05 — Lava-lamp drops, versioned static files, centred Account pages

### Prompts

1. Ok it is getting better I kind of want the animations to be a little
   faster the bubbles a little looser and bigger almost looking like a lava
   lamp. Also I clicked the light dark and auto in the appearance settings
   and it did not change anything. Also the settings menus are not centered
   so the do not look skewed to the left instead of centered.

### Summary

- **Outcome:** all three are done. 820 tests pass (815 before). `ruff check`
  and `ruff format --check` are clean.
  - **Lava lamp:** the drops are 620–1300 px across (were 460–980), with
    looser shapes and a deeper wobble. They're about three times faster:
    18–34 s to rise or fall (were 50–95 s) and a 5–9 s wobble (were 9–16 s).
    They travel 180–480 px up or down, stretching tall and thin as they move
    and squashing wide as they turn, like wax in a lava lamp.
  - **Appearance chips:** a fresh page in headless Edge switched Light,
    Dark and System correctly, so the code wasn't at fault. The likely cause
    was the browser still running the cached `shell.js` from before the
    switch existed: the static URLs never changed, so a normal reload kept
    the old copy. The title bar's switch still worked because, without the
    new script, it falls back to a plain form post. Now the stylesheet and
    every script load through a new `{% versioned_static %}` tag that adds
    `?v=<last change>`, so every change is a new URL. Rechecked in Edge after
    the change.
  - **Centring:** Profile, Settings and API token now share one centred
    column (`max-w-3xl mx-auto`). Before, each had its own width and sat to
    the left.
  - Docs: FRONTEND (the drops, versioned URLs, the Account pages), TESTING
    and the plan.
- **Deviations:** none. The chip fix addresses the cause found (stale
  cached files) rather than changing the switch, which already worked.
- **Sideways:** the regex that swapped the script tags left stray
  backslashes in `base.html` (the shell's escaping again); caught on
  inspection before any test ran.

## 2026-11-05 — Water-drop glow, the giant watermark removed, a manual light/dark switch

### Prompts

1. Ok the gradient blobs are nicer but I would like them to be bigger and
   move more like water drops. Also I would like the axcenity logo large
   watermark to be in the foreground not at the bottom of the page if it
   does not look clean please jyust remove it. Additionally there is
   currently no manual way to set the light and dark settings I wouldlike
   there to be a way to do this.

### Summary

- **Outcome:** all three are done. 815 tests pass (802 before). `ruff check`
  and `ruff format --check` are clean.
  - **Water drops:** each blob is now a drop 460 to 980 px across. It sinks
    and rises slowly, mostly up and down, and wobbles: as it stretches one
    way it squashes the other, keeping its volume like water. Its light sits
    off-centre, and two thin shells follow its wobble 0.6 s and 1.2 s behind,
    like the layered edges in the reference image. There are fewer of them
    (one per 600 px of page), so the bigger drops don't crowd.
  - **Watermark:** tried first as asked, pinned to the bottom of the view
    behind the content. On the library it filled the empty space well, but
    on a scrolled entry page only "nity" showed between the panels. That
    isn't clean, so it was removed, as the user allowed. The top-right mark
    and the small footer wordmark stay.
  - **Light and dark:** System, Light or Dark. A sun, moon or monitor switch
    in the title bar steps through them (visitors too), and Settings has
    Appearance chips. The choice is the `ax-theme` cookie, so pages render in
    it from the first paint; System follows the computer live. Without
    JavaScript, both are forms posting to the new `accounts:theme` (CSRF).
    The light palette moved from a media query to `html[data-scheme="light"]`.
  - Docs: FRONTEND (light and dark, the drops, branding, Settings),
    ARCHITECTURE (`accounts:theme`, the context), TESTING
    (`test_theme_switch.py`), CLAUDE.md's colour rule, the PRD (stories 103
    and 104) and the plan's Phase 7 polish.
- **Decisions:** the theme lives in a cookie, not the database, so it works
  for signed-out visitors and the server can render it before first paint.
  It's per browser, not per account. The switch was click-tested in headless
  Edge: System → Light → Dark → System, the background and label changing
  each time.
- **Sideways:**
  - The first test run found the sign-in and sign-up pages listing their own
    URL in the title bar: the theme form's hidden `next` field. The field
    was dropped; without JavaScript the view returns to the Referer instead,
    when that's on this site.
  - The giant watermark's foreground version was built and screenshotted
    before it was removed, so the removal rests on how it actually looked.

## 2026-11-05 — Files, download defaults and bundles, status history, centred entry page, ambient glow

### Prompts

1. Alright some changes I would like to make to my toolbox the library entry
   has a large assortment of files to choose from. I feel like it woud be
   nice to differentiate between different resolutions file formats and
   image types as well as give the user the option to choose which types
   they would like to default to in the settings, as well as an option to
   download the files as a bundle according to those selected settings. Also
   when the item is fullscreened in the window it looks off center I also
   feel like some other things that can be included in the fullscreen menu
   are items similar to this or collections the item has been featured in.
   Also considering this tool can be used within an optional team
   environment I feel like it would be nice to know who set the review
   status and why. Another thing that I noticed is the tags menu can be
   quite extensive Can we make it expandable and collapsible and show the
   highest tags like it is currently. Next the Axcenity logo is being
   shrouded on some of the menus. can you make sure it is in some way being
   place in the foreground of all menus and pages similar to the front page.
   Also the animations looks a little too consistent and symmetrical thee
   were some of the gradient designs I was looking at I would like them to
   be fluid random and suble going through all of the page regardless of
   size. Also when completed please append this section to PROMPTS.md
   (with a reference image of soft, layered gradient blobs)
2. (Sent while the work was under way.) Ok another thing I noticed
   occasionally when I scroll down it just loads empty space can this be
   fixed as well. (with a screenshot of the library page scrolled past the
   status bar into blank space)

### Summary

- **Outcome:** all nine requests and the scrolling bug are built and tested.
  802 tests pass (725 before). `ruff check` and `ruff format --check` are
  clean.
  - **Files told apart:** `catalog/files.py` reads each variant's
    resolution, format and package (loose maps, bundle, archive, audio) and
    each file's map type (Color, Normal GL, Roughness…). The drawer badges
    them, filters by resolution and format, and marks "Your default".
  - **Download defaults:** a `DownloadPreferences` model (resolution, a
    format per kind, texture maps), edited on the Settings page with chips
    that save on change.
  - **Download bundle:** `pick_bundle()` chooses the files from the defaults
    (nearest resolution below, then above; format fallbacks; only the chosen
    maps). One file is a plain link. Several are fetched and zipped by the
    member's browser (`static/js/bundle-download.js`, a small stored-zip
    writer) with a CREDITS.txt.
  - **Full page:** centred two-column layout, with "Similar in your
    library", "Featured in public packs" and "Find more like this on
    Discover". The drawer shows them too.
  - **Status history:** a `StatusChange` model records who set each status,
    when, via the website or the API, and an optional reason. It's shown
    under the status chips with a folded history, and the API reads and
    writes it (`status_change`, `status_reason`).
  - **Tags:** the first 8 show and the rest fold behind "Show N more",
    remembered in the browser.
  - **Logo:** the mark is on every page, layered above the glow, and in the
    drawer.
  - **Glow:** one ambient layer runs through the whole page. `ambient.js`
    scatters organic blobs with random shapes, gradients, paths and speeds,
    replacing the symmetrical hero and footer glows with ripple rings.
  - **Empty space:** the side panel's hidden chip inputs were positioned
    against the sidebar (which doesn't clip), so a long tag list made the
    whole document taller than the window. `.filter-chip` is now
    `position: relative`. Measured in headless Edge: the document went from
    1514 px to the window's 761 px.
  - Docs: ARCHITECTURE, FRONTEND, TESTING, CLAUDE.md (the colour rule now
    says the glow drifts behind the whole page), the PRD (stories 95–102)
    and the plan (a Phase 7 polish section, with notes for Phase 8).
- **Deviations and decisions:**
  - The PRD rules out downloading or proxying files, so the bundle is built
    in the browser from the provider's URLs instead of on the server. Only
    Poly Haven has multi-file variants, and its CDN sends
    `Access-Control-Allow-Origin: *`. Checked against two real Poly Haven
    files in headless Edge with web security on: Python's `zipfile`
    verified every CRC.
  - There are no teams in the Toolbox, so "who set it" is always the
    entry's owner (or their API token) for now; the record names the person
    so it stays right if teams arrive.
  - "Collections" were dropped earlier in favour of packs, so "featured in"
    lists other members' public packs. They aren't links yet: the public
    pack page is Phase 8 (noted in the plan).
  - This work sits outside the plan's phase order because the user asked
    for it. It's recorded as Phase 7 polish.
- **Sideways:**
  - The first screenshots showed no footer wordmark. That was CSS masks
    refusing a `file://` page, not the site; rerendering with web security
    off showed the real page.
  - Shell heredocs turned `\n` escapes into real newlines and broke
    `catalog/library.py` once. Later edits went through files written with
    the Write tool.
  - The first measurement after the scrolling fix still showed the overflow
    because Edge served the cached stylesheet; a fresh profile confirmed
    the fix.
  - A new test caught a real bug: counting tag use through `asset.tags`
    counted only that asset, so "Find more" fell back to A–Z tags. It now
    counts over every asset.
  - The local `db.sqlite3` needed `migrate` for the two new migrations
    (`accounts.0001_initial`, `catalog.0002_statuschange`).

## 2026-11-05 — Axcenity Toolbox: Phase 7/13, Pack builder

### Prompts

1. The `/implement` skill, given `axcenity-toolbox phase 7`.
2. Looks good I would just make sure to combine multi-step database
   operations in transactions where appropriate. This is mostly concerning
   pack creation, item insertion, and ordering changes.
3. Looks good move to next (approving TDD 1's test).
4. Looks good move to next (approving TDD 2's test, after TDD 1 went green).
5. Looks good move on (approving TDD 3's test, after TDD 2 went green).

### Summary

- **Outcome:** packs work end to end.
  - A member can create a private pack with a title, an intended use and
    comma-separated tags (tidied by `normalize_tag()`). They can switch it
    public and back, rename it, edit it and delete it.
  - The builder autosaves every control: the details, each item's variant
    and import path, and Move up, Move down and Remove. "Add from my
    library" searches as you type.
  - The Add to pack picker on library cards and Discover results lists the
    member's own packs. On Discover it saves the result first (To review).
  - Remove from library now opens a dialog listing the packs the entry
    will leave, and the drawer lists the packs an entry is in.
  - 725 tests pass (650 before). `ruff check` and `ruff format --check` are
    clean.
- **Changes:**
  - `packs/models.py`: `Pack` (with `create_pack()` and `free_slug()`, and
    `owned_by()`), `PackItem`, `default_variant()` and `tags_from_text()`.
    `packs/migrations/0001_initial.py`.
  - `packs/services.py` (new): `add_to_pack()`, `add_from_provider()` and
    `move_item()`, each in one transaction.
  - `packs/forms.py` (new): `NewPackForm`, `PackDetailsForm` and
    `PackItemForm`. The last two save only the posted field.
  - `packs/views.py`, `packs/urls.py`: the pack list, New pack, the builder
    and its eight POST URLs, Add from my library, and the picker with its
    add. Members only, the owner's pack or a 404, with CSRF.
  - `packs/admin.py`: Pack with its items inline.
  - `packs/templates/packs/`: the list, New pack and the builder, plus
    partials for the side panel, the title, the status lines, the
    visibility switch, the items and their rows, the library search and the
    picker list.
  - `catalog/views.py`: `RemoveFromLibraryView` gains a GET confirm (the
    dialog, or a page). `_own_entry()` prefetches the entry's packs.
  - `catalog` templates: the picker loads its list over HTMX. Remove (card
    and drawer) opens `#remove-dialog`. New `remove_dialog.html` and
    `remove_confirm.html`. The drawer gains a Packs section.
  - `static/js/card-actions.js`: loads the picker list on open, opens a
    dialog HTMX has filled, `data-dialog-open` and `data-dialog-done`.
  - `templates/partials/icon.html`: `arrow-up` and `arrow-down`.
  - `styles/source.css`: the pack list, the builder, the picker's packs,
    the Remove dialog, the drawer's packs and `.textarea`.
  - Tests:
    - new: `tests/test_packs.py` and `tests/test_pack_builder.py`
    - `tests/test_access_control.py`: the Phase 7 access rules
    - `tests/test_shell.py`: New pack in the page lists, and pack items'
      type colour
    - four library and drawer tests rewritten from the browser confirm to
      the dialog
  - Docs:
    - `ARCHITECTURE.md`: a Packs section, the URLs and the Remove confirm
    - `FRONTEND.md`: the packs pages, the picker and the Remove dialog
    - `TESTING.md`: the new files
  - Plan: Phase 7 ticked, with notes for Phase 8.
- **TDD:** three behaviours, each red on an assertion first:
  1. `add_to_pack()` appends once per entry and refuses another member's
     entry. It was red because the stub reported `created=True` for the
     duplicate.
  2. `default_variant()` picks a 2K JPG, an MP3 for sounds, otherwise the
     first variant. Seven cases. It was red because the stub returned "".
  3. `add_from_provider()` saves a Discover result as To review first,
     reuses an existing entry untouched, and on a `ProviderError` saves and
     adds nothing. It was red because the stub saved nothing.
- **Decisions:**
  - The owner's pages use the pk (`/packs/<id>/edit/`), so `/packs/<slug>/`
    stays free for Phase 8. The slug is set once and survives a rename.
  - The order is changed with Move up and Move down, not drag and drop
    (that would need a vendored JS library).
  - Variant labels are matched ignoring case and hyphens (ambientCG writes
    "2K-JPG") and stored as written.
  - An import path must be relative, with no `..`, and up to 300
    characters. Backslashes become `/`.
  - Remove's confirm is a GET on `catalog:remove`, so it also works as a
    page without JavaScript.
  - Add from my library marks entries already in the pack "In pack" rather
    than hiding them.
- **Deviations:** at the user's request, pack creation, adding an item,
  Discover's save-then-add and reordering each run in one
  `transaction.atomic()`. `move_item()` also rewrites the positions, which
  closes the gaps that removes leave.
- **Sideways:**
  - I wrote `default_variant()` before its test, then put it back to a stub
    so TDD 2 could start from red.
  - TDD 3's first run failed with `DoesNotExist`, not an assertion. The
    test's lookup became `.filter().first()` (a mechanical change).
  - The first run of the page tests had four mistakes, all in the tests:
    - `HX-Trigger` is sent as JSON
    - a split was off by one attribute
    - an apostrophe isn't escaped in that template
    - a leading newline in the reply
  - The access tests caught a real gap: a signed-out plain GET on a pack's
    fragment URL went to sign-in and came back to the fragment. Every pack
    URL now returns to the builder.

## 2026-11-05 — Axcenity Toolbox: Phase 6/13, Library API and token page

### Prompts

1. The `/implement` skill, given `axcenity-toolbox phase 6`.
2. Looks good just make sure that session-authenticated POST/PATCH/PUT/DELETE
   uses CSRF while token-authenticated requests work without session CSRF.
3. Looks good move to next (approving TDD 1's test).
4. Looks good move to next (approving TDD 2's test, after TDD 1 went green).
5. Looks good move to next (approving TDD 3's test, after TDD 2 went green).

### Summary

- **Outcome:** DRF is set up with token and session authentication. The
  library API:
  - `GET /api/library/` lists the caller's entries through
    `filter_library()`, with the library page's parameters, order and pages
    of 12
  - `POST /api/library/` saves an asset from its provider and ID, plus an
    optional review: a duplicate is a 400 "Already in your library.", and a
    `ProviderError` is a 502 with its message
  - `GET`, `PATCH`, `PUT` and `DELETE /api/library/<id>/` work on the
    caller's own entries only (404 otherwise)

  A token page at `/accounts/token/` shows the member's token, creating it
  on the first visit. 650 tests pass (577 before). `ruff check` and
  `ruff format --check` are clean.
- **Changes:**
  - `pyproject.toml`, `uv.lock`: `djangorestframework` 3.18.3.
  - `config/settings.py`: `rest_framework` and `rest_framework.authtoken`,
    and `REST_FRAMEWORK` (token first, then session; `IsAuthenticated`;
    JSON only). The authtoken migrations come with DRF.
  - `catalog/serializers.py` (new): `AssetSerializer` (Asset fields only,
    read-only), `LibraryEntrySerializer` (the owner serializer: notes,
    rating, status and the community rating, the same rules as
    `ReviewForm`, saving only the fields sent) and
    `NewLibraryEntrySerializer` (adds `provider` and `external_id`).
  - `catalog/api.py` (new): `LibraryAPI` (list and create) and
    `LibraryEntryAPI` (read, update, delete, scoped by `for_user()`). The
    entry view's docstring, served as the `OPTIONS` description, says
    DELETE also leaves the member's packs.
  - `catalog/urls.py`: `catalog:api_library` and `catalog:api_entry`.
  - `catalog/library.py`: `save_to_library()` takes the review for a new
    entry as keyword arguments; `LibraryParams.query_string()` builds the
    tidy query string for both the page's `url()` and the API's links.
  - `accounts/views.py`, `accounts/urls.py`, `accounts/token.html`:
    `TokenView` (`accounts:token`, members only, never cached), with a
    `curl` example.
  - `accounts/partials/account_pages.html` (new): the Account side panel
    (Profile, Settings, API token), shared by the three pages; the profile
    links to the token page.
  - Tests: `tests/test_api_library.py` and `tests/test_token_page.py`
    (new); the token page added to `test_access_control.py`'s members-only
    pages and `test_shell.py`'s member pages.
  - Docs: `ARCHITECTURE.md` (a Library API section, URLs,
    authentication), `TESTING.md` (the new files, the API's CSRF and 401
    rules), `FRONTEND.md` (the panel rows). Plan: Phase 6 ticked, plus a
    note for Phase 8.
- **TDD:** three behaviours, each red on an assertion first:
  1. Another member's entry is a 404 for GET, PATCH, PUT and DELETE, and
     nothing changes. It was red with 200/204, because the scaffold's
     queryset read every entry.
  2. A duplicate save is a 400 "Already in your library.", with no
     provider call and the entry untouched. It was red with 201.
  3. A `ProviderError` on create is a 502 with its message, and nothing is
     stored. It was red with 500.
- **Decisions:**
  - The URL names are `catalog:api_library` and `catalog:api_entry`, using
    generic views rather than a router.
  - Token authentication comes first, so signed out is a 401.
  - The duplicate error uses the 502's `{"detail": …}` shape.
  - Asset fields in PATCH or PUT are ignored, not rejected.
  - The list's reply is `{count, page, num_pages, next, previous,
    results}`.
  - The browsable API is off, because its Bootstrap colours sit outside
    the palette.
  - The token page has no regenerate button, since the PRD doesn't ask for
    one.
- **Deviations:** none. At the user's request, the CSRF tests cover all
  four writes (POST, PATCH, PUT, DELETE) three ways: a session without
  CSRF is refused, a session with the token succeeds, and a token without
  CSRF succeeds.
- **Sideways:** the first run of the new tests had two mistakes, both in
  the tests:
  - tags come back A–Z (`Tag.Meta.ordering`), not in the order given
  - the test helper sent GETs a JSON body

  Both were fixed in the tests; the code didn't change. The 502 test needed
  `Client(raise_request_exception=False)` to see the 500 as a client would.

## 2026-11-05 — Axcenity Toolbox: Phase 5/13, Library drawer (plus polish)

### Prompts

1. The `/implement` skill, given `axcenity-toolbox phase 5`.
2. Looks good one thing to look into is to make the notes autosave
   resilient to failed requsts. Keep the user's unsaved text aand display
   an error rather than losing their changes.
3. Looks good move to next (approving TDD 1's test).
4. Looks good move on (after TDD 1 went green).
5. Looks good move to next test (approving TDD 2's test).
6. Looks good move to 3 (after TDD 2 went green).
7. Looks good move to next (approving TDD 3's test).
8. Looks good move on (after TDD 3 went green, to build the rest).
9. At the commit question: Don't commit.
10. Ok so an issue that I notice when loading the sidebar menu is that it
    brefily pops up goes away then it reappears and stays essentially it
    does not transition very smoothly. For the reviews I want to make sure
    they are for all users meaning it will average all the reviews accross
    all accounts. Also for the sidebar menu I noticed that it seperates the
    icos and the text I would like those to be together when expanded.
11. Answers to the follow-up questions:
    - the flicker is in the library drawer
    - add a community average beside each member's own private rating
    - show it in the drawer, on library cards and on Discover results, and
      add a library sort
    - merge the sidebar into one column, each icon beside its label

### Summary

- **Outcome:** Clicking a library card's title opens a slide-over drawer at
  `/library/<id>/`, and a direct visit shows the same entry as a full
  page. The drawer shows:
  - the asset's details, license and attribution, source link, tags,
    saved date and file variants
  - the review: status chips and star radios that save on change (the
    rating can be cleared), and notes that save after a 0.7 s pause and
    on blur
  - Remove from library

  A status or rating change from the library updates the card behind the
  drawer out of band. Notes autosave survives failures (the user's
  addition). 562 tests pass (524 before). `ruff check` and
  `ruff format --check` are clean.
- **Changes:**
  - `catalog/forms.py` (new): `ReviewForm` binds only the posted fields
    (the rest at their stored values) and saves only those
    (`update_fields`). It gives one-sentence errors for a bad rating,
    status or over-long notes, keeps notes as typed and stores line
    breaks as LF.
  - `catalog/views.py`:
    - `EntryView` returns the drawer fragment or the full page, and sends
      a signed-out drawer request to sign-in with `HX-Redirect`.
    - `UpdateEntryView` replies with the status line: "Saved", or a 400
      that saves nothing. The card goes out of band only for a status or
      rating change from the library. A plain POST redirects to the
      entry. A signed-out HTMX save gets a 401 with a sign-in link.
    - `_own_entry()` scopes every lookup to the member, and
      `_from_library()` reads `HX-Current-URL`.
    - `_wants_results_only` is renamed `_wants_fragment`.
    - `RemoveFromLibraryView` now treats a boosted POST like a plain one.
  - `catalog/urls.py`: adds `catalog:entry` and `catalog:update`.
  - Templates:
    - new: `catalog/entry.html`, plus the partials `entry_detail.html`,
      `entry_drawer.html`, `entry_save_status.html` and
      `entry_remove.html`
    - `library_card.html`: the title opens the drawer, and the card can
      be sent out of band
    - `library.html`: holds the `<dialog id="library-drawer">`
    - `icon.html`: adds an `expand` icon
  - `static/js/entry-drawer.js` (new): opens and closes the drawer. For
    notes, it:
    - keeps a localStorage draft until a save of that exact text succeeds
    - restores a leftover draft and saves it when the entry reopens
    - shows its own message for errors the server doesn't explain, and
      for a dropped connection or a timeout
    - offers Try again, and retries on its own when the browser is back
      online
    - sends the newest CSRF token from the cookie
    - asks before closing, switching entries, navigating or unloading
      with unsaved notes
  - `static/js/card-actions.js`: Escape ignores any open dialog.
  - `templates/base.html`: loads the new script.
  - `styles/source.css`: the drawer, the entry layout, the star input
    (with a `:has()` fill and hover preview) and the status line, with
    reduced-motion overrides. Also removed one stray line (see Sideways).
  - Tests:
    - `tests/test_library_drawer.py` (new, 22 tests, 32 cases)
    - `tests/test_access_control.py`: the Phase 5 rules
    - `tests/test_library_page.py`: the title now opens the drawer
    - `tests/test_theme.py`: a brace-balance check on `source.css`
  - Docs:
    - `docs/ARCHITECTURE.md`: the URLs, the drawer and saving
    - `docs/FRONTEND.md`: the "Library drawer" section and the
      type-colour list
    - `docs/TESTING.md`: the new test file and the access rules
  - `plans/axcenity-toolbox.md`: ticked Phase 5, added the autosave
    criterion and a note for Phase 7.
  - `prd/axcenity-toolbox.md`: recorded the autosave addition under the
    drawer.
- **Polish (prompts 10–11):**
  - **Drawer flicker:** htmx ran the drawer's swaps through the global
    View Transitions, so `#content` faded out and back in behind the
    drawer as it opened. The drawer's own swaps (opening it, every save,
    its Remove) now use `transition:false`.
  - **Community rating:**
    - `SavedAssetQuerySet.with_community_rating()` adds the average and
      count, as subqueries so each entry stays one row.
      `SavedAsset.community` wraps them.
    - `community_ratings()` serves Discover.
    - There's a new `community` library sort, with assets no one has
      rated last.
    - `community_rating.html` shows it on library cards and Discover
      results. `entry_community.html` shows it in the drawer and is sent
      again out of band after a rating change.
    - There's a `lookup` template filter (`catalog/templatetags/`).
    - `tests/test_community_rating.py` has 9 tests.
  - **One-column sidebar:**
    - `base.html` merges the activity bar and the side panel into one
      `<aside id="side-panel">`: the toggle with the panel title, the main
      nav, the page's own panel, then Account and Settings.
    - Each entry is an icon cell with its label beside it, plus a tooltip
      shown only while collapsed. The duplicate Discover, Library and Packs
      text rows are gone.
    - The CSS animates 16 rem ↔ 3.5 rem, with the labels staggered.
    - 8 shell and library tests were rewritten for the new layout.
  - Docs, the plan (a "Phase 5 polish" section) and the PRD (stories 93
    and 94) record all three. The suite is at 571 tests, and ruff is
    clean.
- **TDD:** three behaviours, each RED on an assertion before any code:
  1. An update changes only the field it posts.
  2. A rating of 1 to 5 saves and an empty one clears it. Anything else is
     a 400 with "Choose a rating from 1 to 5." and nothing saved, not even
     the notes posted alongside it.
  3. Another member's entry is a 404 to view (drawer and page) and to
     every update, and nothing changes.
- **Decisions:**
  - one update URL that saves only what's posted, so concurrent saves
    don't overwrite each other
  - opening the drawer doesn't change the address bar; the title stays a
    real link, and the drawer has "Open as page"
  - the card goes out of band only when the change came from the library
    page
  - a changed card stays in the grid even if the filter no longer matches
    it
  - notes are capped at 10,000 characters in the form only, so no
    migration
  - the pack list in the drawer is left for Phase 7
- **Deviations:**
  - Ratings were private per member under the PRD. At the user's request,
    every page now also shows an anonymous community average with its
    count, from the first rating (the user chose this over hiding it until
    3 ratings). Each member's own rating stays private. Noted for Phase 8:
    keep community ratings off public pack pages, or allow for them in
    the sentinel test.
  - The sidebar's two-column design from Phase 1 was replaced at the
    user's request.
  - The user added the notes autosave resilience to the
  approved brief. To keep the text when the session has ended, a
  signed-out HTMX save gets a 401 status line with a sign-in link in a new
  tab. Remove instead redirects the whole window (`HX-Redirect`). A plain
  POST is still sent to sign-in.
- **Sideways:**
  - The first TDD 2 run failed with a `ValueError` (saving an invalid
    form), not an assertion. The scaffolding got an `is_valid()` guard,
    and the re-run failed on `200 == 400`.
  - `tailwind build` failed on a stray line in `styles/source.css` (line
    438, left after `.picker-empty` by the Phase 4 polish). It closed
    `@layer components` early, so the committed stylesheet didn't build.
    The line was removed, and `test_theme.py` now checks the brace
    balance.
  - The signed-out test first missed its message because the apostrophe
    is HTML-escaped. The test now unescapes the body.
  - The test's `" ".join(split())` turned non-breaking spaces into
    ordinary ones, so the expected file sizes were corrected.
  - There's no Node, so the scripts were parse-checked with a throwaway
    `esprima` (`uv run --no-project --with esprima`). The JavaScript
    behaviour hasn't been run in a browser; the manual guide covers it.
  - "Sidebar menu" could have meant the drawer or the left side panel, so
    the agent asked before changing either. The flicker was the drawer,
    and the icons-and-labels request was the side panel.
  - The rewritten sidebar test's regex first failed: there's a newline
    between the icon cell and its `<svg>`, and a doubled backslash crept
    in through `sed`. Both were fixed in the test.
  - On review, browsers send textarea line breaks as CRLF, which the
    10,000 limit would count twice. The form now stores LF, and a test
    covers it.

## 2026-11-05 — Axcenity Toolbox: Phase 4 polish, card actions, tag filter and Remove

### Prompts

1. Currently I have textures setup to be viewable in images, however the
   texture itself seems to be slightly cutoff from the top and the bottom
   can you have it to where it shows the entire texture. When I click on a
   texture or add it to the library it retains the information popup menu,
   I would like for this to go away uness I click another button that
   allows me to see it in full detail, or I can just hover over it as
   normal and view it that way. Next the library button is a bit in the
   way I would like a button likely in the top right or left of the logo
   that can add it to the library. Then I would like another button where
   I can add it to a collection and it allows me to then add it to a
   collection of my choosing. Collections have not been fully implemented
   yet so a button with the ui for now should be good and updating the
   plan to complement these changes should suffice. Next I would like to
   be able to sort the library based on tags from all 3 api sources and
   have a way to remove items from the library, as well as in the library
   a way for me to add an item to a pack. After completing these changes
   please update PROMPTS.md according to source formatting and include any
   chats that are made hearafter as well.
2. Alright I beleive there may be some confusion regarding packs and
   collections. I really just want to keep it down to packs remove
   collections as all functionality will be focused around packs

### Summary

- **Outcome:** the polish was built as asked, outside the plan's phase
  order and recorded as "Phase 4 polish".
  - Texture thumbnails show whole.
  - The hover details go away after a click unless Details keeps them
    open.
  - Save, Add to collection and Details sit in each card's top-right
    corner.
  - The library has a cross-provider Tags filter, Remove, and Add to pack
    and Add to collection buttons.
  - Collections and Add to pack are the interface only, as asked for
    collections. Packs don't exist until Phase 7.
  - The plan gains Phase 7b (Collections), and the PRD gains stories
    87–92.
  - 524 tests pass (497 before). `ruff check` and `ruff format --check`
    are clean. A one-off `tailwind build` emits the new rules.
- **Changes:**
  - `catalog/templates/catalog/partials/result_card.html`: `data-kind` on
    the card, and the `.card-actions` corner (Save, Add to collection,
    Details) in place of the `.result-actions` row. The details list every
    tag.
  - `catalog/templates/catalog/partials/save_button.html`,
    `in_library.html`, `save_error.html`: Save, "In library" (a filled
    check, no logo mark) and Try again are corner squares. The error
    message wraps below them.
  - `catalog/templates/catalog/partials/details_button.html`,
    `picker_button.html`, `picker_dialog.html`, `remove_button.html` (new):
    the Details toggle, the Add to collection / Add to pack buttons, the
    UI-only picker `<dialog>`, and Remove (a POST with `hx-confirm`).
  - `catalog/templates/catalog/partials/library_card.html`: `data-kind`,
    the corner actions (Add to pack, Add to collection, Details, Remove), a
    details panel with the stored tags, and `.star-rating` in place of
    `.rating`.
  - `catalog/templates/catalog/library.html`: the Tags chip group with
    counts (or a hint when there are no tags yet), and both pickers.
    `library_results.html` sends the saved count out of band after a
    Remove. `discover.html` holds the collection picker for members.
  - `catalog/models.py`: `Tag.objects.in_library(user)` (the member's tags
    with `uses`, most used first) and `SavedAssetQuerySet.tagged(names)`
    (every name, one subquery each).
  - `catalog/library.py`: `LibraryParams.tags` (in `is_filtered` and the
    tidy URL), `tag` read through `normalize_tag()` (first 10, A–Z),
    `filter_library()` filtering on it and prefetching tags,
    `filter_groups(params, tags)` with a Tags group (top 24 plus chosen),
    and `FilterChip.count`.
  - `catalog/views.py`, `catalog/urls.py`: `RemoveFromLibraryView` at
    `catalog:remove` (`/library/<id>/remove/`). The library context is
    shared through `_library_context()`, and `_current_library_params()`
    reads the view from `HX-Current-URL`.
  - `styles/source.css`: square, `contain` texture frames; the corner
    actions, their tips and their error line; details on `:hover`,
    `:has(:focus-visible)` or `data-details="open"`, never `:focus-within`;
    the tag-chip count; the picker dialog; `.star-rating`; the
    reduced-motion rules.
  - `static/js/card-actions.js` (new, loaded in `templates/base.html`):
    the Details toggle (with Escape), opening a picker with the asset's
    title, and closing on a backdrop click.
  - `templates/partials/icon.html`: `check`, `info`, `collection`,
    `pack-add`, `trash`, `close`.
  - `tests/test_discover.py`, `tests/test_library_save.py`: the card
    regexes follow the new markup. Rewritten tests cover all tags in the
    details and "In library" as a corner check with no mark. New tests
    cover the details going after a click, the Details toggle, square
    textures and the corner actions.
  - `tests/test_library_filter.py`: tag filter tests: across providers,
    every tag needed, listed once, tidied values, never another member's,
    the URL, `in_library()` and the chips.
  - `tests/test_library_page.py`: the Tags chips, the card's corner
    actions, details and pickers, Remove (the asset stays, the same view,
    falling back a page, from another page, the last entry, without HTMX,
    POST only) and the star class.
  - `tests/test_access_control.py`: Remove's sign-in, 404 and CSRF rules,
    and tags never leaking another member's entries or tags.
  - `docs/ARCHITECTURE.md`, `docs/FRONTEND.md`, `docs/TESTING.md`: the
    remove URL, tags, the corner actions, the details behaviour, the
    pickers and the new tests.
  - `prd/axcenity-toolbox.md`: stories 87–92, the Collection model,
    dated notes under Discover, Library and branding, and a collections
    row in the access table.
  - `plans/axcenity-toolbox.md`: a ticked "Phase 4 polish" section,
    "already in place" notes in Phases 5, 6 and 7, and the new Phase 7b:
    Collections.
- **TDD:** not used. This was a user-requested polish rather than a plan
  phase run through `/implement`. Tests were written alongside each
  change, including the tag filter's owner rule and Remove's access rules.
- **Decisions:**
  - "Top right or left of the logo" was read as the card thumbnail's top
    right, because a sound's play button already holds the top left.
  - "In library" in the corner is a check without the logo mark, because
    the brand rule (story 76) keeps the logo off provider thumbnails.
  - Only textures get the square frame. Other kinds keep 4:3 cover.
  - Tags were built as a filter (an entry needs every chosen tag), not a
    sort order. The side panel shows the top 24 tags with counts.
  - Remove uses the browser's confirm until Phase 7's dialog that lists
    packs.
  - Library cards got the details panel and Add to collection too, to
    match Discover.
  - Collections went in as Phase 7b in `catalog`, private and website
    only. Adding an unsaved Discover result saves it first.
- **Deviations:** "a way to add an item to a pack" is the interface only.
  The button and picker are in place, but no Pack model exists until
  Phase 7, which wires them to `add_to_pack()`.
- **Follow-up (prompt 2):** collections were removed. Everything centres
  on packs.
  - Discover cards' Add to collection became **Add to pack**, and library
    cards lost their collection button. The corners are now Save / Add to
    pack / Details on Discover, and Add to pack / Details / Remove in the
    library.
  - `picker_button.html` and `picker_dialog.html` became `pack_button.html`
    and `pack_picker.html`. The `collection` icon and the `.picker-new`
    styles were deleted.
  - The plan's Phase 7b was deleted. Phase 7 now notes that its picker is
    already in place on both cards, and gains a criterion: adding a
    Discover result to a pack saves it to the library first.
  - In the PRD, story 92 is now Add to pack from Discover. The Collection
    model, the Collections section and its access row are gone.
  - FRONTEND.md and the tests follow. The tests now also check that no
    "collection" text is left on Discover or the library. 524 tests pass,
    and ruff is clean.
- **Sideways:**
  - The first scripted edit of `catalog/library.py` broke on nested
    quotes and wrote nothing. It was redone with exact edits.
  - Changing the card markup failed 27 tests whose regexes matched the old
    `<li class="result-card">` and `.result-actions`. The helpers were
    updated, and the six tests whose behaviour changed were rewritten.
  - One new CSS assertion came out convoluted and was simplified. A blanket
    "no `:focus-within`" check would have caught the search bars' own
    legitimate use, so it was narrowed to cards.
  - A headless-Firefox preview of the library showed the stars as grey
    blocks. DaisyUI's `.rating` component had been overriding them since
    Phase 3. The class was renamed `.star-rating`, with a test.

## 2026-11-05 — Axcenity Toolbox: Phase 4/13, Library browsing

### Prompts

1. The `/implement` skill, given `axcenity-toolbox phase 4`.
2. Looks good go ahead and move onto testing
3. Looks good move to next test
4. Looks good move to next
5. Looks good move on

### Summary

- **Outcome:** members can search, filter, sort and page through their
  library.
  - One shared `filter_library(user, params)` handles search (title,
    tags, notes), filters (type, provider, status, minimum rating), the
    four sorts and pages of 12. It only ever returns the caller's own
    entries.
  - The toolbar's search and sort, and the side panel's chips, switch on
    once the library has entries. A change swaps only `#library-results`
    and pushes a tidy URL. The same URL loaded directly, or reached with
    Back, renders the whole page in the same state.
  - An empty library links to Discover, and no matches offers Clear
    filters. Pages over one get a Previous / "Page N of M" / Next pager.
  - 497 tests pass (451 before the phase). `ruff check` and
    `ruff format --check` are clean. A one-off `tailwind build` emits the
    new chip rules.
- **Changes:**
  - `catalog/library.py`: `filter_library()`, `clean_library_params()`,
    `LibraryParams` (with `is_filtered` and the tidy `url()`),
    `LibraryPage` (with `url`, `previous_url` and `next_url`),
    `filter_groups()` for the side panel's chips, and `SORT_LABELS`.
  - `catalog/models.py`: `LIBRARY_SORTS`, and
    `SavedAssetQuerySet.search()` and `sorted_by()`.
  - `catalog/views.py`: `LibraryView` returns the results fragment, with
    `HX-Push-Url`, for the controls' own HTMX requests. Boosted and
    history-restore requests get the full page. A signed-out fragment
    request gets `HX-Redirect` to sign-in.
  - `catalog/templates/catalog/library.html`: the toolbar is now a GET
    form with the HTMX swap. The chips are checkbox and radio labels tied
    to it through `form="library-toolbar"`. The grid/list toggle is gone.
  - `catalog/templates/catalog/partials/library_results.html` (new): the
    count, the grid, the pager and both empty states.
  - `styles/source.css`: chips that are on are inverted, with a focus
    ring and gated hover. The toolbar fields get a focus edge, and there
    are pager styles. The view-toggle styles are removed.
  - `tests/test_library_filter.py` (new): `filter_library()` unit tests.
  - `tests/test_library_page.py`: the layout tests now cover disabled
    while empty, and new browsing tests cover the fragment, the full page,
    the pushed URL, the pager and the empty states.
  - `tests/test_access_control.py`: a visitor's library view and its
    fragment go to sign-in and back, and no parameter shows another
    member's entries.
  - `docs/ARCHITECTURE.md`, `docs/FRONTEND.md`, `docs/TESTING.md`: the
    browsing design, its parameters, the swap and the new test file.
  - `plans/axcenity-toolbox.md`: Phase 4 ticked.
- **TDD:** three behaviours, each red on an assertion before the code:
  1. Never another member's entries, whatever the parameters (the
     scaffold read every `SavedAsset`).
  2. The rating sort is high to low with unrated entries last and ties
     newest first (the scaffold ignored `sort`).
  3. Unknown sort, filter and page values fall back to the defaults (the
     simple filters returned nothing for `type=planet`).
- **Decisions:**
  - The URL parameters are `q`, `type`, `provider`, `status`,
    `min_rating`, `sort` (`newest`, `oldest`, `title`, `rating`) and
    `page`. The pushed URL leaves out defaults, so the whole library is
    `/library/`.
  - Type, provider and status chips allow several choices; minimum
    rating is one choice, Any by default.
  - Every search word must match the title, a tag or the notes. Words go
    through `normalize_tag()` before matching tags, and tags match through
    a subquery, so no entry is listed twice.
  - Title A–Z ignores case, and every sort ends on newest saved and then
    id.
  - A page past the end shows the last page.
  - History-restore requests get the full page, so Back works.
  - Clear filters is a boosted link, so the controls reset too.
  - The grid/list toggle was removed rather than building a list view.
  - The provider chip reads "Openverse Audio", the provider's `NAME`,
    like the shelf headers.
- **Deviations:** none. The brief, all three TDD tests and the plan's
  gaps were accepted as proposed.
- **Sideways:**
  - The scaffold's plain `params.getlist()` broke on the tests' plain
    dicts. A small `_values()` helper reads either a dict or a QueryDict.
  - `page=0` passed the digit check, and `Paginator.get_page(0)` served
    the last page. Page numbers now have to be 1 or more.
  - Three test mistakes were caught by their first runs and fixed in the
    tests:
    - a URL test whose titles didn't contain the searched word
    - a hand-worked minimum-rating list (Brick 05 is rated 1)
    - a fragment check that didn't allow for the blank lines template
      comments leave

## 2026-11-04 — Axcenity Toolbox: Phase 3/13, Save to library

### Prompts

1. The `/implement` skill, given `axcenity-toolbox phase 3`.
2. Looks good go ahead and continue
3. Looks good move to next
4. Looks good move to next
5. Looks good move on
6. Looks good move on
7. Looks good move to next

### Summary

- **Outcome:** members can save Discover results to a private library.
  - The first save of an asset by anyone fetches its full details,
    including every download variant, into a shared Asset. Later saves
    reuse it.
  - The button swaps for an "In library" badge with the logo mark, and
    results the member already has render that way.
  - A provider failure shows its friendly message in the button's place,
    with Try again.
  - Signed-out visitors are sent to sign in and back to their search.
  - `/library/` shows the member's own cards: thumbnail, type, title,
    status and rating. The status bar shows their saved count, updated out
    of band after each save.
  - 451 tests pass (370 before the phase).
    `ruff check` and `ruff format --check` are clean. A one-off
    `tailwind build` emits every new class.
- **Changes:**
  - `providers/records.py`: `Variant` and `VariantFile` (with
    `total_size` and `as_dict()`), `AssetRecord.variants`, and the
    `byte_size()` and `file_name()` helpers.
  - `providers/ambientcg.py`, `polyhaven.py`, `openverse.py`:
    `fetch_record()` in each Toolbox section.
    - ambientCG: one variant per download zip.
    - Poly Haven: `_cached_info()` plus `/files`, keeping every file URL.
      Loose maps are grouped by resolution and format; each bundle is its
      own variant with its included files.
    - Openverse: the main file, then one variant per other file type.
    - An ID that isn't a plain slug is refused before any request. The
      console's functions are untouched.
  - `providers/__init__.py`: documents `fetch_record()`.
  - `catalog/tags.py` (new): `normalize_tag()` and `MAX_TAG_LENGTH`.
  - `catalog/models.py` and `catalog/migrations/0001_initial.py` (new):
    - `Tag` and `Tag.objects.from_names()`.
    - `Asset` and `Asset.objects.from_record()`, unique on (provider,
      external_id).
    - `SavedAsset`: the `Status` choices, a 1–5 rating check, unique on
      (user, asset), and a `PROTECT` link to Asset. Its queryset has
      `for_user()` and `saved_external_ids()`, and the model has `stars`.
  - `catalog/library.py` (new service module): `get_or_fetch_asset()`,
    `save_to_library()` and `UnknownProviderError`.
  - `catalog/views.py`, `catalog/urls.py`:
    - `SaveAssetView` at `catalog:save`: POST only, members only, a 400
      before any provider call, and sign-in redirects back to Discover.
    - The shelf view passes the member's saved IDs.
    - `LibraryView` lists the member's entries.
  - `catalog/discover.py`: `Shelf.page_url`.
  - `config/context_processors.py`: `saved_count`, for members only.
  - `catalog/admin.py`: admin for the three models.
  - Templates:
    - new `save_button.html`, `in_library.html`, `save_error.html`,
      `library_card.html` and `templates/partials/saved_count.html`
    - `result_card.html`: the Save row
    - `library.html`: the grid
    - `base.html`: the count
    - `icon.html`: `plus` and `star`
  - `styles/source.css`: the card as a flex column with a Save row, the
    details panel stopping above it, the Save, badge and error styles, the
    library card's type, status chip and stars, and reduced motion.
  - Tests:
    - new `test_tags.py`, `test_library_save.py` and
      `test_provider_fetch.py`
    - additions to `test_library_page.py`, `test_access_control.py` and
      `test_shell.py` (type colour on library cards)
    - the `make_asset` fixture in `conftest.py`
    - `test_provider_records.py`'s field helper now expects search results
      to carry no variants
  - `docs/ARCHITECTURE.md`, `docs/FRONTEND.md`, `docs/TESTING.md`: saving,
    the models, the Save slot, library cards and the new test files.
  - `plans/axcenity-toolbox.md`: every Phase 3 box ticked.
- **TDD:**
  1. `normalize_tag()` follows each PRD rule (one parametrized test, 14
     cases). Red on 11 cases against a pass-through stub, then green.
  2. `save_to_library()`: the first save fetches once and stores one
     Asset with normalized tags, a second member reuses it without
     fetching, and a repeat save adds no second entry. Red (no fetch),
     then green.
  3. A `ProviderError` saves nothing and keeps its message. Green on its
     first run, because behaviour 2's code fetches before it writes. A
     temporary mutant that reserved the Asset row before fetching made it
     fail on `assert not Asset.objects.exists()`, and the mutant was
     reverted.
- **Decisions:**
  - Variant labels read "2K JPG", "1K glTF" or "MP3", so Phase 7's
    default-variant rule can match one form. An unknown size is stored as
    `null`.
  - The plural "s" comes off the last word only. "Number-only" means
    digits and spaces. `canvas` becomes `canva`, per the PRD's literal
    rule.
  - The save URL replies with fragments only, because its button lives in
    HTMX-loaded shelves.
  - A visitor's Save is a sign-in link, with `next` set to the shelf's
    Discover search. A signed-out POST goes back to the page in
    `HX-Current-URL`, never to the POST-only URL.
  - The Save row sits at the card's foot, so the logo mark never lands on
    a thumbnail and the hover details never cover the button.
  - Library cards show type colour on the type icon and the fallback icon
    only. `test_shell.py` was widened to allow exactly those.
  - The kind labels are singular ("Texture"), unlike the plural tile
    labels.
  - `preview_url` isn't stored on Asset yet. It's noted for Phase 5's
    drawer.
- **Deviations:** none. The brief and the three behaviours were approved
  as proposed.
- **Sideways:**
  - Twice, a long Git Bash heredoc failed to parse ("unexpected EOF"), so
    nothing was written. The files were written with the Write tool and
    small scratch scripts instead.
  - A test caught `file_name()` naming ambientCG's `/get?x=1` download
    "get". Now a path segment only counts when it has an extension.
  - `KIND_CHOICES` first reused the plural tile labels. The labels were
    made singular and the uncommitted migration was regenerated.
  - The existing "every field filled" helper failed on the new `variants`
    field, and was taught that search results carry none.
  - A muddled shell-test assertion, which would have matched `x-texture`,
    was replaced with a chrome check before it ran.
  - A manual live check of `fetch_record()` against all three providers
    (read-only GETs, outside the test suite) showed Openverse's
    alternative WAV has no file name in its URL. Such files are now named
    `<id>.<type>`, and the test fixture was made realistic.

## 2026-11-04 — Axcenity Toolbox: Phase 2b polish (sound previews, Load more, card details, random picks)

### Prompts

1. (With a screenshot of a Poly Haven "Moon 03" card whose author line ran
   past the card.) Ok thre are a few things that I want to improve upon
   firstly the audio/sound section. I want to make this to where I can
   actually play the audio clip in the website rather than it simply
   redirecting me to the website where it was sourced from. Next As of now
   I only have 12 searches being loaded at a time which is fine, however I
   would like to add a load additional option that will progresively load
   another 12 searches when clicked. The author test on some of these
   textures loads outside of the box make this an elipsis and allow users
   to hover over a specifc texture to get more information. Next I would
   lik for you to include some random searches in the discover section
   that way it gives something visual at all times rather than just an
   empty search.
2. Go ahead and include these other coverstations in PROMPTS.md

### Summary

- **Outcome:** four Discover improvements, built on top of the uncommitted
  Phase 2b work.
  - Sound results play their preview in the page.
  - A full shelf ends with "Load 12 more", up to 240 results.
  - Long author lists end in an ellipsis inside the card. Hover or focus
    shows the full title, author, license, source and tags.
  - With no query, Discover searches a random featured term for the type,
    with Shuffle.
  - 370 tests pass (339 before), and `ruff check` and
    `ruff format --check` are clean.
  - Checked in headless Edge against the live providers:
    - The sound shelf showed play buttons, an ellipsis on a long author
      and Load more.
    - "moon" on textures showed the ellipsis working, after a fix (see
      Sideways), and a details panel forced open in a scratch page.
    - An empty HDRI search showed "HDRIs for “night”" with both shelves
      filled.
  - Audio playback and the Load more click weren't exercised headless;
    they're in the browser test steps.
- **Changes:**
  - `providers/records.py`: `AssetRecord.preview_url` (default blank).
  - `providers/openverse.py`: `preview_url` from the audio `url`; `page`
    paging, and `MAX_DEPTH` (240), past which it returns `[]` without a
    request.
  - `providers/ambientcg.py`: `page` paging through `offset`.
  - `providers/polyhaven.py`: page N asks `/search` for N × 12 hits, keeps
    the last 12 and fetches `/info` only for those. Later pages stop at
    `keywordMatches`.
  - `catalog/discover.py`:
    - `PAGE_SIZE`, `MAX_PAGE`, `FEATURED_QUERIES`, `clean_page()`,
      `featured_query()` and `shuffle_url()`.
    - `Shelf.page`, `has_more`, `next_url`, `shown_count` and the slot ids.
    - The page goes into `shelf_url()`, `search_cache_key()` and
      `load_shelf()`.
  - `catalog/views.py`:
    - `DiscoverView` shows a random pick when there's no query.
    - `DiscoverShelfView` validates `page` (400) before the HTMX check, and
      renders `shelf_more.html` for later pages.
  - `catalog/templates/catalog/partials/`:
    - `shelf.html`: the grid id, the count partial and Load more.
    - New: `load_more.html` (the button, the end note, or an alert with
      Retry), `shelf_more.html` (the reply: the slot, cards appended with
      `hx-swap-oob="beforeend:…"`, the count and the status) and
      `shelf_count.html`.
  - `result_card.html`: an `<li class="result-card">` with a stretched
    title link, a `.result-author` ellipsis, the `.result-details` panel,
    and a play button plus progress line for sounds.
  - `catalog/templates/catalog/discover.html`: the `#featured-pick` row with
    Shuffle, which replaces the "Search to fill the shelves." empty state.
  - `static/js/sound-preview.js` (new, loaded in `base.html`): delegated
    playback, one preview at a time. It stops on swap and disables its
    button on error.
  - `templates/partials/icon.html`: play and pause icons.
  - `styles/source.css`:
    - the stretched link, `.result-body`'s `minmax(0, 1fr)` column and the
      ellipsis
    - the details panel, the play button and progress line, and Load more
    - reduced-motion rules for the new transitions
  - Tests:
    - `tests/test_provider_records.py`: paging for each provider, and a
      sound-only `preview_url`.
    - `tests/test_discover.py`:
      - Load more: the first page, the next page, the last page, an empty
        page, a failed page, each page cached separately, page 20, and bad
        pages refused for HTMX and direct requests alike.
      - Sound buttons and the script.
      - Hover details and the ellipsis.
      - The random pick, Shuffle and "no pick with a query".
      - The card helpers follow the new markup.
    - Every test fake gained `page=1`.
  - `docs/ARCHITECTURE.md`, `docs/FRONTEND.md`, `docs/TESTING.md`: the
    shelf URL's `page` and its check order, paging per provider, sound
    previews, result cards, Load more and the random pick.
  - `prd/axcenity-toolbox.md`: Discover's bullets record the four changes.
    "Load more" leaves the Tier 3 list, and "Paging inside Discover
    shelves" leaves Out of Scope.
  - `plans/axcenity-toolbox.md`: a ticked "Phase 2b polish" section under
    Phase 2b.
- **TDD:** none. This was a direct request rather than `/implement`. Each
  behaviour got ordinary tests after it was built.
- **Decisions:**
  - Previews stream from the provider's URL with `new Audio()`, never
    downloaded or proxied (the PRD's rule). Only Openverse sounds have one.
  - The play button sits at the thumbnail's top left, above a title link
    stretched over the card, so the card still opens the source and the
    button plays rather than navigates.
  - Load more appends cards out of band and replaces only its own slot, so
    a failed page keeps the cards already shown. It stops at page 20,
    Openverse's anonymous limit.
  - The button shows only after a full page. An exact multiple of 12 costs
    one click that ends with "That's everything".
  - Poly Haven's later pages stop at the keyword matches, so Load more
    never shows unrelated semantic guesses.
  - Each random pick was checked live to fill both of its type's shelves.
    ambientCG's 34 models are all food, so the model picks are apple,
    bread, fruit and food.
  - The pick isn't put in the command bar, and Shuffle never repeats it.
  - The hover panel is `aria-hidden`, because the card already holds the
    same text. It also opens on keyboard focus.
- **Deviations:**
  - "Load more" was a PRD Tier 3 stretch item, and shelf paging was out of
    scope. They were built because the user asked, and the PRD and plan
    were updated to match.
  - This round wasn't logged until the user asked.
- **Sideways:**
  - The first headless screenshot showed long author lists still running
    past the card. A grid column of `auto` grows to fit its content, so
    the ellipsis never applied. `.result-body` now uses
    `minmax(0, 1fr)`, and the test checks for it. The earlier test checked
    only the ellipsis CSS, so it passed while the page was wrong.
  - `featured_query()` first took `random.choice` as a default argument,
    so the test's patch didn't apply. It now looks the function up at
    call time.
  - Two Bash heredocs failed to parse, so the tests and the doc edits were
    written to scratch files and applied from there.
  - The new card markup broke the old card helpers and the
    "no query, no shelves" test. They were updated to the new structure
    and behaviour.

## 2026-11-04 — Axcenity Toolbox: Phase 2b/13, Caching, provider credits, fallback icons, status bar and failure tests

### Prompts

1. The `/implement` skill, given `axcenity-toolbox phase 2b`.
2. Everything looks good go ahead and start the tests
3. Looks good move to next
4. Looks good move to next
5. Looks good move to next

### Summary

- **Outcome:** Discover now caches, credits its providers, never shows a
  broken thumbnail, and reports each provider's status in the status bar.
  - Successful searches are cached for 1 h per (provider, kind,
    normalized query). Poly Haven `/info` is cached for 12 h. Failures are
    never cached.
  - Every shelf ends with its provider's credit line.
  - A missing or broken thumbnail shows the type's icon.
  - The status bar shows OK, error or unknown for each provider, updated
    out of band as each shelf loads.
  - Story 83's failure suite covers all three levels.
  - 339 tests pass (283 before), and `ruff check` and
    `ruff format --check` are clean. A one-off `tailwind build` emits every
    new class.
- **Changes:**
  - `providers/cache.py` (new): `use_cache()` and `remember()`, an optional
    cache with no Django import. A lookup that raises is never stored.
  - `providers/polyhaven.py`: `INFO_CACHE_SECONDS` (12 h) and
    `_cached_info()`, which `search_records()` now uses. The console's
    `search()`, `get_details()` and `_info()` are untouched.
  - `providers/ambientcg.py`, `polyhaven.py`, `openverse.py`: `CREDIT` and
    `HOME_URL` in each Toolbox section. `providers/__init__.py` documents
    them and the cache hook.
  - `catalog/apps.py`: `ready()` installs Django's cache into
    `providers.cache`.
  - `catalog/discover.py`:
    - `search_cache_key()` (the cleaned, case-folded and hashed query) and
      the 1 h cache in `load_shelf()`.
    - `ProviderStatus`, `record_status()`, `provider_status()` and
      `provider_statuses()`.
    - `Shelf.credit`, `credit_url`, `tile` and `status`.
  - `config/context_processors.py`: the status bar gets
    `provider_statuses()`.
  - `templates/partials/provider_status.html` (new) and
    `templates/base.html`: one status-bar item per provider, also used for
    the out-of-band swap.
  - `catalog/templates/catalog/partials/shelf.html`: the credit line, and
    the status item out of band on a loaded shelf.
  - `catalog/templates/catalog/partials/result_card.html`: the type icon
    under the thumbnail, and `data-thumb-fallback` on the image.
  - `static/js/shell.js`: a capture-phase `error` listener removes a
    broken thumbnail, which uncovers the icon.
  - `styles/source.css`: the status dot and item, the shelf credit, and
    the thumbnail stacked over its fallback icon.
  - `tests/test_provider_failures.py` (new): a timeout, a connection error
    and a 429 for each provider, Openverse's 500 with HTML, Poly Haven's
    404 on `/search` and on `/info`, `keywordMatches == 0`, and one
    distinct message per failure.
  - `tests/test_discover.py`:
    - The three TDD tests.
    - The mixed-shelves test, parametrized over six failures in both
      directions.
    - App-level checks that each failure reaches the alert unchanged and
      stays out of the cache, plus the 1 h timeout.
    - Credits in every shelf state.
    - Fallback icons for all four types, and the out-of-band status.
    - A cached shelf leaving the status alone.
  - `tests/test_provider_records.py`: the `/info` cache (one fetch, 12 h,
    failures not stored), no caching without an installed cache, and the
    console `search()` never caching.
  - `tests/test_access_control.py`: a visitor's status bar holds provider
    status only. `tests/test_shell.py`: the placeholder test was renamed.
  - `docs/ARCHITECTURE.md`, `docs/FRONTEND.md`, `docs/TESTING.md`: caching,
    the cache hook, status, credits, fallback icons and the new test file.
  - `plans/axcenity-toolbox.md`: every 2b box ticked.
- **TDD:**
  1. A repeated search, including one differing only in case or
     whitespace, calls the provider once. Red, then green.
  2. A failure is never cached, and a success on Retry is shown and
     cached. Already green when first run, because behaviour 1's code
     stores only on success. A temporary mutant, which kept the alert but
     cached the failure as empty, made it fail on its Retry assertion, and
     the mutant was reverted.
  3. Shelf outcomes set the status bar to ok or error, and unused
     providers read unknown. Red, then green.
- **Decisions:**
  - On a cache miss, the provider gets the first search's cleaned query
    with its case kept. Only matching ignores case.
  - Provider status lasts 1 h and is set only when a provider is actually
    contacted, never by a cache hit.
  - The cache hook keeps `providers` free of Django, so the console script
    never caches.
  - The fallback icon uses its type colour, because it shows the asset's
    type.
  - The status bar stays monochrome: a solid dot, an alert icon, or a
    muted dot.
  - Poly Haven's 404 is tested on both `/search` and `/info`.
- **Deviations:** none. The brief and the three behaviours were approved
  as proposed.
  - **Open question:** `get_json()`'s 429 message cites Openverse's quota
    even for ambientCG and Poly Haven. It's left unchanged here, because
    `get_json()` also serves the console script.
  - **Phase 3 note:** `fetch_record()` must use
    `polyhaven._cached_info()`.
- **Sideways:**
  - The first cache key contained spaces, and Django warned that memcached
    would reject it, so the query is now hashed.
  - The credit line broke the 2a test's alert regex, which was anchored on
    `</section>`. It was repaired mechanically to anchor on the credit
    line.
  - A Python-written test edit turned `\n` into real newlines inside a
    string literal. The broken lines were rewritten with the Edit tool.
  - A junk line was left in the new failure-test file and removed before
    the run.
  - The visitor status-bar test first split inside the `<footer>` tag, and
    was fixed to start after it.

## 2026-10-31 — Axcenity Toolbox: Phase 2a/13, Discover with provider shelves and error handling

### Prompts

1. The `/implement` skill, given `axcenity-toolbox phase 2`.
2. This looks good but lets change some things:
   Enforce 12-result limit before fetching poly haven details as poly haven
   makes one / info request per search result, limit hits before those
   request rather than fetching everything and sorting through it avoiding
   the uneccesary API call when possible.
   Define shelf request validation order such as kind provider compatabiiy
   and nonblank before checking whether it is an HTMX request this makes
   sure that it is sending back a 404 or 400 rather than a redirect
   Make the provider errors safe to display in 2a since the shelf siplays
   providererror messages directly do not expose raw exception text or
   respons details to users. Keep diagnostic details in server -side
   logging. Move this section into 2a rather than 2b
3. looks good just make sure that the test verifies the absence of type t
   and category parameters for openverse not just eh absence of incorrect
   values move to next.
4. Looks good move on
5. ensure the Retry button is inside the failed shelf's alert and that the
   error message is HTML-escaped when rendered.other than that move on

### Summary

- **Outcome:** Discover works end to end for all four types.
  - The page shows four type tiles and a command bar. `/` focuses the bar,
    and the home search's `q` lands in it.
  - Each matching provider gets a shelf that loads through its own HTMX
    request.
  - A shelf shows up to 12 results (thumbnail, title, author, license), a
    "no matches" message, or an alert with Retry.
  - 283 tests pass (227 before), and `ruff check` and
    `ruff format --check` are clean.
  - Checked live through headless Edge and curl:
    - "brick" on textures filled both shelves with 12 results.
    - Openverse returned 12 rain sounds.
    - A mismatched shelf URL gave 404, and a direct visit redirected to
      its Discover page.
- **Changes:**
  - `providers/records.py` (new): the shared `AssetRecord`, `KINDS`, and
    parsing helpers (`items_in`, `text`, `tag_names`) that turn a bad
    shape into a safe `ProviderError` and skip bad items.
  - `providers/ambientcg.py`, `polyhaven.py`, `openverse.py`: `KEY`,
    `KIND_FILTERS` (the PRD mapping) and `search_records()`, added below
    the untouched console code.
    - Poly Haven cuts its hits to the limit before any `/info` request.
  - `providers/__init__.py`: `PROVIDERS_BY_KEY`, `providers_for_kind()`,
    and a `NullHandler` so the console script stays quiet.
  - `providers/http.py`: `get_json()` messages never carry exception text
    or response content. The catch-all no longer includes `{exc}`, and
    `Retry-After` is echoed only when it's a number. Every failure logs
    its details to the `providers` logger.
  - `config/settings.py`: `LOGGING` sends the `providers` logger to the
    console.
  - `catalog/discover.py` (new): `KindTile`, `Shelf`, `clean_query()`,
    `clean_kind()`, `shelf_url()`, `discover_url()`, `shelf_provider()`,
    `pending_shelves()` and `load_shelf()`.
  - `catalog/views.py`, `catalog/urls.py`:
    - `DiscoverView` reads `type` and `q`.
    - `DiscoverShelfView` is new, at `catalog:discover_shelf`
      (`/discover/<kind>/<provider>/?q=`). It validates the kind, the
      provider, the match between them and the query before it checks for
      HTMX.
  - `catalog/templates/catalog/discover.html`, `partials/shelf.html`,
    `partials/result_card.html`: the page, the four shelf states and the
    result card.
  - `templates/partials/icon.html`: texture, HDRI, model and sound icons.
  - `static/js/shell.js`: the `/` shortcut, skipped while the cursor is in
    a text field.
  - `styles/source.css`: the command bar, type tiles, shelves, result
    cards, skeletons, and the toned-down `.shelf-alert`. Reduced motion
    stops the pulse and the tile bar.
  - `tests/test_provider_records.py` and `tests/test_discover.py` (new).
    `tests/test_access_control.py` gains signed-out Discover and shelf
    access.
  - `tests/test_shell.py`: "type colour nowhere yet" is now two tests: no
    type colour in the chrome on any page, and in content only on
    Discover's tiles.
  - `docs/ARCHITECTURE.md`, `docs/FRONTEND.md`, `docs/TESTING.md`: the
    shelf URL and its check order, the provider-error rules, the Discover
    layout, and the new test files.
  - `plans/axcenity-toolbox.md`: three 2a criteria added at the user's
    request, and every 2a box ticked.
- **TDD** (three behaviours, each red then green):
  1. Each kind uses exactly the PRD's providers, and each provider sends
     the PRD's filter. Openverse sends no `type`, `t` or `category`
     parameter.
  2. A bad shelf URL is refused before any provider is called: 404 for an
     unknown kind, an unknown provider or a mismatch, and 400 for a blank
     query, for HTMX and plain requests alike.
  3. With one provider failing and the other working, the failed shelf
     holds the escaped message and a Retry button aimed at its own URL,
     inside its alert. The working shelf shows its results, and fetching
     in either order gives the same fragments.
- **Decisions:**
  - "Phase 2" was read as 2a only; 2b stays separate.
  - One kind vocabulary (`texture`, `hdri`, `model`, `sound`) in URLs and
    code.
  - The mapping lives in `providers/` (`KIND_FILTERS`).
  - ambientCG's author is "ambientCG". CC0 attributions are composed.
  - An unknown `type` on the page falls back to textures. With no `q`,
    the page shows a hint and fires no shelves.
  - A valid shelf opened directly redirects to its Discover page.
  - Queries are trimmed, whitespace is collapsed, and they're cut to 100
    characters.
  - A card opens the provider's page in a new tab. There's no type badge
    on cards: the PRD asks for thumbnail, title, author and license, and
    the tile already shows the type.
- **Deviations:** the user changed the brief in three ways, and each
  became a 2a acceptance criterion:
  - Cut Poly Haven's hits before `/info`.
  - Validate the shelf URL before the HTMX check.
  - Make `ProviderError` messages safe now, with details logged
    server-side, rather than in 2b.

  They also had test 1 check each Openverse parameter name explicitly,
  and test 3 prove that the message is escaped and that Retry sits inside
  the alert.
  - **One behaviour change for the console script:** an unexpected
    request error now prints the safe message instead of the raw
    exception text. Its regression tests are unchanged and pass.
- **Sideways:**
  - A first draft of `load_shelf()` wrapped `dataclasses.replace` in a
    pointless helper; it was caught on review and removed.
  - Two Bash heredocs that appended tests failed on shell quoting, so the
    tests were written with the file tools instead.
  - The first headless capture of the sounds page caught Openverse
    mid-load, so only the skeleton showed. Fetching the shelf with curl
    confirmed it returns 12 results.
  - `docs/code-walkthrough.md`'s line links into `providers/http.py` are
    now out of date. The doc says to trust function names over line
    numbers, so it was left alone.

## 2026-10-31 — Axcenity Toolbox: Phase 1 shell polish, round 6 (system light mode, page transitions)

### Prompts

1. Ok now can you add a light mode that adjusts to the systems settings and
   some transitions for going between menus rahter than just having it look
   instantaneous.

### Summary

- **Outcome:** the site follows the system's light or dark setting, and
  moving between pages animates. 223 tests pass (183 before), and
  `ruff check` and `ruff format --check` are clean. Headless Edge
  captured Home, Library, sign-in, three hover states and the transition
  frames with the colour scheme emulated as light, then repeated the hover
  states and Home in dark to check for regressions.
- **Light mode:**
  - **Palette:** the values come from the engine's own light palette
    (`crates/editor/src/theme.rs`, `Palette::new(dark = false)`). That's
    the same source as the dark one, and the engine already offers a
    "System" theme choice.
  - **One theme:** an unlayered `@media (prefers-color-scheme: light)`
    block sets the same tokens and DaisyUI roles to their light values, so
    it's still the single `axcenity` theme. The light set includes the
    engine's on-light type and status colours. Primary buttons turn
    near-black with white text.
  - **Contrast tokens:** new `ink`, `on-ink` and `shade` tokens replace
    every fixed white or black in the chrome. These cover the hover
    inversion, current-page marks, tooltips, focus rings, button hovers,
    watermarks, the hero mark and the signature shadow. In light mode,
    hover inverts to near-black with white content.
  - **Dots and logo:** the dot grid reads `--grid-dot` (ink at 4 %, 7 % in
    light). The title-bar wordmark image is inverted through
    `--logo-filter`.
  - **Glow:** the drop-glow blobs use `multiply` at 40 % in light, because
    `screen` washed out on white.
  - **Settings page:** it now reads "Axcenity, following your system (dark
    or light)".
- **Page transitions:**
  - **How:** `globalViewTransitions` in the htmx config runs each boosted
    swap through the View Transitions API.
  - **Content:** fades up and out over 0.16 s, then the new page rises in
    over 0.34 s. The rest of the page crossfades over 0.18 s.
  - **Current-page marks:** in the activity bar, side panel and title
    bar, each shares a `view-transition-name`, so the mark glides from the
    old item to the new one.
  - **Fallbacks:** browsers without View Transitions just swap, and
    reduced motion turns it off.
  - **Captured:** in the frames, the title-bar underline slides from HOME
    to LIBRARY while the content crossfades.
- **Files:** `styles/source.css`, `templates/base.html`,
  `templates/partials/empty_state.html`,
  `accounts/templates/accounts/settings.html`, `tests/test_shell.py`,
  `tests/test_theme.py`, `tests/test_auth_pages.py`, `docs/FRONTEND.md`
  (new "Page transitions" section, light mode and contrast tokens),
  `CLAUDE.md` (the colour rule), `plans/axcenity-toolbox.md` (an "Already
  in place" note in Phase 13).
- **Tests:** four tests that pinned white or black were updated to the
  contrast tokens. New tests cover:
  - the light block matching the engine's palette, type and status
    colours, the flipped primary, and monochrome chrome
  - the logo inversion and multiply glow
  - no raw white or black in the chrome
  - ink watermarks
  - the Settings label
  - the view-transition config, names, glide and reduced motion
  - each transition name being used at most once per page
- **Deviations:**
  - Light mode isn't in the PRD, and the "only the axcenity palette" rule
    was read to include the engine's own light values. CLAUDE.md now says
    the palette has a dark and a light set.
  - The transitions pull part of Phase 13 ("View Transitions on HTMX
    swaps") forward at the user's request. The plan notes it, so Phase 13
    only extends them to fragment swaps.
- **Sideways:**
  - The CSS update script aborted on a step whose line the earlier blanket
    hover-inversion replacement had already changed. It wrote nothing, and
    was fixed and rerun.
  - A test session for `test_user` was created in the local dev database
    for signed-in captures and deleted afterwards.

## 2026-10-30 — Axcenity Toolbox: Phase 1 shell polish, round 5 (boosted navigation, sign-in as focal point)

### Prompts

1. Ok for the sign in menu I would like to focal point to be the sign in
   menu remove the watermark make the sign in menu a bit bigger and make
   sure that the watermark is the same subtle design as the other
   watermarks accross the other pages. I also amd still getting the weird
   page glitch when I click a page the white bar shows up breifly to the
   left of the button that is pressed.
2. (Answer to the agent's question on the watermark, which the request
   both removed and restyled) Remove footer watermark (Recommended): drop
   it from sign-in and sign-up entirely, and match the other working
   pages' background.
3. Ok it is in the top bar not the sidebar
4. This is the issue I get [screenshot of the Home page's top bar, HOME
   current with its underline, just left of TOOLBOX]
5. Ok I know what the issue is it is reloading the page rather than using
   the htmx to upadte and not completely refresh the page

### Summary

- **Outcome:** navigation no longer reloads the page, and sign-in is the
  page's focal point. 183 tests pass (174 before), and `ruff check` and
  `ruff format --check` are clean. A DevTools-driven browser check showed
  the document is never reloaded: a marker set on `window` survived each
  of these:
  - a TOOLBOX click
  - opening sign-in
  - a boosted sign-in, after which the CSRF header matched the rotated
    token
  - the panel toggle after swaps
  - sign-out
  - Back

  A TOOLBOX click now shows just two frames, before and after.
- **The glitch, in order:**
  - **Wrong first guess (sidebar):** frames showed the current-page bar
    left of an activity-bar icon vanishing once hover turned the icon
    white. The user said the glitch is in the top bar, so nothing was
    changed there.
  - **Fonts:** with the font files held back, the first paint showed
    HOME's fill and white underline with no text, just left of TOOLBOX.
    That's the reported bar, and it matches the user's screenshot.
    - `.ttf` was served as `application/octet-stream`, because Windows'
      mimetypes doesn't know it. `config/settings.py` now registers
      `font/ttf`.
    - A first-load font gate (inline `<head>` script plus CSS) hides the
      title-bar chips until JetBrains Mono is ready, capped at 3 s. In
      the worst-case test it still let through one stray frame.
  - **Real fix:** the user pointed to the root cause, a full page reload
    on every click. `<body hx-boost="true">` now swaps each page in
    without reloading the document, so fonts, CSS and scripts stay
    loaded. What that took:
    - The CSRF header moved to a new `#app` wrapper that swaps. `<body>`
      survives swaps, and Django rotates the token at sign-in.
    - An htmx-config meta: no history snapshots, and error pages swap in.
    - `shell.js` and `password-toggle.js` rewritten with document-level
      delegation. Both load globally, and the per-page scripts block is
      gone.
    - The hover gate re-arms after each swap.
    - The title-bar logo is `hx-preserve` with `width`/`height`. A
      rebuilt image blanked for a frame and slid the chips left.
- **Sign-in and sign-up:**
  - The footer watermark is removed, through a new `{% block watermark %}`
    emptied in `auth_base.html`.
  - The `auth` surface and its corner glow are deleted. Both pages use
    the same `work` background as the other working pages.
  - The card is bigger: `max-w-6xl` card, `max-w-md` form column, a
    2.75 rem headline, a 15 px lead, 48 px inputs and a 48 px submit.
- **Files:** `templates/base.html`, `static/js/shell.js`,
  `static/js/password-toggle.js`, `styles/source.css`,
  `config/settings.py`, `templates/registration/auth_base.html`,
  `templates/registration/login.html`,
  `accounts/templates/accounts/signup.html`, `tests/test_shell.py`,
  `tests/test_auth_pages.py`, `docs/FRONTEND.md` (HTMX section rewritten),
  `docs/TESTING.md`, `plans/axcenity-toolbox.md`. The plan's architecture
  note now says fragment views must check
  `request.htmx and not request.htmx.boosted`.
- **Tests:** the heading, submit, script-loading and auth-background tests
  were rewritten for the new layout. New tests cover:
  - `hx-boost` and the htmx config
  - the CSRF header on `#app`, not `<body>`
  - boosted requests getting full pages
  - a boosted sign-in redirecting
  - the preserved, sized logo
  - delegation and re-arming in `shell.js`, and delegation in the toggle
    script
  - `.ttf` served as `font/ttf`
  - the font gate
  - the bigger card with no watermark
  - auth pages on the work surface
- **Deviations:**
  - The watermark request both removed it and asked for it to match the
    other pages. The agent asked, and the user picked "remove it, and
    match the working pages' background".
  - The agent's font fixes were partial. The user identified full page
    reloads as the root cause, and boosted navigation replaced them as
    the real fix. The font gate stays for first loads.
- **Sideways:**
  - Several screencast captures came back empty or at shifting sizes, and
    an in-page timing logger ran before `<html>` existed and logged
    nothing. The scripts were fixed or dropped.
  - Editing `config/settings.py` triggered an auto-reload, and the user's
    port 8000 server stopped answering for a while. It came back on its
    own.
  - A `--noreload` test server on port 8001 kept serving cached templates,
    so boosting looked broken. Stopping its process was blocked, so
    testing moved to port 8002. All three test servers were stopped at
    the end through their background tasks.
  - A test session for `test_user` was created in the local dev database
    for signed-in captures and deleted afterwards. The boosted check also
    signed `test_user` in and out with the password recorded in the
    README.

## 2026-10-30 — Axcenity Toolbox: Phase 1 shell polish, round 4 (top-bar glitch, sign-in and sign-up redesign)

### Prompts

1. Ok there seems to be this weird glitch when navigating through menus it
   will breifly pop up with something different in the top-bar menu and
   almost look glitched out. Next we need to improve the login menu.
   Please append chat messages to PROMPTS.md according to source
   formatting.
   Align the form and branding panel vertically.
   Make both columns approximately the same height.
   Give the branding panel a subtle gradient or radial glow instead of a
   completely flat black background.
   Add a subtle border to the overall authentication container.
   Keep the form itself visually simple.
   A password visibility toggle.
   A Forgot password? link (when password recovery is implemented).
   A slightly more prominent form heading.
   More breathing room between the password field and submit button.
   A subtle focus ring on active inputs.
   Clear inline validation and authentication error messages.
   [pasted] Remove redundant navigation
   There are currently two sign-in indicators:
   - The active SIGN IN breadcrumb/tab at the top.
   - The SIGN IN action on the right.
   [end of paste]
   Since the user is already on the sign-in page, the right-side sign-in
   action is redundant.
   Change the top-right navigation to:
   - Sign up button.
   - Optionally, a Home link.
   Keep the active SIGN IN indicator in the main navigation.
   The logo looks good, but the panel has a lot of unused space.
   introduce a small supporting message below it, something like:
   Your assets. Your projects. Your Axcenity.
   Keep your favorite resources organized and ready for your next project.
   This reinforces what the Toolbox actually does without making the login
   page feel like a marketing landing page.
   I like the large watermark and gradient, but I'd make two changes:
   - Reduce the watermark opacity slightly so it doesn't compete with the
     authentication form.
   - Make the gradient more subtle around the form and stronger toward the
     bottom corners.

### Summary

- **Outcome:** the top-bar glitch is fixed, and sign-in and sign-up are
  redesigned. 174 tests pass (153 before), and `ruff check` and
  `ruff format --check` are clean. Headless Edge captured sign-in (blank,
  after a wrong password, with the password shown) and sign-up with field
  errors. A DevTools-driven check confirmed the hover gate.
- **The glitch:**
  - **Finding:** title-bar screencasts during navigation showed no font
    flash in headless Edge, even with the cache off. They did show that
    clicking a title-bar chip lands the cursor on whichever chip sits there
    on the new page. Real browsers re-apply `:hover` there, so the chip
    flipped to its icon and went white the moment the page appeared. An
    activity-bar click popped its tooltip the same way.
  - **Fix:** `shell.js` sets `<html data-pointer>` only after the pointer
    moves more than 4 px, and every chrome `:hover` rule is now prefixed
    `html[data-pointer]`. Keyboard focus isn't gated. A DevTools check
    showed TOOLBOX stays a label after a zero-distance move on arrival,
    and flips after a real 12 px move.
  - **Second, likely cause:** the fonts used `font-display: swap`, so a
    slow font would paint the mono labels in a fallback and then jump.
    `base.html` now preloads the four chrome fonts, and JetBrains Mono and
    Plus Jakarta Sans use `font-display: block`.
- **Sign-in and sign-up:**
  - A new `registration/auth_base.html` holds both pages: one bordered
    `#auth-card`, two equal-height columns, and contents centred
    vertically. The form column is plain: Account micro-label, a 2.5 rem
    headline, the lead, the fields, `pt-4` above a full-width square
    submit, and a ruled switch link.
  - The branding panel sits on a monochrome radial glow. It has the
    wordmark, "Your assets. Your projects. / Your Axcenity.", the
    supporting line and a "Toolbox" micro-label.
  - `partials/form_fields.html` rewrite:
    - form-wide errors as a `role="alert"` `.form-alert` with an icon
    - field errors right under each field, in a list whose id matches
      Django's `aria-describedby`
    - help-text ids
    - a show/hide toggle on every password input (new
      `static/js/password-toggle.js`, loaded on auth pages only)
    - a "Forgot password?" slot beside the password label
  - Password recovery is out of scope (PRD), so the link shows only once
    an `accounts:password_reset` URL exists.
  - Inputs are square, with a subtle focus ring (a light border and a
    3 px, 12 % white glow) and a red edge when invalid. The forms are
    `novalidate`, so all errors show inline.
  - **Title bar:** the sign-in page shows only Sign up on the right, and
    the sign-up page only Sign in, without a `?next=` back to sign-up. The
    active breadcrumb stays.
  - **Background:** a new `auth` surface has no hero glow and no rings.
    The centre blob is at 10 %, and the corner blobs at 80 % stay in
    their corners. The watermark drops from 6 % to 3.5 %. Reduced motion
    stops the corner drift too.
- **Files:** `templates/base.html`, `static/js/shell.js`,
  `static/js/password-toggle.js` (new), `styles/source.css`,
  `templates/registration/auth_base.html` (new),
  `templates/registration/login.html`,
  `accounts/templates/accounts/signup.html`,
  `templates/partials/auth_brand.html`,
  `templates/partials/form_fields.html`, `templates/partials/icon.html`
  (eye, eye-off, alert), `tests/test_shell.py`,
  `tests/test_auth_pages.py` (new), `tests/urls_with_password_reset.py`
  (new, test-only URLconf), `docs/FRONTEND.md`, `docs/TESTING.md`.
- **Tests:** the hover-inversion test now expects the gate prefix, and
  the auth pages' surface test expects `auth`. New tests cover:
  - the hover gate in `shell.js` and the CSS
  - the font preloads and `font-display: block`
  - the bordered two-column card
  - the brand glow and message
  - the heading size
  - each page's top-right actions, with other pages keeping both
  - password toggles, and their script loading only on auth pages
  - the Forgot link: hidden now, shown under the stand-in URLconf
  - room above the submit button
  - the focus ring
  - the wrong-password alert
  - linked field errors
  - the auth background rules, including reduced motion
- **Deviations:**
  - "Optionally, a Home link": no right-hand Home was added, because the
    user removed it in round 2 and the Home chip on the left already does
    the job.
  - The redundant-action rule was applied to sign-up as well, so it shows
    only Sign in.
  - The auth pages got their own `auth` surface, not `work`, so their
    background could be shaped separately.
  - The glitch was never reproduced exactly in headless Edge. Both fixes
    target the two causes the investigation pointed to: hover on arrival
    (confirmed and fixed) and a late font swap (not seen locally, guarded
    against).
- **Sideways:**
  - A sed edit stripped the `\b`s from a regex, and the test failed. It
    was fixed with the editor.
  - The first field-error regex assumed Django's `aria-describedby` held
    only the error id. It lists the help text id first, so the regex was
    loosened. The markup was correct.
  - Early screencast frames came back at shifting sizes, a headless
    artefact. Frames not at 1440×900 were dropped from the comparison.
  - A test session for `test_user` was created in the local dev database
    for signed-in captures and deleted afterwards.

## 2026-10-30 — Axcenity Toolbox: Phase 1 shell polish, round 3 (showcase vs work surfaces, library controls, solid empty state)

### Prompts

1. Ok I would like for you to change the following:
   Reduce the watermark opacity slightly by roughly 20-30%
   Give the panel a slightly more visible surface, a cleaner border, and
   more vertical padding. The current dotted outline is difficult to
   distinguish from the background.
   Even when the library is empty, show where search, sorting, filtering,
   and view controls will live. This establishes the layout before assets
   are added.
   The heading and description are good, but the empty-state panel sits
   quite far below them. Bring the content together slightly.
   Marketing/discovery surfaces: More expressive gradients, oversized
   branding, and atmospheric backgrounds.
   Working surfaces: Library, Packs, and asset management should be more
   restrained, with stronger content hierarchy and less prominent
   background effects.

### Summary

- **Outcome:** all six changes are in. 153 tests pass (137 before), and
  `ruff check` and `ruff format --check` are clean. Headless Edge
  captured Home and Library signed in, Packs, and Discover signed out.
- **Changes:**
  - **Watermark:** opacity went from 0.08 to 0.06, 25 % less.
  - **Empty-state panel:** the dashed outline is now a solid `bg-surface`
    panel with a `border-line-strong` border. Vertical padding went from
    `p-10` to `py-16`. The title is brighter, and the link is a
    `.btn-quiet`.
  - **Library controls:** `#library-toolbar` sits directly under the
    header: search (`q`), sort (the PRD's four sorts) and a grid/list view
    toggle. `#library-filters` sits in the side panel, where the PRD puts
    filters, with Type, Provider, Status and Minimum rating chips. All are
    disabled until Phase 4, and while the library is empty. The empty
    state says they switch on once something is saved. New icons: `filter`,
    `sort`, `grid` and `list`.
  - **Closer together:** the content wrapper went from `space-y-12` to
    `space-y-8`. Library and Packs wrap the header, controls and panel in
    a `space-y-5` section.
  - **Two moods:** `<main data-surface>` comes from a new
    `{% block surface %}` (default `work`).
    - **Showcase (Home, Discover):** the hero glow is taller (40 rem) and
      stronger (75 %), with ripple rings. A soft top light sits under the
      dot grid. An oversized, cropped mark (`.hero-atmosphere` and
      `.hero-mark`) sits behind the hero, top right.
    - **Work (Library, Packs, Account, Settings, the auth pages):** no
      hero glow or mark. The footer glow is at 35 % opacity, 22 s and has
      no rings. Headers use a new `compact` option on
      `page_header.html` (a 2 rem headline and a 14 px lead), so the
      content leads.
  - **Files:** `templates/base.html`, `templates/partials/page_header.html`,
    `templates/partials/empty_state.html`, `templates/partials/icon.html`,
    `catalog/templates/catalog/library.html`,
    `catalog/templates/catalog/discover.html`,
    `packs/templates/packs/home.html`,
    `packs/templates/packs/pack_list.html`, the profile and settings
    templates, `styles/source.css`, `tests/test_shell.py`, the new
    `tests/test_library_page.py`, `docs/FRONTEND.md` (new "Two moods" and
    "Library layout" sections), `docs/TESTING.md`, and
    `plans/axcenity-toolbox.md`. The plan's Phase 2a and Phase 4 got
    "Already in place" notes: Discover should read `q`, and Phase 4 should
    wire up the existing controls and decide on the view toggle.
  - **Tests:** the watermark and spacing assertions were updated. The
    drop-tint regex was loosened, because `data-surface` now follows
    `data-drop` on `<main>`. New tests cover:
    - each page's mood and header size
    - auth pages as work surfaces
    - the showcase and work CSS
    - the single oversized mark
    - the library toolbar's position, controls and disabled state
    - the side-panel filter groups, and their absence elsewhere
    - the tighter header-to-content spacing
    - the solid empty-state panel
- **Deviations:**
  - Filters went in the side panel, not the toolbar, because the PRD
    and plan put them there. Search, sort and view are in the toolbar.
  - The view toggle isn't in the PRD, which describes only a card grid.
    It was added because the user asked for view controls, and flagged in
    the plan's Phase 4 for a decision.
  - Account, Settings, sign-in and sign-up were treated as work surfaces
    along with Library and Packs.
  - Nothing was wired up. The controls are disabled placeholders, to stay
    inside Phase 1.
- **Sideways:**
  - After adding `data-surface`, seven per-page tint tests failed. Their
    regex had expected `data-drop` to end the `<main>` tag. The regex was
    fixed, not the markup.
  - A test session for `test_user` was created in the local dev database
    for signed-in screenshots and deleted afterwards.

## 2026-10-30 — Axcenity Toolbox: Phase 1 shell polish, round 2 (hero search, hero glow, watermark back, one Home chip, tooltips, current-page marks)

### Prompts

1. Ok I like the changes so far but I wouldl like to make a few general
   tweaks the color shifting background I wouldlike to make it slightly
   more subtle and apply a similar affect throughout portions of the page
   to make it looks cohesive. Next the axcenity logo on the bottom is a
   nice touch but I still appreadiated the watermark in the empty space
   where other menus and feature will eventually go. Also there are two
   home buttons one on the very right and another on the left next to
   toolbox can you get rid of the one on the right and keep the one on
   the left and push it all the way to the left before toolbox
   also do some of these other things
   Give the hero a little more breathing room.
   Make the headline slightly smaller, but more refined.
   Add a prominent search bar directly below the description.
   Keep Discover and Library as secondary actions.
   Reduce the bottom logo to a subtle brand signature.
   Add a subtle active indicator on the selected page.
   Show tooltips when hovering over icons.
   Give the icons slightly more consistent spacing.
   Add a smooth transition when the side panel expands.
   Make the current page more obvious.

### Summary

- **Outcome:** all fourteen requests are in. 137 tests pass (127 before),
  and `ruff check` and `ruff format --check` are clean. Headless Edge,
  driven over the DevTools protocol, captured Home, Discover and Library
  signed in and out, the tooltips, and four frames of the panel
  expanding.
- **Changes:**
  - **Glow, softer and page-wide:** the blobs dropped from 80 % to 55 %
    opacity with a wider blur. A flipped, 40 %-opacity copy of the glow
    (`.page-glow`, no ripple rings) now hangs from the top of the content
    behind the hero. The colour trios moved from the footer to
    `<main id="content" data-drop>`, so both glows share them. The bars
    and side panel stay monochrome.
  - **Watermark back, logo now a signature:** the giant full-width
    wordmark is back in the footer at 8 % opacity (`.watermark`), filling
    the empty space. Under it, `.brand-signature` is one row: "Built for
    Axcenity Engine", a small `w-20` wordmark, "Axcenity Studios · 2026".
  - **One Home chip:** the right-hand Home is gone. The only Home chip
    sits between the wordmark and TOOLBOX. The home page's own "home"
    breadcrumb is removed (new `{% block breadcrumb_nav %}`, emptied in
    `packs/home.html`), so the left-hand duplicate is gone too. The Home
    chip is marked current on that page.
  - **Hero:** the content wrapper has more room
    (`px-8 lg:px-12 pt-14 pb-12 space-y-12`). `page_header.html` uses a
    new `.headline` (Plus Jakarta 700, `-0.025em`, `text-wrap: balance`,
    44 px at md, down from 48 px at 800 weight) with `space-y-4` and a
    15 px lead.
  - **Hero search:** `packs/home.html` has a square 56 px `#hero-search`
    bar directly below the description, sending `?q=` to Discover. Its
    Search button is the page's only `btn-primary`. Browse Discover and
    Open your library (or Sign up and Sign in for visitors) are now
    outlined, square `.btn-quiet` buttons.
  - **Current page:** activity-bar entries and side-panel rows get a
    lifted fill and a 2 px white left bar (rows also go semibold). The
    current title-bar chip gets a fill and a 2 px white underline.
  - **Tooltips:** activity-bar icons and the panel toggle show a white
    mono `.tip` to the right after 0.2 s, replacing the native `title`
    attributes. `shell.js` switches the toggle's tip between "Collapse
    panel" and "Expand panel". The activity bar is `relative z-20` so tips
    sit over the side panel.
  - **Icon spacing:** one icon size per bar, 16 px in the title bar
    (crumbs included) and 20 px in the activity bar. The first entry group
    in the activity bar and the side panel both start `pt-1` below their
    borders, so rows still line up.
  - **Panel expand:** the width eases out over 0.5 s, the contents fade in
    0.08 s later, and rows slide in on a 0.1 to 0.25 s stagger. Collapse is
    unchanged, and reduced motion turns it all off.
  - **Files:** `templates/base.html`, `templates/partials/page_header.html`,
    `templates/partials/crumb.html`, `packs/templates/packs/home.html`,
    `static/js/shell.js`, `styles/source.css`, `tests/test_shell.py`,
    `tests/test_theme.py`, `docs/FRONTEND.md` (plus a new "Home hero"
    section), `CLAUDE.md` (the colour rule now names the hero glow).
  - **Tests:** the footer, Home-button, swap-chip, drop-palette and
    primary-button tests were rewritten for the new layout. New tests
    cover:
    - the watermark and signature
    - a single Home chip left of TOOLBOX, and no duplicate crumb on Home
    - the hero glow and the softer blobs
    - the hero search as the one primary action, for members and visitors
    - the refined headline
    - the content wrapper's spacing
    - the tooltips
    - one icon size per bar
    - the current page marked in all three places
    - the expand transition with its staggered rows
- **Deviations:**
  - "Keep the one on the left and push it all the way to the left before
    toolbox" was read as the home page's "home" breadcrumb, which sat
    right of TOOLBOX. The single Home chip now sits right after the
    wordmark and before TOOLBOX. The wordmark still links home.
  - "The hero" and "Discover and Library" were read as the home page,
    whose hero had those two buttons. The search bar is there only.
    Discover's own command-bar search remains Phase 2a. Visitors' Sign up
    and Sign in became secondary too, so Search stays the only primary
    action. The old test that Sign up was the home page's primary button
    was replaced.
  - The glow now reaches the hero, which widens the 2026-10-30 colour
    exception from "footer only" to "the content area's glows". The bars
    and side panel stay monochrome. FRONTEND.md and CLAUDE.md say so.
- **Sideways:**
  - Git Bash rewrote the screenshot script's `/` path argument into
    `C:/Program Files/Git/`, so the first capture saved files named `C`.
    Paths are now passed without the leading slash.
  - Two Python heredocs failed in the shell on quoting, so those scripts
    went to scratch files instead.
  - A test session for `test_user` was created in the local dev database
    for signed-in screenshots and deleted afterwards.

## 2026-10-30 — Axcenity Toolbox: Phase 1 shell polish (hover icons, inverted hovers, vivid glow, Home on the right)

### Prompts

1. Ok I currently have my website built in phase 1 @plans/axcenity-toolbox.md
   however there are some additional things I would like changed
   appearance-wise. I mentioned I wanted Icons for toolbox and discover
   buttons, can you make it to where when you however over the text it
   changes it to an icon. Also I want the hover effect colors to contrast
   more rather than just be a light grey make it to where it will change
   the button to be black on a white background and vice versa. Next the
   axcenity watermark is hard to see on the bottom of the page I would
   just like it to be in the center similar to how it was before. Also the
   bottom glowing effect is not as impressive as I wouldlike it to be and
   th colors are not that vibrant can you make the movement more
   accentuated more vibrant colors and make sure that the text still
   remains readable. Also for the buttons on the top I noticed you used
   rounded corners I wouldlike to make the simple squared because I am
   going for a more modern geometric style. Also there is a weird grey bar
   shifting on the bottom can this be fixed. Can you also make sure that
   the home button is on the very right this will eventually be built
   into another website. Also please append any conversations to
   PROMPTS.md according to source formatting.

### Summary

- **Outcome:** Phase 1's shell got the seven appearance changes. No new
  feature or phase work. 127 tests pass (113 before, plus 14 new), and
  `ruff check` and `ruff format --check` are clean. Headless Edge,
  driven over the DevTools protocol, captured hover states and glow frames
  signed in and signed out to check each change.
- **Changes:**
  - **Hover icons:** "TOOLBOX", every breadcrumb and the new "HOME" chip
    are `.chip-swap` chips. The label and an icon share one grid cell, and
    on hover or focus the label fades out while the icon rises in. The
    chip keeps its width. New `partials/crumb.html` builds the
    breadcrumbs, and all eight page templates use it, each with its
    page's icon (discover = search, library, packs, home, account = user,
    settings = gear, sign in, sign up). `partials/icon.html` gained
    `toolbox` and `home` icons.
  - **Inverted hovers:** activity-bar entries, the panel toggle,
    side-panel rows and title-bar chips turn white with black content.
    The wordmark chip turns white and its image inverts to black.
    `btn-primary` (Sign up) turns black with white text and a white edge,
    and plain `btn`s turn white. The `.btn` rules are unlayered so they
    beat DaisyUI's hover tint.
  - **Watermark:** the footer wordmark is now centred, about 26 rem wide
    and full white (it was full-width at 7 % opacity). The credits sit
    centred below it as one line.
  - **Glow:** three blurred, screen-blended blobs, each drifting and
    scaling on its own path (9, 11 and 13 s), plus ripple rings pulsing
    every 6 s. New vivid colour trios per page replace the pastels.
    `.footer-text` adds a dark drop shadow so the wordmark and credits
    stay readable. Reduced motion stops all of it.
  - **Square corners:** title-bar chips, the Sign-up button and the
    panel toggle are square.
  - **Grey bar:** the old glow animated the whole layer up by 4 %, which
    bared a strip of plain background along the footer's bottom edge as it
    moved. The layer is now still, and only the blobs move. They're
    anchored 45 % below the bottom edge, so no edge can show. Sampled
    pixels along the bottom are coloured in every captured frame.
  - **Home on the right:** a "HOME" chip (`#home-button`) after a divider
    is the last item in the title bar, signed in or out.
  - **Files:** `templates/base.html`, `templates/partials/crumb.html`
    (new), `templates/partials/icon.html`, the eight page templates,
    `styles/source.css`, `tests/test_shell.py`, `tests/test_theme.py`,
    `docs/FRONTEND.md`, `CLAUDE.md` (the colour rule now says "footer drop
    glow" instead of "pastel").
  - **Tests:** existing assertions were updated for the new chip markup
    and the new colour trios. New tests cover:
    - each page's swap chips, with the current crumb carrying its page's
      icon
    - the CSS that hides the icon until hover
    - Home as the last title-bar control, signed in and out
    - square title-bar buttons and panel toggle
    - the hover inversion rules
    - the still glow layer with anchored, animated blobs, and reduced
      motion
    - the three blobs in the markup
    - the centred, full-white wordmark
- **Deviations:**
  - "Home button on the very right" was read as a new Home chip at the
    far right of the title bar. The wordmark and "TOOLBOX" still link
    home too.
  - "Discover button" was read as the breadcrumb chip, so every page's
    crumb got its own icon, not just Discover's.
  - Square corners were applied to the title bar and the panel toggle
    only. Buttons inside page content keep DaisyUI's radius.
  - The inverted hover was extended to the activity bar and side-panel
    rows so all hover states match.
  - The drop colours are now vivid, not pastel. `test_theme.py` keeps the
    name `PAGE_PASTELS` with a comment saying so.
- **Sideways:**
  - The first hover capture showed the Toolbox icon grey on white:
    its `text-fg-secondary` utility outranked the hover colour. It moved
    to a `.bar-item-app` component class, and FRONTEND.md now warns
    against colour utilities on chips.
  - A docs-update script stopped on a search string that didn't match
    and wrote nothing. It was corrected and rerun.
  - To capture signed-in screenshots, a session for `test_user` was
    created in the local dev database. It was deleted afterwards.

## 2026-10-30 — Axcenity Toolbox: Phase 1/14, Branded shell and accounts

### Prompts

1. The `/implement` skill, given `axcenity-toolbox phase 1`.
2. Ok please write a CLAUDE.md file with progressive disclosure using the
   docs folder to sotre more advanced information about the application
   when needed. Next make sure that out of the tests you do create make on
   that makes the access control tests explicit and that anonymous users
   can access discover but receive the expected redirect or denial for
   Library Packs Profile and Settings. Verify that sign-out rejects GET and
   works through POST.
   Next regarding the font pint the Plus Jakarta Sans source record the
   exact google fonts commit or version that was used as well as the OFL
   license attributed to it.
   Other than that everything else looks good and you are good to start
   building.
3. Ok so a few things I want to change firstly lets remove the CIDM 3312
   -2026 and Replace it with Axcenity Studios 2026 next the sidebar collaps
   I feel should be on the left where the actual sidebar are. Also I am not
   too sure why the discover library and packs are offcenter from the
   buttons can these be lines up with bigger text. next the site logo is
   incredibly small can we make it bigger. The water mark is also in a
   strange place I feel like the Built for Axcenity engine and Axcenity
   Studios text should be below the watermark. Additionally with the sign
   in I feel that the logo should be on the right of the sign in menu. Also
   I created a test_user account at with the username as test_user and
   password 5eMN9sKdr6cvJB if you can save this in docs and the README.
4. Ok some more additional changes these are smaller and mostly boil down
   to allignment:
   The sidebar close menu I would like to have the bottom on the actual
   sidebar itself remove the top axcenity logo as there is already one
   towards the top of the page. Next the Actual user account and sign out
   appear misalligned, some iconography would be nice here. Same with the
   topbar menus such as toolbox and discover which are also misalligned
   with the axcenity logo. Some however affect would also go a long way
   here. Next I would like the sidebar menu to have a sleek animation
   feature, and I want to differ a bit from artcrafts design a bit on the
   bottom of a page can you add a water drop gradient effect while still
   keeping the dot matrix pattern it should use some pastel colors for
   each page to make it more vibrant.

### Summary

- **Outcome:** The Django project now wraps the existing `providers`
  package. It runs Django 6.1.2, django-tailwind-cli 4.8.2 (DaisyUI
  through the standalone binary, so no Node), django-htmx 1.29 and Ruff.
  Every page renders inside the editor shell: title bar with wordmark and
  "TOOLBOX", activity bar, collapsible side panel and a monochrome status
  bar with placeholders. Sign-up, sign-in and sign-out (POST only) work,
  and members-only pages send visitors to sign-in and back. The test folder
  has a shared conftest with the cache-clearing fixture and the network
  guard. 113 tests pass, and `ruff check` and `ruff format --check` are
  clean. All ten Phase 1 boxes are ticked in the plan.
- **Changes:**
  - `pyproject.toml`, `uv.lock` — runtime deps (django, django-tailwind-cli,
    django-htmx); dev deps (ruff, pytest, pytest-django, responses,
    pytest-cov); pytest and Ruff config (line length 100; rules E, F, W, I,
    B, UP and DJ; E501 left to the formatter; Markdown excluded).
  - `manage.py`, `config/settings.py`, `config/urls.py`, `config/asgi.py`,
    `config/wsgi.py` — the project. Settings cover the three apps, HTMX
    middleware, local-memory cache, login URLs, static dirs and Tailwind.
  - `config/context_processors.py` — provider names for the status bar.
  - `accounts/` (`views.py`, `forms.py`, `urls.py`, `templates/accounts/*`)
    — `SignUpView` signs the new member in and honours a same-site `next`.
    Login and logout use Django's views, with logout POST only. Profile
    and Settings are members-only pages. `StyledFieldsMixin` gives the
    inputs DaisyUI classes.
  - `catalog/` and `packs/` (views, urls, templates) — the pages the
    activity bar links to: Home and Discover (open to everyone), Library
    and Packs (members only), each with a ghost-mark empty state.
  - `templates/base.html`, `templates/partials/*`,
    `templates/registration/login.html` — the shell, the page header, the
    empty state, the form fields and the icon partials.
  - `static/js/shell.js` — the side-panel toggle. An inline `<head>`
    script applies the saved state before first paint.
  - `styles/source.css` — the Tailwind source. It resets Tailwind's
    palette, turns off DaisyUI's themes, defines the single `axcenity`
    theme from the editor's dark palette and the four type tokens, and
    declares the `@font-face` rules and logo masks.
  - `static/brand/*` — wordmark-white, mark-white, mark-white-small,
    icon-256 and favicon-32, copied from the engine repo.
  - `static/fonts/*` — Inter and JetBrains Mono from the engine repo, Plus
    Jakarta Sans from Google Fonts, and each family's OFL licence.
  - `static/fonts/SOURCES.md` — the pins for the fonts:
    - google/fonts commit `8b0a1d0f5983c89bc2b93f1b5fb55f9e252744b5`
    - the font file's SHA-256
    - the upstream Tokotype commit
    - the copyright and OFL 1.1 terms
    - the engine commit the other fonts were copied from
  - `tests/conftest.py`, `tests/test_access_control.py`,
    `tests/test_accounts.py`, `tests/test_shell.py`, `tests/test_theme.py`,
    `tests/test_network_guard.py`, `tests/test_console_regression.py` — the
    suite (see TDD).
  - `asset_search.py`, `providers/http.py`, `providers/openverse.py`,
    `providers/polyhaven.py` — Ruff reformatting only, plus
    `zip(..., strict=False)` twice and `raise SystemExit(0) from None`. The
    regression tests passed before and after.
  - `CLAUDE.md`, `docs/ARCHITECTURE.md`, `docs/TESTING.md`,
    `docs/FRONTEND.md` — progressive disclosure. CLAUDE.md holds the
    commands, the always-on rules and a "Read before…" table pointing into
    `docs/`.
  - `.gitignore` — the built `static/css/tailwind.css` and the downloaded
    `.django_tailwind_cli/`.
  - `plans/axcenity-toolbox.md` — Phase 1 boxes ticked.
  - **Prompt 3 layout changes:**
    - `templates/base.html` — the footer reads "Axcenity Studios · 2026",
      and the giant wordmark now sits above the footer text. The panel
      toggle moved to the far left of the title bar, a `w-14` cell over
      the activity bar. The title bar is now `h-12`, and the wordmark went
      from 18 px to `h-8` (32 px). The side-panel header is `h-14` and the
      default rows use `.panel-row`, so Discover, Library and Packs line up
      with their activity-bar icons in larger 15 px text.
    - `styles/source.css` — the `.panel-row` style: `h-11` rows matching
      the activity bar, with hover and current-page states.
    - `templates/partials/auth_brand.html` and
      `templates/registration/login.html`,
      `accounts/templates/accounts/signup.html` — the forms sit in a
      two-column layout, with a wordmark panel to the right on wide
      screens.
    - `accounts/templates/accounts/profile.html`, `settings.html` — their
      side panels use the same rows.
    - `tests/test_shell.py` — five new tests: the toggle position, the
      wordmark size, the row alignment, the footer order and text, and the
      logo to the right of both auth forms.
    - `README.md`, `docs/TESTING.md` — the `test_user` account, with a
      note that it lives only in the git-ignored local database.
    - `docs/FRONTEND.md` — describes the new layout.
  - **Prompt 4 alignment and polish:**
    - `templates/base.html` — the Home logo tile is gone from the activity
      bar. The panel toggle took its place, in an `h-14` slot level with
      the panel's header, with a collapse icon and an expand icon. The
      title bar became `h-8` chips with hover backgrounds: the wordmark,
      "TOOLBOX", breadcrumb links, the account chip (user icon), sign-out
      (logout icon), sign-in (login icon) and sign-up (user-plus icon).
      The footer gained the drop glow, and the credits became brighter so
      they read over it.
    - `styles/source.css` — the `.bar-item`, `.crumb`, `.brand-link` and
      `.panel-toggle` hover styles, with a 4 px text nudge so mono caps sit
      on the wordmark's centre line. The panel now slides: its width goes
      to 0 over 0.42 s while the contents fade and drift, and it becomes
      `visibility: hidden` at the end. A reduced-motion fallback turns it
      off. Six per-page pastel trios drive the `.drop-glow`: three
      translucent radial gradients plus ripple rings, drifting slowly over
      the dot grid. The dots now scroll with the content.
    - `static/js/shell.js` — turns on the slide only after the first
      frame, so page loads never animate, and swaps the toggle's title.
    - `templates/partials/icon.html` — the panel-close, panel-open, login,
      logout and user-plus icons.
    - Every page template — its breadcrumb is now links.
      `accounts/templates/accounts/settings.html` — new copy for the
      toggle's location.
    - `tests/test_shell.py`, `tests/test_theme.py` — tests for:
      - the toggle replacing the logo tile
      - the slide CSS and its after-first-paint switch
      - chip icons and breadcrumb links
      - the drop palette per page
      - pastels allowed only in the drop rules, and never matching a
        type colour
    - `docs/FRONTEND.md`, `CLAUDE.md` — the new shell, and the pastel
      exception to the colour rule.
- **TDD:** Skipped. The phase is scaffolding, configuration and Django's
  built-in auth, with no new business rule, and the earlier TDD review
  found no Phase 1 candidates. The criteria got ordinary tests:
  - `test_access_control.py` states the rules page by page:
    - Home and Discover return 200 to visitors.
    - Library, Packs, Profile and Settings return 302 to
      `/accounts/login/?next=<path>`, and signing in returns to the page.
    - An off-site `next` is ignored.
    - A GET to sign-out returns 405 and the member stays signed in; a POST
      signs them out.
    - Sign-up, sign-in and sign-out without a CSRF token return 403.
  - The network guard is proven against requests, `get_json()`, urllib
    and raw sockets.
  - Console regressions cover each provider's `search()` and
    `get_details()`, plus three end-to-end runs of `asset_search.main()`.
- **Decisions:**
  - **Plus Jakarta Sans:** the engine repo doesn't have it. It was
    downloaded from google/fonts at a pinned commit, and renamed
    `PlusJakartaSans-Variable.ttf` for clean static URLs.
  - **Network guard:** it patches `socket.getaddrinfo` and `connect`, and
    raises a `RuntimeError` subclass so `get_json()` can't turn it into a
    `ProviderError`.
  - **Colour test:** it checks `styles/source.css` against the editor
    palette plus the type colours. DaisyUI's `info` is grey, so it can't
    be confused with the HDRI blue, and every `*-content` colour is the
    app background `#171717`.
  - **Placement:** Home lives in `packs` (`packs:home`), since it becomes
    the gallery. Settings is a members-only page that shows the active
    theme. The status bar shows grey "unknown" dots, and the saved count
    only for members.
  - **Active nav:** set through each view's `extra_context`.
- **Deviations:**
  - The user asked for a `CLAUDE.md` with progressive disclosure into
    `docs/`. The brief had offered only `docs/TESTING.md`.
  - The user asked for one explicit access-control test file covering
    Discover versus Library, Packs, Profile and Settings, and GET versus
    POST sign-out.
  - The user asked for the Plus Jakarta Sans source to be pinned with its
    OFL attribution.
  - After the first build, the user asked for six layout changes and for
    the `test_user` login to be recorded in the docs and the README. The
    agent made one extension that wasn't asked for: sign-up gets the same
    logo panel as sign-in, because the two pages share a layout. Headless
    Edge screenshots before and after checked each change.
  - Prompt 4 overrides two earlier decisions:
    - The activity bar's Home tile, which the plan's Phase 1 spec
      requires, was removed at the user's request. The wordmark links
      home.
    - The per-page pastels break the PRD's rule that colour only ever
      means asset type (story 74). It's recorded as a deliberate, tested
      exception, confined to the footer glow.

    "Sidebar close button on the actual sidebar" was read as the
    activity-bar slot that held the logo. That slot is level with the
    panel's header and stays visible when the panel collapses.
- **Sideways:**
  - Ruff 0.17 also formats Python code blocks inside Markdown, and
    rewrapped the snippets in `docs/code-walkthrough.md`. A
    `git status` check caught it. The file was restored and `*.md` was
    excluded from Ruff.
  - Two shell heredocs (the templates and this log entry) failed on
    quoting, so those files were written with the editor tool instead.
  - Two first-run test bugs:
    - The nav's own `aria-label="Main"` was counted as an entry.
    - `client` and `member_client` turned out to be the same object.

    Both tests were fixed. Password hashing in tests was switched to MD5,
    which cut the suite from 18 s to under 1 s.
  - The approved brief said `zip(..., strict=False)`. The first edit used
    `strict=True`, and it was changed back to match the approval.
  - The first logo panel on the sign-in page showed the mark above the
    wordmark, so the "A" appeared twice. The screenshot caught it, and the
    panel was cut to the wordmark alone.
  - Measuring the title bar in a screenshot showed the mono labels 2 px
    above the wordmark's letters. After the fix, a second measurement
    showed "TOOLBOX" unchanged. That turned out to be two stale things,
    not the fix: Edge's cached stylesheet, and Django's cached template
    under `runserver --noreload`. A fresh browser profile and a server
    restart showed every label at the wordmark's centre (24.5 px).
  - A heredoc turned `\b` into a literal backspace character in
    `tests/test_theme.py`. `grep -P '\x08'` found it, and it was
    removed.
  - The first glow was too faint to read as "vibrant", so its strength was
    raised from about 30% to about 48%.

## 2026-10-30 — Picked TDD candidates for each Axcenity Toolbox phase

### Prompts
1. `@plans/axcenity-toolbox.md` `@prd/axcenity-toolbox.md` `/tdd` Look
   through the plan and determine which phase would be good candidates for
   TDD, keep in mind all phases will likely not need TDD and should only
   be applied if necessary. Also append this conversation including this
   one and further messages to PROMPTS.md according to source formatting.
2. Ok I want to make 2 additional adjustments - HTMX integration test to
   phase 5 this verifies that if one provider shelf fails the other
   providers shelf still renders successfully.
   Do not make the test require a particular order between ranking assets
   with equal counts instead just test the ranking groups and establish a
   tie-breaking rule for whatever you feel is appropriate.

### Summary
- **Outcome:** The agent ran the selection step of the `tdd` skill
  against every phase of `plans/axcenity-toolbox.md`. It proposed at most
  three behaviors in each of ten phases (2a, 2b, 3, 4, 6, 7, 8, 9, 10,
  11). Phases 1, 5, 12 and 13 got none, because they're configuration,
  framework wiring, UI or motion, or a rule the access gate already tests.
  After the user's two changes:
  - Phase 2a gained a second candidate: the HTMX mixed-shelf test, where
    one provider's shelf fails and the other's still renders its results.
  - The Phase 10 ranking test now checks the groups of equal shared-tag
    count in order, not the order inside a group. The agent chose the
    tie-break (title A–Z, then id) and added it to Phase 10's acceptance
    criteria in the plan.

  The candidates are waiting for the user's approval. No app code was
  written and nothing was committed.
- **Deviations:**
  - The skill picks behaviors for one phase at a time. The user asked
    about the whole plan, so the agent made the selection for every phase
    at once. The red-green cycles still run phase by phase as each one is
    built.
  - The user asked for the shelf test in "phase 5". The plan's Phase 5 is
    the library drawer, which has no shelves. Step 5 of the PRD's build
    order is "Discover: provider shelves and error handling", which is the
    plan's Phase 2a, so the agent put the test there and said so.
- **Sideways:** None.

## 2026-10-30 — Planned the Axcenity Toolbox build from the PRD

### Prompts
1. `/prd-to-plan` `@prd/axcenity-toolbox.md` append this sessions
   conversations to PROMPTS.md according to source formatting.
2. Ok I would split phase 2 into two phases 2a provider search, shelves,
   HTMX loading and error handling 2b caching, provider credits fallback
   icons status bar and failure tests
   Merge phase 9 and 10
   Keep 5 and 6 seperate as well as 7 and 8 keeping tier 2 seperate as
   well
   Also add completion gates for every phase making sure that every
   relevant automated test passes no live provider API occurs during a
   test existing functionality remains operations and access control
   rules are tested whenever possible making sure that ruff passes.
   Also for the PRD since I did not mention this early please update the
   build order:
   Split Discover into two milestones prover shelves and error handling
   then caching and status reporting
   combine the main-page gallery and demo data into one final tier 1
   milestone
   Kep tier 2 ordering unchanged
   Clarify the existing phase 2 requirements. for story 83 which involves
   failure tests make sure that the provider client tests using responses
   application level tests using mocked provider functions
   HTMX shelf behavior when one provider fails and another succeeds.
   Also add one clarification to the data model, as of now the Asset model
   is shared accross users while SavedAsset is user-specific.
   Asset records are resused globally
   SavedAsset records are unique per user and asset
   Deleting a SavedAsset must never delete the shared Asset
   A PackItem can only reference a SavedAsset belonging to its pack owner.
   Clarify API authentication:
   Websites forms use Django CSRF protection
   Session-authenticated API write requests require CSRF validation.
   Token-authenticated API requests use the token instead

### Summary
- **Outcome:** The agent ran the `prd-to-plan` skill on
  `prd/axcenity-toolbox.md` and wrote `plans/axcenity-toolbox.md`.
  - **Phases:** 14 vertical slices. Tier 1 is Phases 1, 2a, 2b and 3–9,
    and Tier 2 is Phases 10–13.
  - **Header:** the durable decisions (apps, URLs, models, the
    shared/per-user record rules, access, authentication and CSRF,
    providers and caching, frontend, testing).
  - **Completion gate:** a standard gate that every phase repeats: all
    tests pass, no live provider calls, existing features still work, the
    access rules are tested, and Ruff passes. Each phase also lists its
    own access-rule checks.

  The PRD got four updates:
  - the shared/per-user record rules in the data model
  - the CSRF rules under Authentication
  - the three test levels for story 83
  - the Tier 1 build order: Discover is split into two milestones, and the
    gallery and demo data are merged into the final one

  No app code was written and nothing was committed.
- **Deviations:**
  - **User changes to the breakdown:** the user split Discover into 2a
    and 2b, merged the gallery phase with the demo-data phase, kept
    Phases 5/6 and 7/8 separate, kept Tier 2 as proposed, and asked for a
    completion gate on every phase.
  - **Stories moved by the agent:** the agent moved a few stories from
    where the PRD's build order puts them, so that each phase can be
    demoed on its own:
    - Delete-with-pack-list (story 31) and the drawer's list of packs
      (part of story 25) go in the pack builder phase, because packs
      don't exist before it.
    - The status bar (story 73) is split. Provider status comes with
      Discover, and the saved count comes with saving.
    - The token page (story 6) goes with the library API, not with
      accounts.
  - **"Phase 2":** "Clarify the existing phase 2 requirements" could mean
    the plan's Discover phase or the PRD's build-order step 2 (provider
    error tests). The agent applied the three test levels to both: Phases
    2a and 2b in the plan, and the PRD's Testing section.
  - **Decisions the PRD left open:**
    - Pack slugs are unique across the whole site.
    - Adding the same SavedAsset twice to one pack leaves a single item.
    - `?mine=1` on the pack API needs sign-in.
    - The status bar's provider status comes from the latest shelf
      outcome, with no extra health checks.
    - A network guard fixture fails any unmocked request.
    - Phase 1 adds regression tests for the console script, so the
      "existing features still work" gate can actually be checked.
- **Sideways:** In one Phase 1 criterion, the agent described a console
  menu exit choice without checking that it exists. The agent removed it
  before finishing.

## 2026-10-30 — Wrote the Axcenity Toolbox PRD

### Prompts
1. `@HANDOFF.md` `/to-prd` also append any conversations from now on
   including this one to PROMPTS.md accoring to source formatting.

### Summary
- **Outcome:** The agent ran the `to-prd` skill on the design in
  `HANDOFF.md` and wrote `prd/axcenity-toolbox.md`. It contains:
  - a problem statement and solution
  - 86 user stories in nine groups, each tagged with its build tier
    (T1 essential, T2 signature)
  - a table tracing every graded requirement to its stories
  - implementation decisions: apps, data model, providers and caching,
    pages, auth, an API endpoint table, visual design, tooling, tests,
    demo data and the build order
  - two explicit acceptance-criteria sections, as the handoff asked: an
    access-rules table covering the website and the API, and the export
    manifest's fields (Option A, locked by a golden-file test)
  - Out of Scope (including the Tier 3 stretch items) and Further Notes

  No app code was written and nothing was committed.
- **Deviations:** None; the user overrode no recommendations and asked no
  follow-up questions. The user asked for this session's prompts to be
  logged as it goes, so this entry was written without the usual
  end-of-session prompt. The design was silent on five points, so the
  agent picked defaults and listed them under Further Notes for review:
  - Discover search is open to signed-out visitors, but saving needs
    sign-in
  - owners can delete their packs
  - private packs return 404 to non-owners
  - the default variant falls back to the first one listed
  - a signed-out API request gets DRF's default 401 or 403
- **Sideways:** No failures. The skill bans code snippets, so the manifest
  contract is written as field tables, not a JSON example.

## 2026-10-30 — Designed Axcenity Toolbox (Django asset catalog and pack creator)

### Prompts
1. `/grill-me` I would like you to build an asset catalog and pack creator
   for a game engine known as Axcenity that I have created using Rust and
   Lua. This will be known simply as Axcenity toolbox, the website features
   a main page allowing users to see packs that have been created by other
   users such as combined textures, hdri, models and sounds. It can also
   offer suggestions on certain assets that can be used on certain
   projects. It must adhere to the following requirements technical and
   business:
   Technical: Django, Django REST Framework (DRF), SQLite, uv, Ruff,
   Tailwind CSS with DaisyUI, HTMX and Pytest
   Business:
   Your project must have one cohesive purpose. The purpose of your app is
   your own decision, but must serve a clear user need, with features that
   work together.
   Users can find items through an external API. Choose an API provider
   with free access sufficient to build and demonstrate your project.
   Users can save selected items to your application. Store enough
   information locally for saved items to remain accessible when the
   external API is unavailable.
   Users can add and edit their own information. This might include notes,
   ratings, status, or progress. Choose information that serves your
   application's purpose.
   Users can browse their saved items on a website. Include search,
   filtering, sorting, and pagination. These features must operate on
   locally saved data.
   Users must sign in to manage their saved data. Decide who can view or
   modify it. You may choose private data, public viewing, or selective
   sharing. Enforce those rules through both the website and the API.
   Your application provides its own API. Support listing, creating,
   updating, and deleting saved entries.
   The application handles unsuccessful external requests. Show a useful
   message when the provider is unavailable or a request fails.
2. B *(a personal library plus packs)*
3. A *(a shared `Asset` table plus a per-user `SavedAsset`)*
4. A *(link to provider thumbnails, with a placeholder icon if one fails)*
5. A *(packs double as project kits; suggestions match tags)*
6. C *(notes, rating and status, plus Axcenity fields `preferred_variant`
   and `import_path`)*
7. A *(a JSON manifest export)*
8. A *(a private library; packs are public or private by choice)*
9. A *(Django's built-in login plus DRF session and token authentication)*
10. For this one I feel like I can make it to where we seperate the asset
    types between textures models sounds and hdris. The sound will only
    pull from openverse and the others will pull from both ambientcg and
    poly haven
11. A *(provider sections that load on their own; no paging on Discover)*
12. A *(move `preferred_variant` and `import_path` to `PackItem`)*
13. C *(the pack builder plus an "Add to pack" dropdown in the library)*
14. A *(the full library search, filter, sort and pagination set through
    one `filter_library()`)*
15. A *(API create takes `provider` + `external_id` and the server fetches
    the rest)*
16. A *(library CRUD; packs read-only plus export in the API)*
17. A - I would also like to make the page look modern and have some cool
    transitions, the actual engine is inspired off of VSCode so make it
    look modern and sleek using Inter fonts. One of the websites I really
    like the design of is ArtCraft at getartcraft.com with its scrolling
    sidebar and fancy animations, if we could have something like that it
    would be cool
18. *(screenshot of the getartcraft.com home page)* A - this is the artcraft
    home for inspiration
19. A - Try to keep it unique with your own desgin inspired from vscode
    while adapting appearance features from the reference I gave you.
20. B *(`seed_demo` loads a committed snapshot of real provider data)*
21. A *(`django-tailwind-cli` with DaisyUI)*
22. A *(`monkeypatch` for app tests, `responses` for provider tests)*
23. A - /prototype I would like you to show me how you plan on laying out
    the searches for assets as I want to make sure that looks good.
    *(A answered Q21: new provider functions next to the old ones)*
24. *(attached the engine's `assets/branding/build.py`, its README and the
    logo images)* I really like the gallery shelves as it seems the most
    like what I am going for, it does look very much like artcraft which I
    am ok with. But I was wondering if we could transform it a bit and add
    a few features that keep the modern asthetic. such as changing the font
    and logo design to include this throughout the project in various
    locations that are animated, watermarked or featured.
25. Lets do monochrome. I also am not sure of the font of my wordmark so
    make a best guess and move onto further grill me questions as needed
26. A *(a `Tag` model with `normalize_tag()`)*
27. B *(deleting a saved asset removes it from packs, after confirmation)*
28. A *(cache successful searches for 1 h and Poly Haven `/info` for 12 h)*
29. A *(copy a public pack, and save single items from it)*
30. A *(apps: `catalog`, `packs`, `accounts`, plus `config` and
    `providers`)*
31. A *(the library drawer with autosave)*
32. A *(a versioned export manifest with `files[]` and `credits`)*
33. Use the tier system you reccomended
34. `/handoff` in the next session you will create the PRD
35. go ahead and append this conversations to PROMPTS.md according to
    source formatting

### Summary
- **Outcome:** A `/grill-me` interview of 29 questions, plus one
  `/prototype` round, produced a complete design for **Axcenity Toolbox**:
  - a Django site where users find assets from ambientCG, Poly Haven and
    Openverse, save them to a private library with notes, rating and status,
    and build tagged packs
  - public pack sharing with a "Copy pack" button, and suggestions by tag
    overlap
  - packs export as a versioned JSON manifest for the user's engine

  The full design is in `HANDOFF.md`, which was rewritten for the next
  session (writing the PRD). The previous console-script handoff is still
  in git at `48548a6`. Other work:
  - **Prototypes:** `prototypes/discover.html` shows three Discover
    layouts. `prototypes/discover-branded.html` is the chosen one: gallery
    shelves with the engine's logo, the `theme.rs` palette, monochrome
    chrome and Plus Jakarta Sans headings.
  - **Memory:** the agent saved a note recording where the engine's
    branding and palette live.
  - No app code was written and nothing was committed.
- **Deviations:**
  - **Personal fields (Q5):** the user chose C (adding engine-specific
    `preferred_variant` and `import_path`) over the recommended A. The
    agent later found that a saved asset can be in several packs with
    different needs, so Q10 moved those fields to `PackItem`.
  - **Discover layout (Q9):** the user replaced the agent's provider picker
    with their own type-first design: Sounds come from Openverse, and
    everything else from ambientCG plus Poly Haven. That raised a new
    question (Q9b) on combining two providers.
  - **Adding to packs (Q11):** the user chose C (both the pack builder and a
    library dropdown) over the recommended A. The agent routed both through
    one `add_to_pack()` function.
  - **Visual direction:** the user asked for a modern VSCode-inspired look
    based on getartcraft.com, and sent a screenshot to show that its
    "scrolling sidebar" is a right-edge scroll ruler. They then asked for a
    prototype, picked "Gallery shelves" out of three variants, and asked
    for their engine's logo and fonts to be woven through it. They chose
    monochrome chrome, and the wordmark font was left to the agent's best
    guess (Plus Jakarta Sans).
  - **Unanswered sub-questions:** the user didn't answer six of them. The
    agent took the recommended default each time and said so:
    - how Axcenity loads assets today (Q6)
    - paging on Discover (none)
    - `pytest-cov` and Ruff as formatter (yes)
    - keeping `asset_search.py` working (yes)
    - copying packs being website-only (yes)
    - `django-htmx` (yes)
- **Sideways:**
  - **ArtCraft fetch:** fetching getartcraft.com returned only page text,
    with no CSS or scripts, so the agent couldn't verify the sidebar or the
    animations and said so. The user's screenshot settled it.
  - **Provider data gaps:** reading `providers/` showed that the
    console-shaped results have no thumbnails, and that Poly Haven's
    `get_details()` throws away download URLs. That led to Q21 (a new
    `AssetRecord` shape). The live snapshot taken for the prototype showed
    that ambientCG has only one "wood" model.
  - **Checking the prototype:** Node isn't installed, so the agent couldn't
    syntax-check the JavaScript. It checked the prototypes by rendering
    them with headless Edge and reading screenshots. That caught:
    - type badges with low contrast against the textures
    - a stray outline around the search box
    - bright borders on the skeleton (loading) cards
    - the prototype panel covering the design
    - a title-bar wordmark that was too small

    All were fixed.
  - **Logo masks:** CSS masks can't load local files from `file://` pages,
    so the logos were downscaled with Pillow (`uv run --with pillow`, not
    added to the project) and embedded as data URIs.
  - **Live requests:** the agent made read-only requests to the three
    providers to capture the prototype's data. The snapshot and the build
    scripts stayed in the session scratchpad, not the repo.

## 2026-10-30 — Built the ambientCG / Poly Haven / Openverse console script

### Prompts
1. `@HANDOFF.md` Setup the script, append any messages to PROMPTS.md
   according to source formatting
2. Ok how do I run the code and test the apis
3. Alright they all seem to be working well including openverse. I would
   like you to walk me throuh the code and tell me how the api request are
   being made, retreived and displayed back to me in the console.
4. Alright looks good can you include this in the docs folder as a md file
   and ensure that all prompts are being recorded in PROMPTS.md

### Summary
- **Outcome:** Built the console script from the design in `HANDOFF.md`.
  - **Scaffold:** `uv init --app --no-package` with Python 3.13 pinned and
    `requests` as the only dependency (`pyproject.toml`, `uv.lock`,
    `.python-version`). The generated `main.py` was removed.
  - **Code:** `asset_search.py` plus `providers/` (`http`, `ambientcg`,
    `polyhaven`, `openverse` and a small `formatting` helper).
  - **Live checks:** each provider was run live for a normal search, an
    empty search (`zzqqxx`), a details view, a bad ID and invalid menu
    input. All passed.
  - **README:** `README.md` now has "How to run" and "How to verify"
    sections, a table of test cases and sample output.
  - **Manual testing:** the user ran the script and confirmed that all
    three providers work, including Openverse.
  - **Walkthrough:** the agent explained how requests are built, sent,
    parsed and printed, following one Poly Haven search from start to
    finish. That explanation was saved as `docs/code-walkthrough.md`.
  - Nothing was committed.
- **Deviations:** The user overrode no recommendations. Prompts 2 and 3
  were follow-up questions about running the script and how the code
  works. The agent made these changes to the handoff design:
  - **New module:** added `providers/formatting.py` (sizes and `m:ss`
    durations), which the handoff's file list didn't include. Both the
    providers and the script use it, and putting it in
    `providers/__init__.py` would have caused a circular import.
  - **ID lookup:** added an "ID lookup (i)" choice next to search. The
    assignment allows "a search phrase or item ID" as input, and the
    planned bad-ID check needs a way to type an ID.
  - **Bundles:** Poly Haven details list every bundle the API returns
    (`blend`, `gltf`, `fbx`, `usd`, `mtlx`), not only `blend` and `gltf`.
  - **ambientCG type:** the agent found that `include=type` returns the
    asset type, which fills the Type column.
- **Sideways:**
  - **Wrong scaffold:** `uv init --app` (uv 0.12.19) produced a packaged
    `src/` layout with a build system, not the flat layout the design
    requires. The agent deleted those generated files and re-ran it with
    `--no-package`.
  - **Encoding crash:** the first Poly Haven HDRI details run crashed with
    `UnicodeEncodeError`. A description contained U+2011, which the cp1252
    code page Windows uses for piped output can't encode. Fixed with
    `sys.stdout.reconfigure(errors="replace")`.
  - **Menu input:** `str.isdigit()` accepts characters such as `²` that
    `int()` rejects, so the agent switched the menu checks to `isdecimal()`
    and tested `²` input.
  - **Openverse slowness:** Openverse was degraded during testing.
    Uncached searches took 30–60 s, and some returned HTTP 500. The 10 s
    timeout fired and showed its error message. That checked the timeout
    path but blocked the normal check. To verify the list and details
    display, the agent did one run with the timeout raised to 90 s through
    a one-off override. The code still uses 10 s, and the README notes the
    slowness.
  - **Bad-ID response changed:** an Openverse bad ID now returns 404 (JSON
    for a well-formed UUID, HTML otherwise), not the 500 HTML page recorded
    in the handoff. Both cases end in the same friendly error.

## 2026-10-30 — Designed the ambientCG / Poly Haven / Openverse console script

### Prompts
1. `/grill-me` I would like for you to setup a short console script that
   makes a real API request to these providers, ambientCG, Poly Haven and
   Openverse Audio. This must be verifiable in a Python script and must:
   Accept user input, such as a search phrase or item identifier. Make a
   meaningful request to the external API. Use your own credentials if the
   provider requires them. Display selected results clearly in the console.
   Handle unsuccessful requests and empty results with useful messages.
   This folder/repository does not have an environment yet and will soon
   belong a django project that will us uv, you should setup this project
   with uv in mind do not set it up with another package manager. Since this
   is for a game asset collection and management center some useful
   information my be texture information, names size file format or
   anything you deem as useful.
2. C *(one script plus a `providers/` package)*
3. A *(`uv init --app` at the repo root, flat layout)*
4. Just use Django REST Framework (DRF) *(answering which HTTP library to
   use)*
5. A *(`requests` now; Django and DRF later)*
6. A *(interactive `input()` prompts)*
7. B *(search list, then a details view for one result)*
8. A *(Poly Haven `/search` + `/info`; `keywordMatches == 0` means empty)*
9. A *(same list columns for every provider; Poly Haven files summarized
   per resolution)*
10. A *(shared `get_json()` helper that raises one `ProviderError`)*
11. A *(anonymous access, no credentials)*
12. A *(manual verification only)*
13. B *(5 results plus an optional asset-type filter)*
14. `/handoff` We will continue to build the script in the next session,
    please append this current conversation to PROMPTS.md according to
    source formatting.

### Summary
- **Outcome:** A `/grill-me` interview settled 11 design decisions for the
  console script. The full agreed design and the API facts confirmed live
  are recorded in `HANDOFF.md`. In short:
  - The layout is `asset_search.py` plus `providers/` (`http`, `ambientcg`,
    `polyhaven`, `openverse`), set up with `uv init --app`, Python 3.13 and
    `requests`.
  - The script uses interactive prompts and shows a list, then details for
    one result.
  - Errors go through a single `ProviderError`, and all three providers are
    used anonymously.
  - No code was written and nothing was committed. Building the script is
    the next session's work.
- **Deviations:**
  - **HTTP library:** asked which library to use, the user answered "just
    use DRF". The agent explained that DRF builds APIs rather than calling
    them, and the user then chose `requests`, with Django and DRF to be
    added later.
  - **Verification:** the agent recommended a pytest suite with faked
    responses. The user chose manual verification instead.
  - **Unanswered sub-questions:** the user didn't answer whether to pin
    Python 3.13 or whether to loop after each search. The agent took the
    recommended default (yes) for both.
- **Sideways:** Partway through the interview, the agent made live
  read-only requests to check its assumptions and found two surprises:
  - Poly Haven's semantic `/search` never comes back empty (`zzqqxx`
    returned 814 hits) and returns only slugs, without names. That led to an
    extra question on how to detect empty results.
  - Openverse returns a 500 HTML page, not a 404, for a bad audio ID, so the
    error handling must cope with a body that isn't JSON.

  Sample responses were saved to the session scratchpad, not to the repo.

## 2026-10-30 — Researched free CC0/CC-BY game-asset APIs for the Django app

### Prompts
1. `/research` I would like you to research and find free APIs for a Django
   application that I am building. This application features a common
   library for game assets that are considered publicly usable such as CCO
   or Attribution related assets. The assets should contain items such as
   textures, sounds, 3D models, HDRIs etc. Compare these providers and use
   multiple if neccesary using official documentation, including available
   data, usage limitations and signup requirements.
2. Go ahead and append the prompt history to PROMPTS.md according to source
   formatting

### Summary
- **Outcome:** A background research agent compared 15 providers against
  their official docs and made live, keyless requests to 13 of them. The
  report is saved at `docs/research/game-asset-apis.md`, with a comparison
  table, a section per provider, a recommended combination and an open
  questions list. Recommendation: start with no signup by using Poly Haven
  and ambientCG (CC0 textures, HDRIs and models) and Openverse (CC audio with
  per-asset attribution), then add Freesound, Sketchfab and Wikimedia Commons
  later. OpenGameArt and Kenney have no API, Pixabay's license isn't
  Creative Commons, and Jamendo's API is non-commercial only. Nothing has
  been committed yet.
- **Deviations:** None. No recommendations were overridden and no follow-up
  questions were asked. The repo had no notes folder, so the agent chose
  `docs/research/` as the location.
- **Sideways:** The agent briefly wrote scratch files to the repo root while
  working and deleted them before finishing; `git status` showed only
  `docs/` afterward. Several primary sources couldn't be reached, so their
  claims are marked unverified in the report: Sketchfab's API agreement
  pages loaded empty, Smithsonian's open-access and terms pages returned
  403, and Internet Archive's search endpoint returned a backend error.