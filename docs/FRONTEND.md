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
  only the tokens that are used. Each has a dark and a light value.
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
- **Never** put the logo on a provider thumbnail.

## The shell (`templates/base.html`)

| Part | id | Notes |
|---|---|---|
| Title bar | `title-bar` | `h-12`. From the left: the wordmark (`h-8`, links home), a divider, **Home** (`#home-button`, the only Home chip), "TOOLBOX", the breadcrumb, then the account chips on the right. Every item is a square `h-8` chip (`.bar-item`, `.crumb`) with 16 px icons. The breadcrumb sits in `{% block breadcrumb_nav %}`. Home empties that block, because its Home chip already marks the page. Sign-out is a POST form |
| Activity bar | `activity-bar` | A top slot (`h-14`) holding the panel toggle, then Discover, Library, Packs (`pt-1`, `gap-1`), then Account and Settings. Every icon is 20 px and has a `.tip` tooltip instead of a `title`. The bar is `relative z-20` so tooltips sit over the side panel. A view sets `extra_context = {"active_nav": "<key>"}` to mark its entry with `aria-current="page"` |
| Side panel | `side-panel` | `{% block panel_title %}` and `{% block side_panel %}`. It slides shut (see below). The header is `h-14`, the same as the toggle slot, and rows use `.panel-row` (`h-11` with `gap-1` and `pt-1`, like the activity bar), so each row lines up with its icon. Keep these heights in step if either bar changes |
| Content | `content` | `data-drop` = the page's `active_nav`. The hero glow (`.page-glow`), then `{% block content %}` in a `px-8 lg:px-12 pt-14 pb-12 space-y-8` wrapper, then the footer (`page-footer`): the drop glow, the faint giant watermark, and the `.brand-signature` row ("Built for Axcenity Engine", a small wordmark, "Axcenity Studios · 2026") |
| Status bar | `status-bar` | Monochrome. It lists provider names from `config.context_processors.shell`. Member-only data (the saved count) appears only when signed in |

**Side panel collapse:** an inline script in `<head>` sets
`<html data-panel="open|collapsed">` before first paint, from
`localStorage["ax-panel"]`. Phone-width screens default to collapsed.
`static/js/shell.js` wires the `#panel-toggle` button and keeps
`aria-expanded` in step. The toggle holds two icons (`.when-open` and
`.when-collapsed`), and CSS shows whichever fits the state.

**Side panel animation:** collapsing animates the panel's width to 0 over
0.42 s on a smooth ease-out curve. The contents fade and drift left at the
same time, and the panel becomes `visibility: hidden` at the end, so its
links leave the tab order. Expanding is gentler: the width eases out over
0.5 s, the contents fade in 0.08 s later, and the `.panel-row`s slide in on
a 0.1 to 0.25 s stagger (`--row-delay`). `shell.js` sets `data-panel-ready` after the
first frame, so the transition never plays on page load. Reduced motion
turns it off.

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

**Current page:** marked the same way in three places. The activity-bar
entry and the side-panel row get white text, a slightly lighter fill and a
2 px white bar on the left edge, and the row also turns semibold. The
title-bar chip (the crumb, or Home on the home page) gets white text, a
fill and a 2 px white underline (`inset` box shadow).

**Tooltips:** each activity-bar icon holds a `<span class="tip"
aria-hidden="true">`, a white mono label that slides out to the right after
0.2 s. The link's `aria-label` stays the accessible name. `shell.js` swaps
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
  navigation would get a fragment instead of a page. Today every view
  returns a full page.
- **CSRF:** `<div id="app" hx-headers='{"X-CSRFToken": "…"}'>` sends the
  token with every HTMX request. It sits on `#app`, not `<body>`, because
  a swap replaces `#app` but keeps `<body>`. Django rotates the token at
  sign-in, so the header has to come from the newest page. Never exempt a
  view from CSRF.
- **Scripts:** every script loads once, in `base.html`'s `<head>`, for
  every page. A swap doesn't run a new page's `<head>`, so there's no
  per-page scripts block. Scripts listen on the `document` (delegation)
  rather than binding to elements a swap replaces, as `shell.js` and
  `password-toggle.js` do.
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
  `current-act` in the activity bar, `current-row` in the side panel, and
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
so the layout is set before any assets arrive. They're disabled until
Phase 4 wires them up, and while the library is empty.

- `#library-toolbar` (`.work-toolbar`, square and bordered) sits directly
  under the header. It holds the search (`.toolbar-search`, `q`), the sort
  (`.toolbar-field`, the PRD's four sorts) and a grid/list view toggle
  (`.toolbar-seg`).
- `#library-filters` sits in the side panel, below the usual rows,
  because the PRD puts the filters there. It has `.filter-group`s of
  square `.filter-chip`s: Type, Provider, Status and Minimum rating,
  inside a `<fieldset disabled>`.
- `#library-results` holds the empty state now, and the grid later.

## Home hero

`packs/home.html` puts a `#hero-search` form directly below the
description. It's a square, 56 px bar that sends `q` to `catalog:discover`,
whose search arrives in Phase 2a. Its Search button is the page's only
`btn-primary`. Under it, Browse Discover and Open your library (members)
or Sign up and Sign in (visitors) are secondary `.btn-quiet` buttons:
outlined, square, and inverted on hover.
