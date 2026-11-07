# Frontend

Read this before changing templates, styles, branding or HTMX. The visual
reference is [prototypes/discover-branded.html](../prototypes/discover-branded.html).
It's a throwaway prototype, so take its look, not its code.

## Tailwind + DaisyUI (no Node)

- django-tailwind-cli downloads a standalone Tailwind binary with DaisyUI
  built in (`TAILWIND_CLI_USE_DAISY_UI = True`) into `.django_tailwind_cli/`.
  The folder is git-ignored.
- The source is `styles/source.css`. It sits outside `STATICFILES_DIRS`, as
  the library requires. The build writes `static/css/tailwind.css`, which is
  also git-ignored.
- `uv run python manage.py tailwind runserver` runs Django and the watcher.
  `tailwind build` makes a one-off minified build.
- Tailwind finds classes by scanning the project's files. A class built from
  string pieces at runtime won't be found, so write class names out in full.

## Colour

- `@theme { --color-*: initial; }` drops Tailwind's palette, and
  `@plugin "daisyui" { themes: false; }` drops DaisyUI's themes. The only
  theme is `axcenity`, set on `<html data-theme="axcenity">`.
- The utility colours come from the editor's palette: `app`, `panel`,
  `surface`, `elevated`, `inset`, `control`, `control-hover`,
  `control-active`, `line`, `line-strong`, `fg`, `fg-strong`,
  `fg-secondary`, `fg-weak` and `fg-muted`. `white` and `black` are also
  defined, but the chrome doesn't use them directly (see contrast tokens).
- **Light and dark:** System (follow the computer), Light or Dark, chosen
  by hand (user request, 2026-11-05).
  - **The choice** is the `ax-theme` cookie (`accounts/theme.py`), for
    visitors and members alike, so the server renders `<html
    data-scheme-choice="…">` and, for Light or Dark, `data-scheme="…"` on
    the first paint. For System, an inline `<head>` script sets
    `data-scheme` from `matchMedia("(prefers-color-scheme: light)")` before
    first paint and follows the computer live. Without JavaScript, System is
    dark.
  - **Setting it:** the title bar's switch (`#theme-toggle`, a monitor, sun
    or moon for the current choice) steps System → Light → Dark, and the
    Settings page's Appearance chips pick one. `shell.js` switches at once,
    writes the cookie (a year, `SameSite=Lax`) and keeps every switch and
    chip in step. Both are forms that POST `choice` to `accounts:theme`
    (CSRF) when JavaScript is off; it sets the cookie and goes back to the
    page (the Referer, if it's this site).
  - Dark is the default: the `@theme` values.
  - `html[data-scheme="light"] { … }` in `source.css` (nested rules, which
    Tailwind's build flattens) sets the same tokens to a **light storm
    grey** (user request, 2026-11-06). It started as the engine's light
    palette (`crates/editor/src/theme.rs`, `Palette::new` with `dark =
    false`), which the user found too bright. Now the surfaces are a cool
    mid grey (app `#BEC0C2`, panel `#CACCCE`, surface `#D3D5D7`), and the
    text, lines and status colours are darker to keep their contrast: body
    text 10:1 and secondary 6.6:1 on the panel, and every text and status
    colour at least 4.5:1 even on the darker bars (`test_theme.py` checks
    it). `shade` is a deep storm grey (`#2B2D31`), so shadows and dialog
    backdrops darken rather than glow white; the footer's brand signature
    takes a panel-coloured halo instead. It's still the one `axcenity`
    theme, just flipped, so every utility and component follows.
  - In light mode, the type colours become the engine's on-light accents
    (`#A8460B`, `#3451D1`, `#1C7547`, `#6741D9`), which only ever mark
    icons and keep over 3:1 on the grey.
  - The ambient glow's blobs switch from `screen` to `multiply` blending,
    and the layer drops to 22 % (30 % on showcase pages), because screen
    washes out on white.
  - The title-bar wordmark image (white) is inverted through
    `--logo-filter`.
- **Contrast tokens:** `ink`, `on-ink` and `shade`.
  - `ink` is white on dark and `#18181B` on light. Hover inversion,
    current-page marks, tooltips and the marks use it.
  - `on-ink` is what sits on ink.
  - `shade` sits behind text over the glow.
  - Never use `white` or `black` for chrome. `test_shell.py` allows white
    only in highlight `radial-gradient`s, which read on both backgrounds.
    The dot grid reads `--grid-dot`, which is ink at 4 % (7 % in light).
- DaisyUI roles:
  - `primary` is white (`#FAFAFA`) with dark text in dark mode, and
    near-black (`#18181B`) with white text in light mode. Use
    `btn btn-primary` for the main action.
  - `success`, `warning` and `error` are the editor's status colours.
  - `info` is grey, so it can't be mistaken for the HDRI blue.
- **Type colours** are `texture`, `hdri`, `model` and `sound` (for example
  `text-texture`). Use them only to show an asset's type. Tailwind emits
  only the tokens that are used. Each has a dark and a light value. So far
  they appear in four places:
  - Discover's type tiles (the icon and the bar under the current tile)
  - a result's fallback type icon, inside the shelf fragments
  - a library card's type icon (`.library-type-icon`) and fallback icon
  - the same two icons in the library drawer and on an entry's page
  - the same two icons on each item in the pack builder (Phase 7) and on
    a pack's page (Phase 8), and on each row of Add from my library
    (2026-11-05)
  - each gallery card's mosaic tiles on the main page: the asset's type
    icon under its thumbnail (Phase 9)
  - the main page's orbit hero (Phase 12; textures only): each ring's
    line (`border-texture`) and each tile's texture icon (never the grey
    guide rings)

  `test_shell.py` keeps them out of the chrome on every page, out of every
  other page's own content (on the main page, out of everything but the
  orbit), and on library cards and pack items to those two icons only.
- **Page drop colours (the one exception):** each page's content area has
  an ambient glow in three vivid colours, drifting behind the whole page
  (see "Ambient glow"). The colours are chosen by `#content[data-drop="<active_nav>"]` in
  `source.css` (`<main id="content" data-drop>`). These are decoration
  only. They appear in those rules and nowhere else, never in the bars or
  the side panel, and never match a type colour. This exception to the PRD's "colour only means asset
  type" rule was asked for by the user on 2026-10-30. They started as
  pastels, and the user asked for brighter ones the same day (the tests
  still call them `PAGE_PASTELS`).
- `tests/test_theme.py` fails if `source.css` gains any colour outside this
  palette (dark or light), or uses a drop colour outside the
  `#content[data-drop]` rules. `static/js/ambient.js` only ever names the
  tokens (`var(--drop-a)`…), never a hex value. It also checks the light block's storm-grey values and their contrast.

## Fonts

All fonts are served from `static/fonts/`, never from a CDN. Their sources,
pins and licences are recorded in
[static/fonts/SOURCES.md](../static/fonts/SOURCES.md).

| Use | Family | How |
|---|---|---|
| Body | Inter | Default (`font-sans`) |
| Page headlines | Plus Jakarta Sans 700, `-0.025em`, balanced | `.headline` (used by `page_header.html`) |
| Other display text | Plus Jakarta Sans 800 | `.display`, or `--font-display` to swap it |
| Micro-labels | JetBrains Mono, uppercase | `.micro` |

**No late font swap:** `base.html` preloads JetBrains Mono Regular, Inter
Regular and Medium, and Plus Jakarta Sans, so they download alongside the
stylesheet. JetBrains Mono and Plus Jakarta Sans use `font-display:
block`, not `swap`, so the title bar and headlines never paint in a
fallback font and then jump. With `swap`, the mono labels changed width as
the real font arrived. Inter still swaps, because system-ui is a close
match.

**Font gate (first load only):** a fresh document can still paint before
its fonts arrive. The title-bar chips would then show their fill and
white current-page underline with no text: a stray white bar. An inline
`<head>` script sets `<html data-fonts="loading">` until JetBrains Mono is
ready (capped at 3 s), and CSS hides the chips whole meanwhile. Boosted
navigation (see HTMX) keeps the fonts loaded after the first page, so
this only matters on a full load or refresh.

## Branding

- The logo files in `static/brand/` are copied from the engine repo's
  `assets/branding/`. The identity is black, white and grey only.
- **Wordmark:** `wordmark-white.png` in the title bar, and a small `w-20`
  `.word` in the footer's brand signature. The giant full-width footer
  watermark was removed at the user's request (2026-11-05): they wanted it
  in view rather than at the foot of the page, or gone if that wasn't
  clean. Pinned to the bottom of the view it was cut off behind the content
  on long pages, so it went. The top-right mark (`.hero-mark`) carries the
  logo on every page.
- **App icon tile:** `icon-256.png` stays in static, but no page uses it.
  The user removed it from the activity bar because the title-bar wordmark
  already links home.
- **Favicon:** `favicon-32.png`.
- `.mark` and `.word` are CSS masks, so the logo takes `currentColor`. The
  image URLs come from `{% static %}` through `--mark-url` and `--word-url`
  on `<html>`.
- The ghost mark is the empty state in `partials/empty_state.html`.
- **Section icons** (user requests, 2026-11-06): each section's sidebar
  icon as a line drawing (`catalog/templatetags/shell_tags.py`:
  `PAGE_ICONS` and the `page_icon` filter on `active_nav`): Discover a
  magnifier, Library the books, Packs the box, Attribution the license,
  Account the person, Settings the gear. The main page has none (its orbit
  fills the cover).
  - **In the header:** `.page-hero-glyph`, the header's left column (8.5
    rem, 6.5 rem compact, 4 rem on a phone): the icon in `fg-secondary`
    with 1-of-24 strokes, in a square `line-strong` frame on a 3 % ink fill,
    with ink corner ticks top left and bottom right. The user first had it
    as a faint background watermark behind the header, then asked for it
    beside the text instead.
  - **In the sidebar:** `.side-watermark`, the same icon at 13 rem in the
    open sidebar's bottom right corner above the Account rows, only a little
    of it past the edge (2.25 rem), 6 % ink (8 % in light mode), under
    the rows (`z-index: -1` in the aside's stacking context; it clips
    itself, so the tooltips still stick out). It fades out when the sidebar
    collapses. The user liked it in the corner, first cropped by 4.5 rem,
    then centred whole, and settled on the corner with enough of it in view
    to read.
  - Both draw themselves in each time a page arrives (`watermark-draw`, 2
    s, a dash offset). Monochrome only, never a type colour, never on a
    provider's thumbnail.
- "In library" used to be a badge with a small `.mark` in a Save row at the
  card's foot. Since the Phase 4 polish (2026-11-05) Save lives in the
  card's top-right corner, over the thumbnail, so "In library" is a filled
  check there and carries **no** mark (the logo never sits on a provider's
  image).
- **Never** put the logo on a provider thumbnail.

## The shell (`templates/base.html`)

| Part | id | Notes |
|---|---|---|
| Title bar | `title-bar` | `h-12`. From the left: the wordmark (`h-8`, links home), a divider, **Home** (`#home-button`, the only Home chip), "TOOLBOX", the breadcrumb, then the account chips on the right. Every item is a square `h-8` chip (`.bar-item`, `.crumb`) with 16 px icons. The breadcrumb sits in `{% block breadcrumb_nav %}`. Home empties that block, because its Home chip already marks the page. Sign-out is a POST form |
| Sidebar | `side-panel` (with `activity-bar` inside) | One column: the activity bar and the side panel merged (user request, 2026-11-05). From the top: an `h-14` slot with the panel toggle and `{% block panel_title %}` (`.sidebar-title`, "Explorer" by default); `nav#activity-bar` with Discover, Library, Packs and Attribution (`pt-1`, `gap-1`); the page's own panel (`.side-panel-inner`, `{% block side_panel %}`: the Library filters, the Account pages' Profile, Settings and API token rows); and an Account nav at the foot with Account and Settings. Each entry is an `.act.act-row` (`h-11`): a 3.5 rem `.act-icon` cell holding its 20 px icon, its `.act-label`, and a `.tip` tooltip for the collapsed strip, instead of a `title`. The sidebar is `relative z-20` so tooltips sit over the content. A view sets `extra_context = {"active_nav": "<key>"}` to mark its entry with `aria-current="page"` |
| Content | `content` | `data-drop` = the page's `active_nav`. `.content-stage` holds the ambient glow, the mark, then `{% block content %}` in a `px-8 lg:px-12 pt-14 pb-12 space-y-8` wrapper, then the footer (`page-footer`): the `.brand-signature` row ("Built for Axcenity Engine", a small wordmark, "Axcenity Studios · 2026") |
| Status bar | `status-bar` | Monochrome. Each provider's last known status (`partials/provider_status.html`, from `config.context_processors.shell`): a solid ink dot for OK, an alert icon for an error, a muted dot for unknown, with the words in `title` and screen-reader text. The saved count (`partials/saved_count.html`, `#saved-count`) appears only when signed in, counts only that member's entries, and is sent again out of band after each save |

**Side panel collapse:** an inline script in `<head>` sets
`<html data-panel="open|collapsed">` before first paint, from
`localStorage["ax-panel"]`. Phone-width screens default to collapsed.
`static/js/shell.js` wires the `#panel-toggle` button and keeps
`aria-expanded` in step. The toggle holds two icons (`.when-open` and
`.when-collapsed`), and CSS shows whichever fits the state.

**Side panel animation:** the sidebar is 16 rem open and the 3.5 rem icon
strip collapsed. The icon cell is 3.5 rem in both states, so the icons
never move.
- **Collapsing** animates the width over 0.42 s on a smooth ease-out curve.
  The labels and the title fade at once, and the page's panel fades and
  drifts left, then becomes `visibility: hidden`, so its links leave the
  tab order.
- **Expanding** is gentler. The width eases out over 0.5 s, the labels
  slide in on a 0.1 to 0.2 s stagger (`--row-delay`), and the page's panel
  fades in 0.15 s later.
- **Clipping:** nothing on the `<aside>` clips, because the tooltips sit
  outside it. Each label clips itself (`overflow: hidden`) as the width
  changes.
- **Tooltips** show only while collapsed, since the labels name the icons
  when it's open.

`shell.js` sets `data-panel-ready` after the first frame, so the transition
never plays on page load. Reduced motion turns it off. The first version
had two columns: the icon bar, plus a panel that repeated Discover, Library
and Packs as text rows. The user asked for one column with each icon
beside its label (2026-11-05).

**Hover is an inversion:** dark chrome (activity bar entries, the panel
toggle, side-panel rows, title-bar chips) turns white with black content.
The wordmark chip inverts its image to black. White buttons
(`btn-primary`) turn black with white text and a white edge, and plain
`btn`s turn white. The `.btn` rules sit outside any layer so they beat
DaisyUI's own hover tint. Don't put a text-colour utility on a chip: it
outranks the hover colour. Use a component class like `.bar-item-app`.

**Hover gate:** the chrome's `:hover` rules (activity bar, tooltips,
side-panel rows, title-bar chips, label-to-icon swaps, the wordmark chip)
are prefixed `html[data-pointer]`. `shell.js` sets that attribute only once
the pointer really moves (more than 4 px) on the current page.

Without the gate, a click loads the next page under a cursor that hasn't
moved, and the browser re-applies hover to whatever is now under it. A
chip flipped to its icon and turned white, or a tooltip slid out, the
moment the page appeared. The user reported this as a top-bar "glitch".
Keyboard `:focus-visible` isn't gated. Put any new chrome hover rule behind
the gate too. With boosted navigation, the gate is re-armed after every
swap (`htmx:afterSwap` in `shell.js`).

**Current page:** marked the same way in the sidebar and the title bar.
The sidebar entry gets white text, a slightly lighter fill, a 2 px white
bar on the left edge and a semibold label. So does a page's own
`.panel-row` (the Account pages' Profile and Settings). The title-bar chip
(the crumb, or Home on the home page) gets white text, a fill and a 2 px
white underline (`inset` box shadow).

**Tooltips:** each sidebar entry holds a `<span class="tip"
aria-hidden="true">`, a white mono label that slides out to the right after
0.2 s, while the sidebar is collapsed. The link's `aria-label` stays the accessible name. `shell.js` swaps
the toggle's tip between "Collapse panel" and "Expand panel".

**Square corners:** title-bar chips, the Sign-up button (`rounded-none`),
the panel toggle, the home hero search and its `.btn-quiet` actions are
square, for the geometric look the user asked
for. Don't add `rounded-*` to the chrome.

**Label-to-icon swap:** "HOME", "TOOLBOX" and every breadcrumb are
`.chip-swap` chips holding a `.chip-label` and a `.chip-icon`. Both sit in
one grid cell, so the chip keeps the label's width. On hover or focus the
label fades up and out and the icon rises into its place. Page templates
build crumbs with `partials/crumb.html` (`href`, `label`, `icon`,
`current`).

**Title-bar alignment:** JetBrains Mono caps sit about 2 px above the
wordmark's letters at `line-height: 1`. A 4 px `padding-top` on the chip
text (not the icons) puts every label on the wordmark's centre line.
Wrap chip text in a `<span>` so the padding applies.

**Ambient glow** (user request, 2026-11-05): the old glow was three
blobs on fixed paths with concentric ripple rings, behind the hero and in
the footer, and the user found it too regular and symmetrical. Now one
layer runs through the whole page, fluid, random and subtle. Later the
same day the user asked for big water drops, then for bigger, looser and
faster ones, like a lava lamp:

- **Where:** `<div class="ambient" data-ambient>` is the first child of
  `.content-stage`, a wrapper inside `#content` that grows with the content
  (`flex: 1 0 auto`). So the layer spans the page from the top to the end of
  the footer, however long it is, and scrolls with it. `#content` clips it.
- **What:** `static/js/ambient.js` places the drops on load and after each
  swap (`htmx.onLoad`): one per 650 px band of page, at a random height in
  the band (a second in some bands on wide screens), up to 22. Each is 620
  to 1300 px across, with its own loose, uneven shape, a two-colour
  gradient from the page's drop tokens with its light off-centre (`--hx`,
  `--hy`), aspect, blur, opacity, three drift waypoints (180–480 px up or
  down, a little sideways), wobble, speeds (18–34 s to rise or fall, 5–9 s
  wobble) and a random starting point in its cycle, so nothing moves in
  step. A page that grows (Load
  more, a filter) gets drops for the new part (`ResizeObserver`), and the
  old ones stay put. Every page load rolls a new arrangement.
- **How it moves, like lava-lamp wax:** only transforms animate.
  `.ambient-blob` rises and falls between its waypoints (`ambient-drift`),
  pulling tall and thin while it travels (`--thin`, `--tall`) and squashing
  wide as it turns (`--flat`, `--squat`). Inside
  it, the drop's body (`.ambient-drop`) wobbles (`ambient-wobble`): it
  stretches one way as it squashes the other (`--wa` and `--wb = 2 - --wa`,
  so it keeps its volume, as water does) and turns a little. Two thin
  shells (`.ambient-shell`) wobble the same way 0.5 s and 1 s behind, like
  the layered edges of a drop settling, as in the user's reference image.
- **How strong:** 34 % on work pages (and 1.15× slower), 52 % on showcase pages,
  24 % and 32 % in light mode, where the drops multiply instead of screen.
  Reduced motion keeps the arrangement, still. Without JavaScript there's no
  glow, only the dot grid.

`.brand-signature` has a dark drop shadow so it stays readable over the
brightest ink. The layer is translucent, so the dot grid shows through.
`.grid-bg` uses `background-attachment: local`, so the dots scroll with
the content.

**Nothing sticks out of the window** (user report, 2026-11-05): the page
used to scroll on past the shell into empty space. Each `.filter-chip`
hides its input with `sr-only`, which is absolutely positioned. The chips
weren't positioned, so those inputs were placed against the sidebar,
which deliberately doesn't clip (its tooltips stick out). A long Tags list
pushed hidden inputs below the window, and the document grew by that
much. `.filter-chip` is `position: relative` now, so each input sits in
its chip, inside the panel that scrolls and clips. Anything absolutely
positioned in the side panel needs a positioned parent inside it.

**Partials:**

- `partials/page_header.html` takes `label`, `heading`, `lead` and
  `compact`. On a section page it's two columns (`.page-hero.has-glyph`):
  the section's icon (`.page-hero-glyph`, see "Section icons"), then
  `.page-hero-text`. The text is a kicker row (the small mark, the
  micro-label and a `.page-hero-rule` hairline running out to the content's
  right edge and fading; none on the main page), a `.headline`
  (`text-[2.25rem]`, `md:text-[2.75rem]`) and a 15 px lead, `space-y-4`.
  Working pages pass `compact=True`, which gives a `md:text-[2rem]`
  headline, a 14 px lead and `space-y-3`. The block spans the content's
  width so the rule can; the headline keeps `max-w-3xl` (`max-w-2xl`
  compact) and the lead `max-w-xl`.
- `partials/empty_state.html` takes `title`, `body`, `link_url` and
  `link_text`. It's a solid `bg-surface` panel with a `border-line-strong`
  border and `py-16`. The first version had a dashed outline that was hard
  to tell from the background.
- `partials/form_fields.html` renders a form's errors and fields:
  - Form-wide errors (a wrong username or password) show first as a
    `#form-errors` `.form-alert` with `role="alert"` and an icon.
  - Each field's errors sit right under it in a
    `<ul id="<auto_id>_error" class="field-errors">`. That id matches the
    `aria-describedby` that Django puts on an invalid input, alongside
    `aria-invalid="true"`. Help text gets `<auto_id>_helptext` the same
    way.
  - Password inputs are wrapped in `.password-field` with a
    `.password-toggle` show/hide button (`static/js/password-toggle.js`,
    which keeps `aria-pressed` and its label in step).
  - Pass `forgot_url` to put "Forgot password?" beside the `password`
    label.
- `partials/icon.html` takes `name` and `size`.
- **Side-panel rows** (user request, 2026-11-06): every `.panel-row` starts
  with a 16 px `.panel-row-icon` (muted, strong when current, inverted with
  the row on hover): Account pages (user, gear, key), Attribution center
  (license, pack, library), each pack (pack), and "On this page". A row may
  end in a `.panel-row-count`. A group of rows can fold: `<details
  class="panel-fold" data-remember="…">` with a `.panel-row` summary and a
  `.panel-fold-chevron`, its rows (`.panel-fold-rows`) shorter and indented.
  Each `.filter-group` label (`.filter-group-title`) has a 13 px icon too
  (`FilterGroup.icon`: type shapes, provider globe, status check, rating
  star, tags tag, license, commercial use), as does each panel's "Filters"
  title. `test_every_side_panel_row_has_an_icon` checks the rows.
- `partials/crumb.html` is a breadcrumb chip that swaps to an icon on
  hover. It takes `href`, `label`, `icon` and `current`.
- `partials/auth_brand.html` is the branding panel to the right of the
  sign-in and sign-up forms, on wide screens only. It has the wordmark,
  "Your assets. Your projects. / Your Axcenity.", a line on what the
  Toolbox does, and a "Toolbox" micro-label, over a monochrome radial glow.

Auth forms get the DaisyUI `input` class from `accounts.forms.StyledFieldsMixin`.
`.input` is square, on the inset colour, with a subtle focus ring (a light
border plus a 3 px, 12 % white glow) in place of DaisyUI's offset outline.
An `aria-invalid` input has a red edge and a red-tinted ring.

## HTMX

- `{% htmx_script %}` from django-htmx loads htmx 2. `HtmxMiddleware` sets
  `request.htmx`.
- **Boosted navigation:** `<body hx-boost="true">`. Links and forms fetch
  the next page in the background and swap its body in, so the document,
  stylesheet, fonts and scripts stay loaded.
  - The user asked for this after full page reloads made the top bar
    flash. Rebuilding the whole document on every click is what caused
    those flashes.
  - After a redirect, htmx puts the final URL in the address bar, so
    sign-in and sign-out land on the right page.
- **The htmx-config meta:**
  - `historyCacheSize: 0`: Back refetches the page instead of restoring a
    stale snapshot.
  - Errors swap in: `[45]..` is set to `swap: true`, so a 404 or a 403
    shows instead of the click silently doing nothing.
- **Fragments versus pages:** a boosted request also carries `HX-Request`.
  A view that returns a fragment for HTMX must check
  `request.htmx and not request.htmx.boosted`, otherwise boosted
  navigation would get a fragment instead of a page. Discover's shelves
  are the first fragments (see "Discover" below). The library also skips
  `request.htmx.history_restore_request`, because Back after a swap
  refetches the URL and needs the whole page (see "Library layout").
- **CSRF:** `<div id="app" hx-headers='{"X-CSRFToken": "…"}'>` sends the
  token with every HTMX request. It sits on `#app`, not `<body>`, because
  a swap replaces `#app` but keeps `<body>`. Django rotates the token at
  sign-in, so the header has to come from the newest page. Never exempt a
  view from CSRF.
- **Versioned URLs:** the stylesheet and every script load through
  `{% versioned_static %}` (`catalog/templatetags/shell_tags.py`), which adds
  `?v=<the file's last change>`. A member once clicked the new light/dark
  chips while their browser still ran the old cached `shell.js`, and nothing
  happened (2026-11-05). Now every change is a new URL.
- **A newer version loads the page in full** (user report, 2026-11-06): a
  boosted swap replaces only `<body>`, so a tab kept the stylesheet and
  scripts it first loaded, and a style fix (centred pack thumbnails) looked
  unfixed until a hard reload. On `htmx:beforeSwap`, `shell.js` compares the
  `?v=` URLs in the arriving page's `<head>` with the loaded ones; for a GET
  that names different ones it cancels the swap and loads the URL in full.
- **Scripts:** every script loads once, in `base.html`'s `<head>`, for
  every page. A swap doesn't run a new page's `<head>`, so there's no
  per-page scripts block. Scripts listen on the `document` (delegation)
  rather than binding to elements a swap replaces, as `shell.js`,
  `password-toggle.js`, `sound-preview.js`, `card-actions.js`,
  `entry-drawer.js`, `entry-files.js`, `bundle-download.js`, `pack-sort.js`, `scroll-ruler.js`, `ambient.js`
  and `motion.js` do (`ambient.js` sets itself up through `htmx.onLoad`).
- **Preserved:** the title-bar logo link (`#brand-link`) is
  `hx-preserve`, so it isn't rebuilt on each swap. A rebuilt image left a
  blank frame with the chips sliding left. Its `<img>` also has
  `width`/`height`, so it holds its space on first load.

## Page transitions

Boosted swaps run through the View Transitions API: `globalViewTransitions`
in the htmx config.

- **Content:** `#content` (`view-transition-name: content`) fades up and
  out over 0.16 s, then the new page rises in over 0.34 s.
- **Rest of the page:** a short 0.18 s crossfade.
- **Current-page marks:** each bar's current item has a shared name:
  `current-act` in the sidebar, `current-row` for a page's own panel row, and
  `current-chip` for the title-bar crumb or Home. The mark glides from
  the old item to the new one over 0.32 s.
- **One name per page:** a name used twice on a page cancels the whole
  transition. Only one item per bar may be `aria-current`, and
  `test_each_transition_name_is_used_once_per_page` checks it.
- **Fallbacks:** browsers without View Transitions just swap, and reduced
  motion turns every transition animation off. The user asked for this on
  2026-10-31, ahead of Phase 13, which lists "View Transitions on HTMX
  swaps".
- **Fragment swaps** (Phase 13): every other htmx swap (a filter, Load more,
  a builder save) ran the same drop and rise, so the whole page lifted for a
  small change. `motion.js` marks each swap on `htmx:beforeTransition`:
  boosted navigation clears `<html data-swap>`, anything else sets it to
  `fragment`, and then `#content` crossfades in place over 0.2 s (opacity
  only). Whatever didn't change is the same in both images, so only what
  changed visibly changes. Swaps that say `transition:false` (the drawers,
  the pickers, the builder) still skip it.

## Motion

*(Phase 13, stories 77 and 79.)* The branding's motion, in `source.css`'s
"Motion" section plus `static/js/motion.js`, which only marks state for the
CSS. Monochrome throughout: ink and the grey tokens, never a type or drop
colour.

- **Wordmark:** it wipes in from the left on load (`brand-wipe`, a
  `clip-path` on `#brand-link`). Every 12 s, starting at 3 s, the letters
  dim to 60 % (`brand-dim` on the image) while an ink band crosses them
  (`.brand-shine`, a layer masked to the wordmark through `--word-url`). At
  rest the band waits outside the mask. The shine is hidden while the chip
  is hovered or focused, because the chip inverts.
- **The mark cuts in:** the page's faint mark (`.hero-mark`) is revealed
  diagonally on load (`mark-cut`). The PRD's icon tile left the activity bar
  at the user's request, so the mark stands in for it.
- **Full loads only:** both intros match `html:not([data-booted])`;
  `motion.js` sets `data-booted` after 1.6 s, so a boosted swap never
  replays them (some browsers re-insert the preserved logo, which restarts
  its animations).
- **Parallax watermark:** the mark's layer (`.hero-atmosphere`) sinks at 0.4×
  the scroll over the first 60 rem (a scroll-driven animation on `#content`'s
  `--page` timeline), so it drifts behind the content. It sits in `@supports
  (animation-timeline: scroll())`, so other browsers show the mark still. The
  PRD's giant wordmark stays gone (story 104).
  - **It never stretches the page** (user report, 2026-11-06): the sinking
    layer used to add scroll height, so each scroll to the bottom sank it
    further and left blank space under the footer. `.content-stage` is
    `overflow-y: clip` now, so nothing reaches past the footer.
  - **No hard edge on the main page:** there the layer sits below the hero,
    mid-page, so its top edge was in view and cut the mark off in a straight
    line. On that page the layer fades in at the top as well as out at the
    bottom, and the mark sits 4 rem into it.
- **The logo loader** (`partials/loader.html`, `.ax-loader`): the mark in
  grey with a light band sweeping across it (`--loader-band`, `loader-sweep`),
  with a label or a screen-reader "Loading". It carries no role; the region
  that's loading says so. It's the only loading indicator, and there are no
  spinners.
  - **Everywhere:** the status bar's mark (`#status-loader .status-mark`)
    sweeps while any htmx request runs, boosted navigation included.
    `motion.js` counts from `htmx:beforeSend` to the request's own
    `loadend`, shows it after 150 ms (`<html data-busy>`) and sets
    `aria-busy` on `#content`.
  - **A pending shelf** (user request, 2026-11-06, from the prototype): six
    skeleton cards (`.result-skeleton`: a thumbnail block and two lines,
    fading 10 % per card along the row) under `.shelf-loading-badge`, a
    square frosted box centred over them with the loader at 2.5 rem over a
    mono "Searching <provider>". The badge sits beside the `<ul>`, never on
    a tile, and is `aria-hidden` (the shelf is `aria-busy`).
  - **In place:** a pending shelf's "Searching", Load more's "Loading…", the
    pack picker's "Loading your packs…" (`card-actions.js`) and the drawer's
    "Saving…" (`entry-drawer.js`).
  - **Never on a thumbnail:** a card's corner squares sit on the provider's
    image, so a saving Save keeps its pulse; the status bar shows the loader.
- **Cursor spotlight:** result and library cards, Discover's type tiles,
  gallery cards, pack cards and pack rows. A `::before` holds a 16 rem pool of
  ink (9 %, 6 % in light mode) at `--spot-x`/`--spot-y`, shown on the card
  `motion.js` marks `data-spot`. It's mouse only, behind the hover gate, and
  ignores the pointer. It sits above the thumbnail but under a card's details
  and corner actions (z-index 1).
- **The main page is all cover** (user requests, 2026-11-06): with a
  mouse (`@media (hover: hover) and (pointer: fine)`), the main page
  (`#app:has(#home-orbit)`) opens on its cover alone, filling the window
  above the status bar (`--cover-offset`), with the title bar and sidebar
  tucked away.
  - **Past the cover they come in:** `motion.js` sets `<html
    data-cover="past">` once the cover's bottom edge rises above the middle
    of the window, and clears it below 60 % (the gap stops flicker). It
    listens for scroll in the capture phase and checks again after every
    swap.
  - **On the cover** they still float in while the pointer rests on the edge
    they left (a 0.75 rem `::after` strip that travels with them, behind the
    hover gate) or keyboard focus is inside. The sidebar floats in under the
    title bar, so showing it shows the bar too.
  - **The transition:** the title bar glides down (0.6 s, ease-out), the
    sidebar follows 0.08 s later, then their items (the title bar's
    children, the sidebar's rows and its panel) fade and slide in one after
    another (`--chrome-i`, 35 ms apart). Leaving, the items fade at once and
    the bars slide off after 0.3 s. Hover colours keep their own undelayed
    fades.
  - **Nothing shifts:** the bars float (fixed). The stage keeps the
    sidebar's room (`--side-reserve`, 16 rem, 3.5 rem collapsed) so
    everything after the cover is laid out as on other pages, and the cover
    is pulled back by half of it (`.home-hero { left }`) to stay centred on
    the window.
  - Touch screens keep both bars in place; every other page is unchanged.
- **The orbit answers the scroll** (user request, 2026-11-06): in the
  parallax's `@supports` block, each ring turns on past its spin over the
  cover's height (`orbit-scroll-turn`: 28°, 42° and 58° from the inside
  out, reverse rings the other way), each texture counter-turns as far
  (`orbit-scroll-unturn`) to stay upright, and the stage eases in to 1.16×
  (`orbit-scroll-zoom`). The spin's reverse and hover-pause rules are
  restated for both animations. Reduced motion stills it.
- **Cards lift** (user request, 2026-11-06, from the prototype): result,
  library, gallery and pack cards rise 4 px on hover onto a soft shade drop
  (`--lift-shadow`, lighter in light mode), and a result's thumbnail eases
  in by 7 % over 0.6 s. The edge keeps its usual monochrome hover colour;
  the prototype's type-coloured edge and glow are left out (type colour
  only marks the type icons). Behind the hover gate. The hovered card gets
  `z-index: 2` so its corner tips stay above its neighbours, and a 4 px
  `::after` strip under it keeps the hover while it has risen off the
  pointer. Reduced motion holds it still.
- **Cards blur up:** cards in `.result-grid`, `.gallery-grid`, `.pack-grid`
  and `.pack-rows` rise out of a 10 px blur (`card-in`, 0.5 s), 40 ms apart.
  The stagger counts within each 12 (`:nth-child(12n+k)`), so a Load more
  batch staggers from its own first card. The fill is `backwards` only, so a
  card holds no filter or transform once it's in.
- **Reduced motion:** a blanket rule in the first reduced-motion block
  (`*, *::before, *::after { animation: none !important; transition: none
  !important; scroll-behavior: auto !important; }`) on top of the
  per-component list, which stays. Every entry animation runs from a `from`
  state to the element's own style (or ends fully shown), so with nothing
  animating, the content simply shows as it rests. The spotlight isn't lit,
  and a loader's mark holds still in `fg-secondary` (that rule comes after
  the loader's own, which it has to beat). The orbit and the ruler stay still
  as before.
- **Where it's missing:** htmx starts a View Transition only where
  `document.startViewTransition` exists, and the parallax needs scroll
  timelines. Everything else is plain CSS animation.

## Page widths (keep every page consistent)

The user asked, on 2026-11-06, that every page from now on keep to the same
layout rules. Two shapes only:

- **Full width** (inside the shell's `max-w-[1500px]` wrapper): pages that
  browse a collection or work on one: Discover, the library, Your packs,
  the builder.
- **A centred column** for everything narrower: `width: 100%`, a
  `max-width`, and `margin-inline: auto`, never pinned to the left. Today:
  `.entry-layout` (76 rem), `.attribution` (64 rem), `.pack-page` (60 rem,
  pinned left until the user reported it, 2026-11-06),
  `.discover-asset-page` (48 rem), the Account pages and New pack
  (`max-w-3xl mx-auto w-full`), `.remove-page` (30 rem).
  `test_every_column_page_is_centred_like_the_rest` checks the CSS ones;
  add a new column page's class there.

Within a page, reuse what exists before inventing: `.work-toolbar` for a
page's controls, `.builder-section` for a titled box, `.panel-row` (with its
`.panel-row-icon`) for a side-panel menu row, `.filter-group` /
`.filter-chip` for filters, `.status-chip`, `.file-badge`, `.card-action`,
`btn btn-quiet btn-sm rounded-none` for secondary actions and one
`btn-primary` per area. Rows of an item (`.pack-item`) start their
thumbnail, first text line and actions on one top edge.

## Two moods: showcase and work

`<main id="content" data-surface>` comes from `{% block surface %}`, which
defaults to `work`. Home and Discover override it with `showcase`.

- **Showcase** (discovery and marketing): the ambient glow at 50 %. A soft
  light falls from the top (an extra background layer under the dot
  grid). `.hero-atmosphere` shows an oversized, cropped `.hero-mark`
  (`min(46rem, 62%)`) at 5 % opacity, top right, fading downward. The
  headline is full size.
- **Work** (Library, Packs, Account, Settings): the ambient glow at 32 %
  and 1.4× slower. A smaller mark (`min(22rem, 30%)`, 6 %) tucked into the
  top right corner, clear of the cards and toolbars. Headers are
  `compact`. The header, controls and content sit in a `space-y-5`
  section, so they read as one block.
- **The mark on every page** (user request, 2026-11-05): it used to show
  on showcase pages only. Now every page has it, layered above the glow
  (`.hero-atmosphere` comes after `.ambient`), so the glow never covers it.
  The library drawer has its own faint cropped mark (`.drawer-mark`) in
  its lower corner, behind its content, so the logo stays in view while the
  drawer covers the page. Never on a provider thumbnail.

- **Sign-in and sign-up** are work surfaces too, with the same calm
  glow, so the form is the focal point. A brief
  corner-weighted `auth` mood was tried and dropped at the user's request.

New pages are work surfaces unless they're for browsing or discovery.

## Sign-in and sign-up

Both extend `templates/registration/auth_base.html`, which fills the blocks
`auth_heading`, `auth_lead`, `auth_form` and `auth_switch`.

- **Layout:** one `#auth-card`: a `.auth-card` with a `line-strong`
  border, two equal-height grid columns, and both columns' contents
  centred vertically. It's `max-w-6xl`, and the form column is
  `max-w-md`, a step up from the first version so the form leads the page.
  The form column is plain: a micro-label, a `2.75rem` headline, a 15 px
  lead, 48 px inputs (`.auth-form .input`), `pt-4` of extra room above a
  48 px full-width square submit, and a ruled "New here?" or "Already
  have an account?" line.
- **Inline errors only:** the forms are `novalidate`, so every error
  comes from the server and shows inline in the shell's style, never as a
  browser bubble.
- **Forgot password?:** password recovery is out of scope (PRD).
  `login.html` resolves `accounts:password_reset` with
  `{% url ... as forgot_url %}`, which yields nothing while the URL
  doesn't exist, so the link appears by itself once recovery is built.
- **Title bar:** a signed-out visitor sees Sign in and Sign up on the
  right, except on those pages themselves. The sign-in page shows only
  Sign up, and the sign-up page shows only Sign in, with no `?next=` back
  to sign-up. The breadcrumb still marks the current page.

## Library layout

`catalog/library.html` shows its controls even when the library is empty,
so the layout is set before any assets arrive. They're disabled while the
library is empty.

- `#library-toolbar` is a GET `<form>` (`.work-toolbar`, square and
  bordered, `role="search"`) directly under the header. It holds the
  search (`#library-search`, `q`) and the sort select (the PRD's four
  sorts). The grid/list toggle from the Phase 1 polish was removed in
  Phase 4, because the PRD describes only a card grid.
- The chips are `FilterChip`s in `FilterGroup`s (`catalog/filters.py`, shared
  with Discover), rendered by `catalog/partials/filter_chip.html`, which
  takes `form_id` and `control` (the library's toolbar and `.library-control`
  by default), `autosubmit`, and shows a chip's `icons` before its label.
- `#library-filters` is the library's own panel in the sidebar, under its
  navigation rows, because the PRD puts the filters there. It shows while
  the sidebar is open. It has `.filter-group`s of
  square `.filter-chip`s: Type, Provider and Status are checkboxes (any
  number on), and Minimum rating is a radio group (Any, 1+ … 5). Tags
  (Phase 4 polish) are checkboxes too, one per tag on the member's saved
  assets from every provider, most used first, each with its count
  (`.filter-chip-count`); an entry needs every chosen tag. With no tags
  yet, the group says where they'll come from. The first 8 tags show; the
  rest (up to 48) fold into `<details class="filter-more">` behind "Show N
  more" / "Show fewer" (user request, 2026-11-05). A chosen tag behind the
  fold opens it (`data-forced-open`), and otherwise `shell.js` reopens it
  the way the member last left it (`data-remember`, in `localStorage`).
  Each chip
  is a `<label>` around a `sr-only` input, so it works with the keyboard
  (a focus ring on the chip), and a chip that's on is inverted (ink). The
  inputs carry `form="library-toolbar"`, so they belong to the toolbar's
  form although they sit outside it.
- `#library-results` (`catalog/partials/library_results.html`) holds the
  count ("13–15 of 15 entries"), the grid of
  `catalog/partials/library_card.html` cards, and the pager
  (`#library-pager`: Previous, "Page N of M", Next). Or, instead, an empty
  state: "Your library is empty." with Go to Discover, or "Nothing in your
  library matches …" with Clear filters.

**Swapping only the results:** the form `hx-get`s `/library/` into
`#library-results` (`outerHTML`) with `hx-push-url="true"`.

- **Triggers:** `submit`, typing in the search after 300 ms
  (`input changed delay:300ms from:#library-search`), and any chip or the
  sort at once (`change from:.library-control`). DOM events from the
  side-panel inputs don't bubble to the form, hence `from:`.
  `hx-sync="this:replace"` drops a stale request.
- **The pushed URL:** the view replies with `HX-Push-Url`, the tidy URL
  without defaults or junk, which overrides the raw form query.
- **Pager links** are real URLs with the same `hx-get`, and
  `show:#library-toolbar:top` scrolls back up.
- **Back** restores through htmx's history-miss request, which the view
  answers with the whole page, so the controls match the URL again.
- **Clear filters** is a plain boosted link to `/library/`, so the search
  box and chips reset too. A swap of only the results would leave them
  set.

**Library cards** (`<li class="result-card library-card" id="entry-<pk>"
data-kind="<kind>">`) reuse the result card's frame, thumbnail (square for
textures), stretched title link, corner actions and details panel (see
"Result cards"):

- the provider's thumbnail over the type icon, as on Discover
- the type: its icon in the type colour, then the singular label in mono
  ("Texture", "HDRI")
- the title, which opens the entry's drawer (below). As a plain link it's
  the entry's full page, so Ctrl-click and Copy link work
- a `.library-meta` row: a monochrome `.status-chip` (`data-status`;
  Approved is inverted, Rejected struck through) and five star icons
  (`.star-rating`, filled with `.is-on`, `role="img"` with "Rated N out of 5"),
  or "Not rated". Never call it `.rating`: that's DaisyUI's rating
  component, whose `.rating *` rule painted each star as a grey 24 px block
  (fixed 2026-11-05).
- **Sounds** (user request, 2026-11-06): a sound's card has the play button
  (`catalog/partials/sound_play.html`) on its thumbnail and `data-sound-card`
  on the `<li>`, playing `Asset.preview_url` (its first stored file). The
  drawer's thumbnail has the same button.
- **Corner actions:** Add to pack, Details and Remove.
  - Add to pack opens the page's pack picker (below) for this entry.
  - Remove (`catalog/partials/remove_button.html`, Phase 7) is a link to
    `catalog:remove` that `hx-get`s the confirm into `<dialog
    id="remove-dialog" class="picker-dialog">`, once on the library page
    (see "Remove dialog"). Opened without HTMX it's the same confirm as a
    page. It replaced the browser's `hx-confirm`.
- **Details:** the provider's name and the asset's stored tags.
- **Community rating** (`.library-community`, user request, 2026-11-05):
  once any member has rated the asset, a "Community" line under the status
  and stars shows `catalog/partials/community_rating.html`: a grey filled
  star, the average to one decimal and "· N ratings". It's monochrome and
  grey, so it never reads as the member's own stars. It never names who
  rated. The same partial shows under a Discover result's author
  (`.result-community`) and in the drawer.

**Pack picker** (`catalog/partials/pack_picker.html`): one native
`<dialog id="pack-picker" class="picker-dialog">` on the library and on a
member's Discover page.
- A card's Add to pack button (`catalog/partials/pack_button.html`)
  carries `data-picker="pack-picker"`, `data-picker-asset="<title>"` and
  `data-picker-url`: `packs:picker` with `?entry=<id>` on a library card,
  or `?provider=…&external_id=…` on a Discover result.
  `static/js/card-actions.js` writes the title into the dialog, loads the
  URL into `#pack-picker-list` (`htmx.ajax`, "Loading your packs…" first)
  and calls `showModal()`, so the list is always current.
- The list (`packs/partials/picker_list.html`): each of the member's packs
  is a full-width `.picker-pack` button showing its item count, which posts
  to `packs:picker_add` and swaps the list for the reply ("Added to …", or
  the provider's message in a `.picker-alert`). A pack the asset is already
  in shows "In pack" and no button. Then New pack. With no packs: "You
  don't have any packs yet."
- It's square, on the panel colour, over a `shade` backdrop. A backdrop
  click, Close, the × button or Escape shuts it. The × and Close sit in
  their own `method="dialog"` forms (the list's forms can't nest in one),
  which htmx's boost leaves alone. Its swaps say `transition:false`, like
  the drawer's.

**Remove dialog** (Phase 7): `<dialog id="remove-dialog"
class="picker-dialog">`, once on the library page. A card's Remove or the
drawer's Delete `hx-get`s `catalog:remove` into it
(`catalog/partials/remove_dialog.html`), and `card-actions.js` opens any
`.picker-dialog` that HTMX has just filled. It shows the entry's title,
"It will also leave these N packs:" with each pack (`#remove-packs`), or
"It isn't in any of your packs.", and a note that the notes, rating and
status go too. Its Remove form posts to `catalog:remove` into
`#library-results`, carries `data-drawer-remove` (so an open drawer closes)
and `data-dialog-done` (so the dialog closes once the request succeeds).
The same partial, with `as_page`, is the confirm page
(`catalog/remove_confirm.html`).

## Library drawer

*(Phase 5.)* A card's title `hx-get`s `/library/<id>/` into
`<dialog id="library-drawer" class="drawer-dialog">` (`innerHTML`), once on
`catalog/library.html`. `static/js/entry-drawer.js` calls `showModal()`
after the swap.

- **The panel** (`catalog/partials/entry_drawer.html`): a native dialog,
  full height, `min(34rem, 100vw)` wide, against the right edge. It slides
  in over 0.28 s over a `shade` backdrop. Its sticky head has "Library
  entry", **Open as page** (the entry's URL) and Close. Close, a backdrop
  click or Escape shuts it. Reduced motion turns off the slide. The address
  bar doesn't change.
- **The full page** (`catalog/entry.html`): `.entry-layout`, centred
  (`max-width: 76rem; margin-inline: auto`; it used to sit pinned to the
  left in a 46 rem box, user report 2026-11-05). "Back to your library",
  then the body in a bordered `.entry-page` with the thumbnail and title
  side by side, and `.entry-aside` beside it on wide screens (sticky),
  holding `entry_related.html`. The crumbs are library / entry, and
  Library stays current in the bars.
- **Around the entry** (`catalog/partials/entry_related.html`, user
  request 2026-11-05): **Similar in your library** (`#entry-similar`, up to
  6 of the member's own entries with the most shared tags, then the same
  kind; each a small thumbnail over the type icon, the title and "N shared
  tags"), **Find more like this on Discover** (the kind and the asset's two
  most widely used tags), and **Featured in public packs** (`#entry-featured`,
  other members' public packs holding the asset, with owner and item count;
  never a private pack). The drawer shows the same after the entry, and
  there a similar entry opens in the drawer itself.
- **The body** (`catalog/partials/entry_detail.html`, `.entry`): the
  thumbnail (provider URL over the type icon, square and whole for
  textures), the type and provider, the title (`h2` in the drawer, `h1` on
  the page) and author. Then sections under mono labels:
  - **Your review:** status chips (`.filter-chip` radios), five star radios
    (`.rate-star`, each filled when it or a later star is checked, with a
    hover preview) plus "Clear rating" / "Not rated" (`.rate-clear`), and
    the notes box. Below them is the status line, `#entry-save-status`.
    Under the stars, `#entry-community` gives the community rating ("from
    every member who rated it, you included", or "No one has rated this
    yet."). A rating change sends it again out of band.
  - **Who set the status, and why** (user request, 2026-11-05), under the
    status chips: `#entry-status-note` ("Approved by you · 5 Nov 2026,
    14:02", "· via the API" when a token set it, the reason in quotes, and a
    folded "History · N changes"), or "To review since you saved it on …"
    for an entry with no record yet. Then `#entry-status-reason`, one line
    ("Why is it approved? Add a reason (optional)") that posts only
    `status_reason` on change or Enter (`data-autosave="reason"`, so
    `entry-drawer.js` handles its errors and Try again). A status change
    sends the note and an empty reason box out of band; a reason sends the
    note only, so the box being typed in is never replaced.
  - **License and credit:** the linked license, the attribution, "View on
    <provider>", tags and the saved date.
  - **Your packs** *(Phase 7)*: the packs the entry is in (`#entry-packs`),
    each linking to its builder with the item's variant, or "It isn't in
    any of your packs yet."
  - **Files** (`catalog/partials/entry_files.html`, user request
    2026-11-05):
    - **Your bundle** (`#entry-bundle`): what the member's download
      defaults pick (`catalog.files.pick_bundle`): resolution and format
      badges (`.file-badge`), the package, the file count and size, the map
      types, a note wherever it had to differ ("No 8K here, so 4K, the
      nearest."), and "Defaults: 2K · JPG · every map" linking to Settings.
      One file is a plain **Download** link to the provider's file. Several
      are **Download bundle** (`btn-primary`): `static/js/bundle-download.js`
      reads the `json_script` `entry-bundle-data` (each file's provider URL,
      its path in the zip and size, plus the credits), fetches the files one
      at a time straight from the provider, and saves a stored zip with a
      `CREDITS.txt` (and `MISSING.txt` for any file the provider wouldn't
      hand over). Progress shows in `[data-bundle-status]` and a 2 px bar.
      Over 2 GB it says to use the links instead. The Toolbox never
      downloads, hosts or proxies a file (PRD, Out of Scope): Poly Haven,
      the only provider with multi-file variants, serves its files with
      `Access-Control-Allow-Origin: *`.
    - **Filters:** Resolution and Format chips (`[data-file-filters]`,
      `hidden` until `static/js/entry-files.js` shows them) narrow the list
      in the page.
    - **Variants:** one `<details>` per variant, its summary the resolution
      and format badges, the package (Loose maps, Bundle, Archive, Audio),
      "Your default" (inverted) on the bundle's variant, and "N files ·
      size". Each file row starts with its role: the map it holds (Color,
      Normal GL, Roughness…) or Scene, Data, Archive, Audio.
  - **Remove from library** (`entry_remove.html`): in the drawer it opens
    the Remove dialog; on the full page it links to the confirm page.
- **Type colour:** only the type icon beside the label and the fallback
  icon, as on the cards.

**Saving:** status, rating and notes are three separate forms, each
posting only its own field to `catalog:update`. Status and rating post
on `change`. Notes post 0.7 s after typing stops and again on leaving the
box (`input changed delay:700ms, change`), queued (`hx-sync="this:queue
last"`) with a 15 s timeout. There's no Save button. Every reply replaces
only `#entry-save-status`: "Changes save as you make them.", "Saving…",
"Saved", or an error with **Try again**. A status or rating change from
the library also swaps the card behind the drawer out of band.

**No page transition:** the drawer's swaps (opening it, every save, and
its Remove) say `transition:false` in `hx-swap`. Under the global View
Transitions, the whole `#content` faded out and back in behind the drawer
as it opened, so the drawer seemed to appear, vanish and reappear. The user
reported this on 2026-11-05.

**Notes are never lost** (user request, 2026-11-05). `entry-drawer.js`:

- keeps the text in `localStorage` (`data-draft-key`, `ax-notes-<id>`)
  from the first keystroke until a save of that exact text succeeds. If a
  draft is still there when the entry opens again, the script puts it back
  and saves it.
- on a 400 or 401, lets the Toolbox's own status line swap in. On any
  other error response (a CSRF page, a server error page), a dropped
  connection or a timeout, it writes "Couldn't reach the Toolbox…" or
  "Something went wrong…" there itself, with Try again. A lost connection
  also retries on `online`.
- sends the CSRF token from the `csrftoken` cookie, so a save still works
  after signing in again in another tab, which rotates the token.
- asks before closing the drawer, opening another entry, navigating
  (boosted) or unloading the page while the notes differ from the last
  text the server confirmed and no save is on its way.

Escape in `card-actions.js` ignores every open dialog, the drawer
included.

## Settings

The Account pages (Profile, Settings, API token) share one centred column,
`.account-page max-w-3xl mx-auto` (they sat to the left until the user
pointed it out, 2026-11-05). `accounts/settings.html`, a work surface: **Appearance** (`#appearance`: the
System, Light and Dark chips, see "Light and dark"), then **Download
defaults** (`#download-defaults`, user request 2026-11-05). One small form
per group of `.filter-chip`s (Resolution, Texture format, HDRI format,
Model format, Sound format, and the Texture maps checkboxes), each posting
only its own field to `accounts:download_preferences` on change. There's
no Save button (a `<noscript>` one stands in without JavaScript). Every
reply replaces `#settings-save-status`. The maps form also sends
`maps_posted`, so unticking every map still counts as posted (and is
refused: "Choose at least one map type."). The library drawer's bundle and
"Your default" badge follow these settings.

## Packs

*(Phase 7.)* Work surfaces. Every packs page's side panel is
`packs/partials/pack_nav.html`: "Your packs" with a small **New** action
(`.panel-action`), then one `.panel-row` per pack (`#pack-nav-<id>`), the
open pack current. With none: "The packs you create are listed here."

- **Your packs** (`packs/pack_list.html`): the header, a `.work-toolbar`
  with the count, the **Grid / List** switch (`#pack-layout`, a
  `.layout-switch` of two `.layout-option` links, `?layout=grid|list`, the
  current one inverted with `aria-current="true"`; remembered in the session
  by `packs.views.pack_layout()`, user request 2026-11-06) and **New pack**
  (`btn-primary`). In a list, `#pack-list` is `.pack-rows` of `.pack-row`s:
  the visibility chip, the title (stretched `.pack-card-link` to the
  builder), the intended use on one line and the tags, then the item count,
  the date and View page; one column on a phone. In a grid, `#pack-list` is a
  `.pack-grid` of `.pack-card`s: Private or Public (a `.status-chip`,
  Public inverted), the item count, the title (its link stretched over the
  card), the intended use (two lines), the tags and the date it changed.
  Empty: "You have no packs yet." with New pack.
- **New pack** (`packs/pack_new.html`, a centred `max-w-3xl` column like the
  Account pages): a `novalidate` form through
  `partials/form_fields.html` (title, intended use, tags with their tidying
  rule as help), **Create pack** and Cancel.
- **The builder** (`packs/builder.html`): "Pack builder" over the title
  (`#pack-title`), then a toolbar with the **public/private switch**
  (`#pack-visibility`: two `.filter-chip` radios that post on change and
  swap the form, saying "Only you can see it." or "Anyone can view and
  export it.") and **Delete pack**, which opens `#pack-delete-dialog`
  (`data-dialog-open`; its form is a plain boosted POST). Below, a
  `.builder-grid`: the details and items on the left, **Add from my
  library** on the right (sticky on wide screens).
  - **Details:** title, intended use and tags, three forms each posting
    only its own field on `change` to `packs:details`. The reply replaces
    `#pack-save-status`; a rename also swaps `#pack-title` and the side
    panel's row out of band.
  - **Items** (`#pack-items`, `packs/partials/items.html`): the count, then
    one `.pack-item` per item: the thumbnail over the type icon, the type
    and provider, the title, a **Variant** select and an **Import path**
    input (its placeholder is the default, `<kind>s/<external_id>/`), each
    its own form posting on `change` into the item's status line
    (`#item-<id>-status`). Then Move up, Move down (disabled at the ends)
    and Remove, `.card-action` squares that swap the whole list. There's no
    Save button anywhere.
  - **Add from my library:** a search that `hx-get`s `packs:library_search`
    on load, 300 ms after typing, and on `packItemsChanged` (sent by every
    add, move and remove), into `#pack-library-results`: up to 12 entries,
    each with Add (posting to `packs:add_item`, swapping `#pack-items`) or
    "In pack".
  - **Suggested for this pack** *(Phase 10)*: a `.builder-section` in the
    left column, under the items (Add from my library keeps the sticky right
    column to itself). `packs/partials/suggestions.html` (`#pack-suggestions`,
    `.pack-suggestions`) lists up to 8 `.pack-pick` rows, two to a line from
    48 rem: the thumbnail over the type icon (no hover preview here, as it
    would open over the side panel), the title, type, provider and license,
    then "N shared tags" and "In your library" when the owner has it, and
    **Add** (posting `asset` to `packs:suggestion_add`, swapping
    `#pack-items`), with the note "Adding one that isn't in your library
    saves it there as To review." The block `hx-get`s itself on
    `packItemsChanged from:body` and `packTagsChanged from:body` (two
    separate events). Then **Find more from providers** (`#pack-find-more`,
    `btn btn-quiet btn-sm rounded-none`, to Discover) with "Searches Discover
    for “…”.". With no tags: "Add tags to this pack to see suggestions." and
    `#pack-find-more-hint`, "Add tags to this pack to find more from
    providers."; with no match: "No other assets share this pack's tags
    yet." Type colour only on the type icons.
- All the builder's swaps say `transition:false`, so the page doesn't fade
  behind each save.
- *(Phase 8)* The builder's toolbar has **View pack page** (`#pack-page-link`)
  beside Delete pack, and each pack card has **View page**
  (`.pack-card-page`), raised above the title's stretched link so it opens
  the page rather than the builder. "Featured in public packs" in the drawer
  and on an entry's page links each pack to its page.
- **Private, Unlisted or Public** (user request, 2026-11-05): the builder's
  switch (`#pack-visibility`, `packs/partials/visibility.html`) has three
  chips; the whole block swaps on change. Its line reads "Only you can see
  it.", "Anyone with the link can view and export it. It isn't listed
  anywhere." or "Anyone can view and export it." While unlisted, the share
  link box (`#pack-share`, `packs/partials/share_link.html`) sits below: the
  link in a read-only mono field (`#pack-share-url`), **Copy link**
  (`data-copy`, `card-actions.js`: the clipboard, or the text selected with
  "Press Ctrl+C" where the clipboard isn't available) and **New link**, which
  opens `#pack-rotate-dialog` ("Make a new link?", "The current link stops
  working at once…"). Its form (`data-dialog-done`) swaps `#pack-share`,
  which then says "New link made. The old one no longer works." The pack
  card and the pack page's owner chip say Unlisted (`.status-chip
  [data-visibility="unlisted"]`, outlined in `fg-secondary`).
- **A pack's page** (`packs/pack_page.html`, `/packs/<slug>/`, Phase 8): a
  work surface, `.pack-page`, a centred 60 rem column (it sat to the left
  until the user reported it, 2026-11-06; see "Page widths"). "Public pack", "Unlisted pack" or
  "Private pack" over
  the title (`#pack-page-title`), "By <owner> · N items · Changed …", the
  intended use and the tags. Then a toolbar (`#pack-page-actions`) with
  **Download manifest** (`btn-primary`, `hx-boost="false"` and `download`,
  because a boosted link would swap the JSON into the page) and, for the
  owner only, the Public, "Unlisted · link only" or "Private · only you"
  chip and **Edit in builder**. The share link serves the same page; its
  crumb and Download manifest use the link (`page_url`, `export_url`).
  The items (`#pack-page-items`) are the builder's `.pack-item` rows made
  read-only (`.pack-item-read`, no actions column): thumbnail over the type
  icon, type and provider, title, author, then `.pack-item-facts` (License,
  "no credit needed" for CC0 or the Credit line, Files as a `.file-badge` with
  the count and size, the Import path in mono, and the Source). **Credits**
  (`#pack-page-credits`) says how many items need credit. No edit controls,
  for the owner too; nothing from anyone's library (notes, ratings, statuses,
  the community rating) except the reader's own "In your library".
- **Save and Copy on a pack's page** *(Phase 11)*: the page's only forms.
  - Each item's `.pack-item-download` row starts with
    `packs/partials/item_save.html` (`.item-save`, `btn btn-quiet btn-xs`):
    **Save to library** (plus icon) for a member, posting with `hx-post` and
    swapping itself (`transition:false`); **In your library** (check icon,
    inverted like Discover drawer's `.is-saved`) once the reader has it,
    linking to their own entry, with the saved count out of band after a new
    save; **Sign in to save** for a visitor, back to this page.
  - The toolbar's right group (`#pack-page-own`) ends with **Copy pack**
    (`#pack-copy-button`, the `copy` icon), which opens `#pack-copy-dialog`
    ("Make a private copy?", what it copies, and `#pack-copy-missing`: "N
    assets you don't have yet go into your library as To review." or
    "Everything in it is already in your library, and stays as it is."). Its
    form is a plain boosted POST; the copy's builder opens next. A visitor
    gets **Sign in to copy** instead, and no dialog.
  - By share link, both post to the link's own URLs, and a visitor's sign-in
    comes back to the link.
  - The builder of a copy says "Copied from <title> by <owner>"
    (`#pack-copied-from`, `text-xs`, the `copy` icon), the title linking to
    the original's page only when the member can read it by slug. Members get their packs
  in the side panel; a visitor gets "Shared pack" (`#pack-visitor-panel`)
  with Sign up. Type colour: only the two type icons, as in the builder.
- **Item alignment and sounds** (user reports and request, 2026-11-06): on
  the builder, the pack page and Asset attribution (`.lookup-item`), a
  thumbnail sits in the middle of its row, as in every other thumbnail list
  (Add from my library, Similar in your library). Pinned to the top it looked
  misaligned beside the taller text, which the user reported twice. The
  builder's grip has the thumbnail's height beside it (it used to stretch
  the row), the actions stay at the top on the title's line, and an idle
  status line is hidden so it leaves no empty band. A thumbnail's frame is a
  1 px border on a `::after` above the image (the image used to cover the
  inset shadow, so frames lost edges). An asset's license line in Asset
  attribution reads as one paragraph (`.lookup-license`), so "CC0 1.0" no
  longer breaks. The type icon in a thumbnail with no image is 24 px. A
  sound's item has `data-sound-card` and a centred, smaller play button
  (`sound_play.html` with `small`, `.sound-play.is-small`) on its thumbnail.
- **Builder and pack page polish** (user request, 2026-11-05):
  - **Add from my library** is a form (`#pack-library-form`): the search,
    "Show ones already in this pack" (`show_in`) and a hidden `page`
    (`#pack-library-page`, sent again out of band with each reply, so
    `packItemsChanged` refreshes the same page). Typing or the checkbox
    asks for page 1 (`hx-vals`). Rows (`.pack-pick`) show a 2.75 rem
    thumbnail over the type icon, with an 11 rem preview to the left on
    hover (`.pack-pick-zoom`, behind the hover gate), then the title, type,
    provider and license. `.pack-picks-pager`: Previous and Next
    `.card-action` arrows and "Page N of M · X assets".
  - **Items** (`#pack-items`): an `.ax-select` **Auto sort** that posts on
    change (shown with two or more items) and "Sorted: …" after it. Each
    `.pack-item` starts with a grip (`.pack-item-grip`, `[data-drag-handle]`);
    `static/js/pack-sort.js` makes the row draggable from its grip only,
    moves it live while dragging (`[data-dragging]` dims it), puts it back on
    Escape, and posts `order` through `htmx.ajax` (inheriting `#app`'s CSRF
    header). Each row also has a hint under its import path and a
    **Download** `.card-action`.
  - **`.ax-select`**: the select loses its native arrow
    (`appearance: none`), a `chevron-down` icon sits in its place, and
    options use the elevated colours. The Variant options read
    "2K JPG · 3 files · 24.1 MB".
  - **Downloads**: buttons with `data-bundle-download` and `data-bundle-url`
    fetch the list from `packs:files` when pressed, so it follows the latest
    variants and paths; the status line is the `[data-bundle-status]` in the
    nearest `[data-bundle-box]` (the toolbar's `#pack-downloads`, or the
    item). The builder's toolbar has Download files and Download manifest;
    the pack page has Download files (`btn-primary`) beside Download
    manifest, and each item a Download (a plain link to the provider for
    one file).
  - **"What's an import path?"** (`packs/partials/import_path_help.html`,
    `#import-path-help`): a `<details>` with an example tree, above the
    items on both pages, outside `#pack-items` so a swap never closes it.
    The pack page's "What's this?" opens it (`data-open-details`).
  - **Credits** (`packs/partials/credits.html`, `#pack-page-credits`), in
    brief: how many items need credit, the warnings (`.credits-warnings`, a
    2 px ink edge), and one `.credits-summary` row per license (a
    `.license-chip` to its guide card, a `.status-chip`: Credit required
    inverted, recommended outlined, optional plain, and the summary), then
    **Full attribution and license notice**, the pack's attribution page
    (the share link's own when read by link).
- **Attribution center** (user request 2026-11-05; split into pages the same
  day): a sidebar entry after Packs (`license` icon,
  `active_nav="attribution"`) and its own drop colours. Every page's side
  panel is `packs/partials/attribution_nav.html`: License guide, and for
  members Pack attribution and Asset attribution, the current one marked.
  Monochrome throughout: no type colour on any of its pages.
  - **License guide** (`packs/attribution.html`, `/attribution/`): for
    members two `.attribution-link` cards to their pages, for visitors a
    sign-in note; a table **At a glance**; a `.license-card` per license
    (`#license-<key>`, outlined when targeted) with
    `packs/partials/license_facts.html` (four facts with a check, a cross or
    a dash, never colour alone) and `packs/partials/license_terms.html`
    (**You may**, **You must**, **You may not**, three `.license-terms-col`s,
    the last with an ink top edge), "How to meet it" folded; then **How to
    credit** and **Optional credits**. The side panel adds "On this page".
  - **Pack attribution** (`packs/attribution_packs.html`): the member's
    packs, each with license chips and counts, what's owed, its warnings and
    a link to its page.
  - **A pack's attribution** (`packs/attribution_pack.html`): the title,
    "Compiled by …", who owns the assets, View pack page (and Edit in
    builder for the owner), **Restrictions in force**, the notice
    (`packs/partials/notice_copy.html`, `#attribution-notice`: the full
    notice in a `<pre>` with **Copy the notice** as the `btn-primary`, and
    the credit lines alone with **Copy credit lines**; `data-copy` copies an
    element's text and keeps each button's label), then **License terms**: a
    `.credits-group` per license with the terms and every item's credit (the
    owner also gets each asset's page), and the optional acknowledgements.
    No form controls.
  - **Asset attribution** (`packs/attribution_assets.html`): a form
    (`#attribution-filters`) with the search and two rows of `.filter-chip`
    checkboxes, **License** (only the types in the library) and **Credit**
    (required, recommended, optional; disabled at 0), each with a count. It
    swaps `#attribution-assets-results`
    (`packs/partials/attribution_assets_results.html`) on change or typing,
    with `hx-push-url`, and submits as a page without JavaScript. Results
    say how many match, with Clear filters; Previous and Next are links that
    keep the filters.
  - **An asset's attribution** (`packs/attribution_asset.html`): the
    thumbnail and title, Open in library and View on the provider, the
    license with its facts and terms, the credit to show (or the optional
    acknowledgement), the notice, and the member's packs holding it.
  - The drawer's License row says the credit rule and links to its card.
  - **Iconography and compatibility** (user request, 2026-11-05):
    - `packs/partials/license_symbols.html`: a license's symbols (`lic-zero`,
      `lic-pd`, `lic-by`, `lic-sa`, `lic-nc`, `lic-nd`, `lic-sampling`,
      `lic-unknown`), named in `aria-label` and `title`; `large=True` boxes
      them. Beside every license name: the guide's cards and table, the pack
      page's summary, pack and asset attribution.
    - `packs/partials/license_uses.html`: "Can I use it?", three `.use-cell`s
      (Commercial `use-commercial`, Personal `use-personal`, Internal
      `use-internal`), each with a check, a warning sign or a cross and the
      verdict written out: usable plain, with conditions outlined, not usable
      with an ink top edge, its icon inverted and its verdict underlined.
    - `packs/partials/compatibility.html` (`#pack-compatibility`): when a use
      is blocked, `.compat-warning` (a 4 px ink edge): "This pack may not be
      usable for … use.", the reasons, then "edit the pack" (the owner) or
      "contact the owner, <username>" (anyone else); otherwise a line saying
      it's clear or has conditions. Then the pack's three `.use-cell`s with
      their reasons. On the pack page (above the items), a pack's
      attribution, and inside the builder's `#pack-items`, so each swap
      rechecks it. Pack attribution shows `.use-chip`s per pack.
    - The guide: **Symbols** (two `.symbol-legend`s: the elements and the
      uses, with the verdict key), **At a glance: can I use it?** (symbols, and
      each use's verdict with its icon), and **The licenses**, one card per
      row (`.license-card-head` with large symbols, then the uses and the
      terms).
    - **Legend fix** (user report, 2026-11-06): the legend's stacked
      name-over-meaning rule is `.symbol-legend li:not(.symbol-legend-key) >
      span:last-child`. Without the `:not`, it caught the verdict key's last
      `.use-key`, so "Not usable" put its icon above the word.
    - **On this page** (`#attribution-toc`, user request 2026-11-06): Symbols,
      At a glance, then the eleven licenses folded into one "Licenses" row
      with a count (`#attribution-toc-licenses`, a `.panel-fold`, closed at
      first and remembered as `ax-toc-licenses`), each license row showing its
      first symbol; then How to credit and Optional credits. Every row has
      its icon.
    - Every Attribution page is a centred column (`.attribution`, 64 rem,
      `margin-inline: auto`).

## Main page

`packs/home.html` is a showcase surface. From the top:

- **Hero:** the header, then `#hero-search` directly below the
  description: a square, 56 px bar that sends `q` to `catalog:discover`. Its
  Search button is the page's only `btn-primary`. Under it are secondary
  `.btn-quiet` buttons (outlined, square, inverted on hover): Browse
  Discover and Open your library for members, or Sign up (`#home-signup`)
  and Sign in (`#home-signin`) for visitors.
- **How it works** (`#home-steps`, visitors only, Phase 9): "Four steps
  from search to engine.", then four `.home-step` boxes: 01 Discover, 02
  Save, 03 Pack and 04 Export. Each has its number in mono, a monochrome
  icon in a square, a title and one line. Then a note that browsing needs no
  account. It adds no second primary button; the hero's Sign up and Sign in
  are the buttons. Members see neither the steps nor any sign-up prompt.
- **The gallery** (`#gallery`, everyone, Phase 9): "Public packs" and "See
  what others have built.", then `#gallery-toolbar`, a `.work-toolbar` GET
  form like the library's. It holds the search (`#gallery-search`, `q`) and
  two `.gallery-control` selects: Any type or "Containing textures" and so
  on (`type`), and Newest or Most items (`sort`). The controls sit in the
  page, not the side panel, because the panel starts collapsed here.
  - **Swaps:** it `hx-get`s `/` into `#gallery-results` (`outerHTML`,
    `hx-push-url`), on submit, 300 ms after typing, or on a select's change.
    The view pushes the tidy URL. Pager links are real URLs with the same
    swap. Without JavaScript a `<noscript>` Apply submits the form.
  - **Results** (`packs/partials/gallery_results.html`): "1–12 of N public
    packs", a `.gallery-grid` of cards, and `#gallery-pager`. Instead, there
    may be an empty state:
    - "No public packs yet.", with Go to your packs (members) or Sign up
      (visitors)
    - "No public pack matches “q”." or "No public pack holds that type
      yet.", with Clear filters (`/#gallery`)
  - **A card** (`packs/partials/gallery_card.html`, `.gallery-card`):
    - a 2 x 2 `.gallery-mosaic` of the first four items' thumbnails by
      position. Each `.gallery-tile` is the provider's image over the
      asset's type icon, square and cover. A short pack gets empty
      `.is-blank` tiles.
    - the title (`.pack-card-link`, stretched over the card, to the pack's
      page)
    - "By <owner>", the tags (`.pack-card-tags`), and the count by type in
      mono at the foot
    - nothing from anyone's library. Hovering inverts the edge, behind the
      hover gate.

- **Orbit hero** (`#home-orbit`, `packs/partials/hero_orbit.html`, Phase 12;
  after Artcraft's hero, and a cover of textures only, at the user's requests,
  2026-11-06): the hero fills the first screen (`min-height: calc(100dvh -
  4.5rem)`, the window less the title and status bars) from the content's top
  edge (an unlayered `margin-top`, as `space-y-8` would reset a component one).
  The text is centred in front (`#home-hero-text`: the header, search and
  buttons, on a soft pool of the panel colour) and the orbit turns behind it. The
  orbit fades out down its lower half into the page (a mask on `.orbit`, whose
  layer reaches past the hero's sides, as a mask paints only inside its own
  box), and the page clips it at its sides (`overflow-x: clip` on
  `.content-stage` here). The text comes first in the HTML, so the keyboard
  reaches the search before the orbit. From `packs.hero.hero_orbit()` (see
  ARCHITECTURE.md, "Main page and gallery"):
  - **Rings:** a square stage wider than the window (`min(max(96vw, 150dvh),
    140rem)`, 160vw on a phone), centred on the hero. Faint grey `.orbit-guide`
    rings (some dashed) for depth; over them up to three texture rings (46, 66
    and 86 %, the busiest outermost), each line a 40 % `::before` in its
    `border-texture` colour so it blends in, turning once per `--spin` (90, 120,
    150 s), neighbours turning opposite ways (`.is-reverse`).
  - **Tiles:** textures only. Each is `--tile` rem across (`OrbitRing.tile_rem`,
    bigger further out; × 0.62 on a phone). Each `.orbit-arm` (`--angle`) turns
    its `.orbit-thumb` to its place; the thumb turns back and its `.orbit-face`
    counter-spins against the ring, so it stays upright. A texture with an image
    is a **cut-out** (`.is-cutout`): the provider's sphere render on its
    transparent background, 1.3× bigger, with no tile behind it and a
    drop-shadow that follows its shape. With no image (or one that fails), the
    framed tile and texture icon show (`:has(img)`). Images load eagerly
    (`referrerpolicy="no-referrer"`, `data-thumb-fallback`). Each tile links to
    the newest public pack holding the texture, named in `aria-label` and
    `title`.
  - **Pausing:** hovering a tile (`.orbit:has(.orbit-thumb:hover)`) or keyboard
    focus inside the orbit pauses every ring and face. Reduced motion stills
    them. Only the tiles take the pointer; the text's own controls sit above.
  - **No logo:** nothing in the orbit is the mark or the wordmark. The page's
    faint `.hero-mark` stays (every page has it) but moves below the hero here
    (`translate: 0 calc(100dvh - 4.5rem)`).
  - **No caption:** the legend and the count line were removed at the user's
    request.
  - **Fallback** (`.orbit.is-fallback`, fewer than 6 textures in public packs):
    six texture-icon tiles on the outer ring, opening Discover's textures.
- **Scroll ruler:** see "Scroll ruler". Its sections are Toolbox (`#home-hero`),
  How it works (`#home-steps`, visitors only) and Public packs (`#gallery`).

**The side panel starts collapsed here** (PRD), whatever the member chose
elsewhere:

- `HomeView` sets `panel_start = "collapsed"`, and `base.html` writes it as
  `data-panel-start` on `<html>` (for the first paint) and on `#app` (for
  boosted swaps, which replace `#app` but not `<html>`).
- The head script uses it ahead of `localStorage["ax-panel"]`.
- After each boosted swap, `shell.js`'s `applyPanelStart()` sets the panel
  to the arriving page's start, or back to the saved choice, so leaving the
  main page restores it.
- The toggle still works on the main page and still saves the choice.

## Scroll ruler

*(Phase 12; on every page at the user's request, 2026-11-06.)* In `base.html`,
from 80 rem only (`hidden xl:flex`), with `static/js/scroll-ruler.js`.

- **Where:** `nav#scroll-ruler` (`aria-label="Sections on this page"`), fixed
  down the content's right edge between the title and status bars. The content
  and the footer (`.content-gutter`) get 6 rem of right padding from 80 rem, so
  nothing runs under it (an unlayered rule, as `lg:px-12` would beat a component
  one). A panel-coloured halo keeps its text readable over the glow.
- **The scale** (`partials/ruler_scale.html`, after Artcraft's ruler): a spine
  with a minor tick every 2 % and a numbered major every 10 % (0, 5 … 50), an
  ink fill and a cursor at the scroll position (`--ruler-progress`). Monochrome.
- **The section index:** each page lists its sections in `{% block
  ruler_sections %}`, one `partials/ruler_entry.html` each (`target`, `label`),
  under the same `{% if %}` as the sections themselves, so an entry is only there
  when its section is. The default is Top (`#page-top`, the content wrapper) and
  End (`#page-footer`). Today: the main page; Discover (Search, Types, each
  shelf); the library (Library, Results); an entry's page (Entry, Related, End);
  Your packs; the builder (Pack, Details, Items, Suggested, Add from library); a
  pack's page (Pack, Items when it has any, Credits); the license guide; a pack's
  and an asset's attribution; Settings (Settings, Appearance, Download defaults).
  Numbers are a CSS counter (`01`, `02`…); a label slides out on hover (behind
  the hover gate) or keyboard focus. Every `[id]` in the content has
  `scroll-margin-top: 1.5rem`.
- **Without JavaScript:** each entry is a plain `#id` anchor (htmx never boosts
  those, and the nav says `hx-boost="false"`), evenly spaced down the ruler, and
  still jumps.
- **With it:** `scroll-ruler.js` follows `#content`'s scroll (a capture-phase
  listener) and each swap (`htmx.onLoad`): the fill and cursor; each entry placed
  level with where its section starts in the page (`--at`, `[data-placed]`), at
  least 28 px apart; an entry whose section isn't on the page hidden; and
  `aria-current="true"` on the section in view. A click scrolls smoothly
  (instantly under reduced motion), focuses the section and puts its `#id` in the
  address bar.

## Discover

`catalog/discover.html` is a showcase surface. From the top:

- **Scroll ruler** (Phase 12): Search (`#discover-search`), Types
  (`#type-tiles`), then each provider's shelf (`#shelf-<provider>`, its name).

- **Header:** the usual page header.
- **Command bar:** `#discover-search`, a `.command-bar`. It's a GET form
  with a hidden `type` and the `q` input (`#discover-search-input`). The
  home hero search lands here, because both send `q`.
  - The input carries `data-search-shortcut`, and `shell.js` focuses it
    when `/` is pressed. Nothing happens if the cursor is already in an
    input, textarea, select or editable element, or if Ctrl, Alt or Meta
    is held.
  - A `.command-key` shows the `/` hint.
- **Type tiles:** `#type-tiles`, four `.type-tile` links. The current one
  has `aria-current="true"`, never `"page"`, which belongs to the bars.
  - Each link keeps the query, so switching type re-runs the same search.
  - The icon and the 2 px `.type-tile-bar` take the type colour, and the
    bar grows in under the current tile. The colour classes are written
    out in full in `catalog/discover.py` (`KindTile`) so Tailwind finds
    them.
- **Random pick:** with no query, `#featured-pick` shows "Random pick",
  "<Type> for “<pick>”", a Shuffle button and the providers hint, and the
  shelves search the pick.
- **Shelves:** `#discover-shelves` holds one `catalog/partials/shelf.html`
  per provider.

**Shelf states** (`<section id="shelf-<provider>">`, replaced whole):

| State | What shows |
|---|---|
| Pending | `aria-busy`, `hx-get` of its own URL, `hx-trigger="load"`, `hx-swap="outerHTML"`, the logo loader with "Searching" in its header (Phase 13), and six pulsing `.result-skeleton`s |
| Results | A `.result-grid` (`#shelf-<provider>-results`) of `.result-card`s (see "Result cards"), then Load more when the page came back full |
| No matches | `.shelf-empty`: "No <provider> matches for “q”." |
| Failed | A DaisyUI `alert alert-error` (`.shelf-alert`, toned down and square, with the error colour only on the icon) holding the `ProviderError` message and a Retry button inside the alert. Retry `hx-get`s this shelf's own URL into `#shelf-<provider>` |

The shelf header shows a number (`01`), the provider's name, a rule, and
"Searching", "Unavailable" or the result count.

- **Credit:** every shelf, in every state, ends with a `.shelf-credit` line
  linking to the provider ("Assets from ambientCG · CC0", "Powered by Poly
  Haven", "Made with Openverse").
- **Type-icon fallback:** `.result-thumb` always holds the type's icon
  (`.result-fallback`, in the type colour, because it shows the asset's
  type), and the thumbnail is positioned over it. With no thumbnail URL
  there's no `<img>`, so the icon shows. An `<img data-thumb-fallback>`
  that fails to load is removed by a capture-phase `error` listener in
  `shell.js`, which uncovers the icon. The logo is never the fallback.
- **Status out of band:** a loaded shelf's response also carries its
  provider's status bar item with `hx-swap-oob="true"`, so the status bar
  updates as soon as the shelf loads.
- **Load more** (`catalog/partials/load_more.html`): a full-width square
  `btn-quiet` in `#shelf-<provider>-more`, "Load 12 more" ("Loading…"
  while the request runs). It fetches the next page into that slot
  (`outerHTML`). The reply (`shelf_more.html`) holds:
  - the new slot: the next button, the end note "That's everything from
    <provider> for “q”.", or an alert whose Retry asks for the same page
  - the new cards, in a `<ul hx-swap-oob="beforeend:#shelf-<provider>-results">`.
    htmx appends the `<ul>`'s children, not the `<ul>` itself.
  - the count (`#shelf-<provider>-count`) and the provider's status, both
    out of band

  A failed page leaves the cards already shown in place.

**Result cards** (`catalog/partials/result_card.html`) are `<li
class="result-card" data-kind="<kind>">`s:

- **Whole-card link:** the title's `.result-link` opens the result in
  Discover's drawer (see "Discover's drawer"; it opened the provider's page
  in a new tab until 2026-11-06), and its `::after` is stretched over the
  card, so the whole card is clickable. As a plain link it's the result's own
  page (`catalog:discover_asset`). Interactive parts (the play button, the corner
  actions) sit above it with a higher `z-index`. Keyboard focus on the link
  draws a 2 px ink ring on the card.
- **Thumbnail:** the provider's URL (`referrerpolicy="no-referrer"`, never
  the logo) over the type-icon fallback. The frame is 4:3 with
  `object-fit: cover`, except for textures (`data-kind="texture"`). Their
  thumbnails are square tiles, which 4:3 cut off at the top and bottom, so
  a texture's frame is square with `object-fit: contain`, showing the whole
  tile (user request, 2026-11-05).
- **Author:** `.result-author` is cut with an ellipsis. `.result-body`'s
  column is `minmax(0, 1fr)`; without it, the column grows to fit a long
  author list and the line runs out of the card. That happened with Poly
  Haven's multi-author textures.
- **Corner actions** (`.card-actions`, Phase 4 polish, 2026-11-05): small
  translucent squares (`.card-action`, 1.75 rem) in the card's top-right
  corner, above the stretched link (`z-index: 3`).
  - On Discover they are Save, Add to pack, **View on <provider>** (the
    `external` icon, the source site in a new tab, so it's still one click
    away) and Details. Library cards have their own set (see "Library cards").
  - Each inverts on hover, like the chrome, and has a mono `.card-tip`
    label below it after 0.2 s.
  - The row lets the pointer through between its squares. Forms inside it
    are `display: contents`, so a save error's message can wrap onto its
    own line.
  - They replaced the full-width "Save to library" row at the card's foot,
    which the user found in the way.
- **Details:** `.result-details` (`aria-hidden`, because the card already
  holds the same text) rises over the lower thumbnail and stops under the
  corner row. It shows the full title, author, license, source and every
  tag. It has `pointer-events: none`, so a click still opens the source.
  - It shows on hover (behind the hover gate) or on keyboard focus inside
    the card (`:has(:focus-visible)`).
  - It used to show on `:focus-within`, so it stayed up after a mouse
    click on the card or Save. A mouse click leaves no `:focus-visible`, so
    now it goes once the pointer leaves.
  - **Details** (`data-card-details`, `aria-pressed`) keeps it open
    (`data-details="open"` on the card, set by `static/js/card-actions.js`)
    until it's pressed again or Escape is pressed. Kept open, it takes the
    pointer, so a long tag list scrolls.
- **Save to library** (`catalog/partials/save_button.html`), the first
  corner square:
  - A member gets a `<form class="save-slot">` that `hx-post`s the
    provider and ID to `catalog:save` and swaps itself (`outerHTML`) for
    the reply. The square pulses while it runs.
  - The reply is the "In library" square (`in_library.html`: a filled
    check, no logo mark, linking to the library) plus the saved count out
    of band.
  - On a `ProviderError` the reply is `save_error.html`. The square
    becomes Try again (the alert icon in the error colour), which posts the
    same save. The message (`role="alert"`) drops onto its own line under
    the squares, and the hover details are hidden.
  - A result the member already has renders "In library" straight away.
  - A visitor gets a link to sign in, with `next` set to this Discover
    search. So does Add to pack.
- **Sound preview:** a card with a `preview_url` gets a square ink
  `.sound-play` button at the thumbnail's top left, and a 2 px
  `.sound-progress` line along its foot (`catalog/partials/sound_play.html`,
  shared by library cards, both drawers and pack items since 2026-11-06).
  `static/js/sound-preview.js` (delegated, loaded in `base.html`) plays one
  preview at a time with `new Audio(url)`. It sets the nearest
  `[data-sound-card]`'s `data-sound` (`loading`, `playing`,
  `paused`, `idle`, `error`) and `--progress`, and keeps the button's
  `aria-pressed` and `aria-label` in step. A preview that can't load
  disables its button ("Preview unavailable"). The sound stops when its
  card leaves the page (`htmx:afterSwap`) or the dialog it plays in closes.
- **License symbols** (user request, 2026-11-06): the meta line shows the
  license as its symbols (`license_symbols.html` with `small`, 13 px) beside
  its short name (`.result-license`), from the `license_info` template filter.
  The details add "Commercial": the verdict and why.

**Side panel: license filters** (user request, 2026-11-06), like the
library's: `#discover-filters` with a "Filters" title (and **Clear** while
any is on), then two `.filter-group`s: **Commercial use** ("Allowed only")
and **License** (one chip per license but "unknown", each with its symbols,
`.filter-chip.has-icons`). The chips belong to the command bar's form
(`form="discover-search"`) and carry `data-autosubmit`, so `shell.js`
submits it (boosted) as soon as one changes; without JavaScript a
`<noscript>` Apply does. While any is on, `#discover-filter-note` above the
shelves says which ("Only CC0 or CC BY, commercial use results.") with
Clear filters. A shelf the filters rule out says "Filtered out" and "Every
Poly Haven asset is CC0, which your filters leave out." with Clear filters;
an empty filtered shelf suggests other licenses.

**Discover's drawer** (user request, 2026-11-06): `<dialog
id="discover-drawer" class="drawer-dialog">`, once on the page, filled by a
card's title (`catalog/partials/discover_drawer.html`) and opened by
`entry-drawer.js`, which now works on the page's one `dialog.drawer-dialog`.
Like the library drawer: a sticky head ("Discover result", View on
<provider>, Open as page, Close), the cropped mark, `transition:false`
swaps. The body (`catalog/partials/discover_detail.html`, also the full
page `catalog/discover_asset.html` in a centred 48 rem column with "Back to
Discover"):

- the thumbnail over the type icon (a sound's play button on it), the type
  and provider, title, author and community rating
- `#preview-actions`: **View on <provider>** (`btn-primary`, new tab), Save
  (`catalog/partials/preview_save.html`: posts `slot=drawer` and swaps
  itself for "In your library", inverted, or Try again with the message; a
  visitor gets Sign in to save, back to their search) and Add to pack (the
  page's pack picker, `data-picker`)
- **License**: large symbols, the license (its deed link) and title, the
  credit chip, the summary with What it means, "Can I use it?"
  (`license_uses.html`) and the attribution
- **Details**: the source link and tags; **Downloads**: each variant's
  resolution and format badges, package, file count and size
  (`.preview-variants`), with a note that saving lets you pick and download
- a `ProviderError`: the alert with Retry (into the drawer) and Go to
  <provider>
