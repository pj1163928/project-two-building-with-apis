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
- **Light and dark:** the site follows the system's colour scheme.
  - Dark is the default: the `@theme` values.
  - `@media (prefers-color-scheme: light)` in `source.css` sets the same
    tokens to the engine's light palette (`crates/editor/src/theme.rs`,
    `Palette::new` with `dark = false`). It's still the one `axcenity`
    theme, just flipped, so every utility and component follows.
  - In light mode, the type colours become the engine's on-light accents
    (`#A8460B`, `#3451D1`, `#1C7547`, `#6741D9`), and the status colours
    its light ones.
  - The drop-glow blobs switch from `screen` to `multiply` blending, at
    40 %, because screen washes out on white.
  - The title-bar wordmark image (white) is inverted through
    `--logo-filter`.
- **Contrast tokens:** `ink`, `on-ink` and `shade`.
  - `ink` is white on dark and `#18181B` on light. Hover inversion,
    current-page marks, tooltips and watermarks use it.
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
  - the same two icons on each item in the pack builder (Phase 7)

  `test_shell.py` keeps them out of the chrome on every page, out of every
  other page's own content, and on library cards and pack items to those
  two icons only.
- **Page drop colours (the one exception):** each page's content area has
  a "water drop" glow in three vivid colours, behind the hero and in the
  footer. The colours are chosen by `#content[data-drop="<active_nav>"]` in
  `source.css` (`<main id="content" data-drop>`). These are decoration
  only. They appear in those rules and nowhere else, never in the bars or
  the side panel, and never match a type colour. This exception to the PRD's "colour only means asset
  type" rule was asked for by the user on 2026-10-30. They started as
  pastels, and the user asked for brighter ones the same day (the tests
  still call them `PAGE_PASTELS`).
- `tests/test_theme.py` fails if `source.css` gains any colour outside this
  palette (dark or light), or uses a drop colour outside the drop-glow
  rules. It also checks the light block against the engine's values.

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
- **Wordmark:** `wordmark-white.png` in the title bar. The footer has two
  `.word`s: a giant full-width `.watermark` at 6 % opacity, filling the
  empty space where future features will go, and a small `w-20` wordmark
  in the brand signature below it.
- **App icon tile:** `icon-256.png` stays in static, but no page uses it.
  The user removed it from the activity bar because the title-bar wordmark
  already links home.
- **Favicon:** `favicon-32.png`.
- `.mark` and `.word` are CSS masks, so the logo takes `currentColor`. The
  image URLs come from `{% static %}` through `--mark-url` and `--word-url`
  on `<html>`.
- The ghost mark is the empty state in `partials/empty_state.html`.
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
| Sidebar | `side-panel` (with `activity-bar` inside) | One column: the activity bar and the side panel merged (user request, 2026-11-05). From the top: an `h-14` slot with the panel toggle and `{% block panel_title %}` (`.sidebar-title`, "Explorer" by default); `nav#activity-bar` with Discover, Library and Packs (`pt-1`, `gap-1`); the page's own panel (`.side-panel-inner`, `{% block side_panel %}`: the Library filters, the Account pages' Profile, Settings and API token rows); and an Account nav at the foot with Account and Settings. Each entry is an `.act.act-row` (`h-11`): a 3.5 rem `.act-icon` cell holding its 20 px icon, its `.act-label`, and a `.tip` tooltip for the collapsed strip, instead of a `title`. The sidebar is `relative z-20` so tooltips sit over the content. A view sets `extra_context = {"active_nav": "<key>"}` to mark its entry with `aria-current="page"` |
| Content | `content` | `data-drop` = the page's `active_nav`. The hero glow (`.page-glow`), then `{% block content %}` in a `px-8 lg:px-12 pt-14 pb-12 space-y-8` wrapper, then the footer (`page-footer`): the drop glow, the faint giant watermark, and the `.brand-signature` row ("Built for Axcenity Engine", a small wordmark, "Axcenity Studios · 2026") |
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

**Drop glow:** `.drop-glow` holds three blurred blobs
(`.drop-blob-a|b|c`, screen-blended at 55 % opacity), each drifting and
scaling on its own path (9 s, 11 s and 13 s), plus ripple rings (`::after`)
that pulse every 6 s. A mask fades it upward. The glow layer itself never
moves, and the blobs are anchored 45 % below the footer's bottom edge, so
no bare strip shows along the bottom. (The first version slid the whole
layer up, which showed as a grey bar shifting along the bottom.)
`.page-glow` is the same layer flipped (`scaleY(-1)`), 26 rem tall, at
40 % opacity and without rings, hanging from the top of the content
behind the hero, so the page reads as one piece. `.brand-signature` has a
dark drop shadow so it stays readable over the brightest ink. Reduced motion stops all of it. It's translucent,
so the dot grid shows through. `.grid-bg` uses
`background-attachment: local`, so the dots scroll with the content.

**Partials:**

- `partials/page_header.html` takes `label`, `heading`, `lead` and
  `compact`. It's the hero: a micro-label, a `.headline`
  (`text-[2.25rem]`, `md:text-[2.75rem]`) and a 15 px lead, `space-y-4`.
  Working pages pass `compact=True`, which gives a `md:text-[2rem]`
  headline, a 14 px lead and `space-y-3`.
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
- **Scripts:** every script loads once, in `base.html`'s `<head>`, for
  every page. A swap doesn't run a new page's `<head>`, so there's no
  per-page scripts block. Scripts listen on the `document` (delegation)
  rather than binding to elements a swap replaces, as `shell.js`,
  `password-toggle.js`, `sound-preview.js`, `card-actions.js` and
  `entry-drawer.js` do.
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

## Two moods: showcase and work

`<main id="content" data-surface>` comes from `{% block surface %}`, which
defaults to `work`. Home and Discover override it with `showcase`.

- **Showcase** (discovery and marketing): the hero glow is 40 rem tall,
  at 75 % opacity, with its ripple rings. A soft light falls from the top
  (an extra background layer under the dot grid). `.hero-atmosphere`
  shows an oversized, cropped `.hero-mark` at 5 % opacity, top right,
  fading downward. The headline is full size.
- **Work** (Library, Packs, Account, Settings): no hero glow and no
  mark. The footer glow is at 35 % opacity, slower
  (22 s) and has no rings. Headers are `compact`. The header, controls and
  content sit in a `space-y-5` section, so they read as one block.

- **Sign-in and sign-up** are work surfaces too, with the same calm
  footer glow. They also leave out the footer watermark (an empty
  `{% block watermark %}`), so the form is the focal point. A brief
  corner-weighted `auth` mood was tried and dropped at the user's request.

New pages are work surfaces unless they're for browsing or discovery.

## Sign-in and sign-up

Both extend `templates/registration/auth_base.html`, which fills the blocks
`auth_heading`, `auth_lead`, `auth_form` and `auth_switch`, and empties
`{% block watermark %}`.

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
- `#library-filters` is the library's own panel in the sidebar, under its
  navigation rows, because the PRD puts the filters there. It shows while
  the sidebar is open. It has `.filter-group`s of
  square `.filter-chip`s: Type, Provider and Status are checkboxes (any
  number on), and Minimum rating is a radio group (Any, 1+ … 5). Tags
  (Phase 4 polish) are checkboxes too, one per tag on the member's saved
  assets from every provider, most used first, each with its count
  (`.filter-chip-count`); an entry needs every chosen tag. With no tags
  yet, the group says where they'll come from. Each chip
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
- **The full page** (`catalog/entry.html`): the same body in a bordered
  `.entry-page` surface, under "Back to your library". The crumbs are
  library / entry, and Library stays current in the bars.
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
  - **License and credit:** the linked license, the attribution, "View on
    <provider>", tags and the saved date.
  - **Files:** one `<details>` per variant ("2K JPG · 2 files · 5.2 MB"),
    opening to each file's link and size.
  - **Packs** *(Phase 7)*: the packs the entry is in (`#entry-packs`),
    each linking to its builder with the item's variant, or "It isn't in
    any of your packs yet."
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

## Packs

*(Phase 7.)* Work surfaces. Every packs page's side panel is
`packs/partials/pack_nav.html`: "Your packs" with a small **New** action
(`.panel-action`), then one `.panel-row` per pack (`#pack-nav-<id>`), the
open pack current. With none: "The packs you create are listed here."

- **Your packs** (`packs/pack_list.html`): the header, a `.work-toolbar`
  with the count and **New pack** (`btn-primary`), then `#pack-list`, a
  `.pack-grid` of `.pack-card`s: Private or Public (a `.status-chip`,
  Public inverted), the item count, the title (its link stretched over the
  card), the intended use (two lines), the tags and the date it changed.
  Empty: "You have no packs yet." with New pack.
- **New pack** (`packs/pack_new.html`): a `novalidate` form through
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
- All the builder's swaps say `transition:false`, so the page doesn't fade
  behind each save.

## Home hero

`packs/home.html` puts a `#hero-search` form directly below the
description. It's a square, 56 px bar that sends `q` to `catalog:discover`,
whose search arrives in Phase 2a. Its Search button is the page's only
`btn-primary`. Under it, Browse Discover and Open your library (members)
or Sign up and Sign in (visitors) are secondary `.btn-quiet` buttons:
outlined, square, and inverted on hover.

## Discover

`catalog/discover.html` is a showcase surface. From the top:

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
| Pending | `aria-busy`, `hx-get` of its own URL, `hx-trigger="load"`, `hx-swap="outerHTML"`, and six pulsing `.result-skeleton`s |
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

- **Whole-card link:** the title's `.result-link` opens the provider's page
  in a new tab, and its `::after` is stretched over the card, so the whole
  card is clickable. Interactive parts (the play button, the corner
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
  - On Discover they are Save, Add to pack and Details. Library
    cards have their own set (see "Library cards").
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
  `.sound-progress` line along its foot. `static/js/sound-preview.js`
  (delegated, loaded in `base.html`) plays one preview at a time with
  `new Audio(url)`. It sets the card's `data-sound` (`loading`, `playing`,
  `paused`, `idle`, `error`) and `--progress`, and keeps the button's
  `aria-pressed` and `aria-label` in step. A preview that can't load
  disables its button ("Preview unavailable"). The sound stops when its
  card leaves the page (`htmx:afterSwap`).
