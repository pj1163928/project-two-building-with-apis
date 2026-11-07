# The shell, layout and shared partials

`templates/base.html`, `static/js/shell.js`, and the layout rules every
page shares.

## Parts

| Part | id | Notes |
|---|---|---|
| Title bar | `title-bar` | `h-12`. Left to right: the wordmark (`h-8`, home), a divider, **Home** (`#home-button`, the only Home chip), "TOOLBOX", the breadcrumb (`{% block breadcrumb_nav %}`, emptied on Home), then the theme switch and account chips. Every item is a square `h-8` chip (`.bar-item`, `.crumb`) with 16 px icons. Sign-out is a POST form |
| Sidebar | `side-panel` (with `activity-bar` inside) | One column. From the top: an `h-14` slot with the panel toggle and `{% block panel_title %}` (`.sidebar-title`, "Explorer"); `nav#activity-bar` (Discover, Library, Packs, Attribution); the page's own panel (`.side-panel-inner`, `{% block side_panel %}`); an Account nav at the foot. Each entry is an `.act.act-row` (`h-11`): a 3.5 rem `.act-icon` cell, `.act-label`, and a `.tip` tooltip. `relative z-20` so tooltips sit over the content. A view sets `extra_context = {"active_nav": "<key>"}` to mark its entry `aria-current="page"` |
| Content | `content` | `data-drop` = `active_nav`, `data-surface` from `{% block surface %}`. `.content-stage` holds the ambient glow, the mark, `{% block content %}` in a `px-8 lg:px-12 pt-14 pb-12 space-y-8` wrapper, then `page-footer` (`.brand-signature`: "Built for Axcenity Engine", a small wordmark, "Axcenity Studios · 2026") |
| Status bar | `status-bar` | Monochrome. Each provider's last status (`partials/provider_status.html`): ink dot OK, alert icon error, muted dot unknown, words in `title` and screen-reader text. The saved count (`partials/saved_count.html`, `#saved-count`) for members only, re-sent out of band after each save. The loader mark (`#status-loader`) |

## Sidebar behaviour

- **Collapse:** an inline `<head>` script sets `<html data-panel="open|collapsed">`
  before first paint from `localStorage["ax-panel"]` (phones default to
  collapsed). `shell.js` wires `#panel-toggle` and `aria-expanded`; the
  toggle holds `.when-open` / `.when-collapsed` icons.
- **Animation:** 16 rem open, 3.5 rem strip collapsed; the icon cell is
  3.5 rem in both, so icons never move. Collapsing: width over 0.42 s
  ease-out, labels fade at once, the page's panel fades and drifts left then
  becomes `visibility: hidden` (out of the tab order). Expanding: 0.5 s,
  labels on a 0.1–0.2 s stagger (`--row-delay`), panel 0.15 s later.
  `data-panel-ready` is set after the first frame so nothing plays on load.
  Reduced motion turns it off.
- **Nothing on the `<aside>` clips** (tooltips sit outside it); each label
  clips itself. So anything absolutely positioned in the side panel needs a
  positioned parent inside it: `.filter-chip` is `position: relative` so its
  `sr-only` input stays in the chip. Why: unpositioned hidden inputs
  stretched the document below the window.
- **Tooltips** (`<span class="tip" aria-hidden="true">`) show only while
  collapsed, sliding out after 0.2 s; the link's `aria-label` is the name.

## Chrome interaction rules

- **Hover is an inversion:** chrome (activity entries, the toggle, panel
  rows, title-bar chips) turns ink with `on-ink` content; the wordmark chip
  inverts its image. `btn-primary` inverts with an edge; plain `btn`s turn
  ink. The `.btn` rules sit outside any layer to beat DaisyUI's hover tint.
  Never put a text-colour utility on a chip (it outranks hover); use a
  component class like `.bar-item-app`.
- **Hover gate:** every chrome `:hover` rule is prefixed `html[data-pointer]`,
  which `shell.js` sets only after the pointer really moves (> 4 px) on the
  current page, and re-arms after every swap. Why: after a click the next
  page loads under a still cursor and the browser re-applies hover, so
  chips flipped and tooltips slid out on arrival. `:focus-visible` isn't
  gated. **Put every new chrome hover rule behind the gate.**
- **Current page:** sidebar entry and a page's own `.panel-row`: ink text,
  a lighter fill, a 2 px ink bar on the left, semibold. Title-bar chip: ink
  text, a fill, a 2 px inset underline. One `aria-current` per bar.
- **Square corners:** no `rounded-*` in the chrome (chips, Sign up, the
  toggle, the hero search, `.btn-quiet`).
- **Label-to-icon swap:** "HOME", "TOOLBOX" and crumbs are `.chip-swap`
  chips (`.chip-label` + `.chip-icon` in one grid cell, so width holds).
  Build crumbs with `partials/crumb.html` (`href`, `label`, `icon`,
  `current`).
- **Title-bar alignment:** wrap chip text in a `<span>`; its 4 px
  `padding-top` puts JetBrains Mono caps on the wordmark's centre line.

## Ambient glow

One translucent layer through the whole page, like lava-lamp wax.

- `<div class="ambient" data-ambient>` is the first child of
  `.content-stage` (`flex: 1 0 auto`), so it spans top to footer and
  scrolls with the page; `#content` clips it.
- `static/js/ambient.js` places drops on load and each swap
  (`htmx.onLoad`): one per 650 px band (a second in some bands on wide
  screens), up to 22, each 620–1300 px across with its own shape, a
  two-colour gradient from the page's drop tokens (light off-centre via
  `--hx`, `--hy`), blur, opacity, three drift waypoints, wobble and a random
  start. A growing page gets drops for the new part (`ResizeObserver`).
- **Transforms only:** `.ambient-blob` drifts (`ambient-drift`), stretching
  while travelling (`--thin`, `--tall`) and squashing at turns (`--flat`,
  `--squat`); `.ambient-drop` wobbles (`--wa`, `--wb = 2 - --wa`, volume
  kept); two `.ambient-shell`s follow 0.5 s and 1 s behind.
- **Strength:** 34 % on work pages (1.15× slower), 52 % on showcase; 24 %
  and 32 % in light (multiply). Reduced motion keeps the arrangement still.
  No JavaScript: no glow, only the dot grid (`.grid-bg`,
  `background-attachment: local`). `.brand-signature` has a drop shadow.

## Two surfaces: showcase and work

`<main id="content" data-surface>` from `{% block surface %}`, default
`work`. **New pages are work surfaces unless they're for browsing.**

- **Showcase** (Home, Discover): stronger glow, a soft top light, an
  oversized cropped `.hero-mark` (`min(46rem, 62%)`, 5 %) top right, full
  headlines.
- **Work** (everything else, sign-in included): calmer glow, a smaller
  mark (`min(22rem, 30%)`, 6 %) in the corner, `compact` headers; header,
  controls and content in one `space-y-5` section.
- `.hero-atmosphere` comes after `.ambient`, so the glow never covers the
  mark.

## Page widths

Two shapes only:

- **Full width** (inside the shell's `max-w-[1500px]`): pages that browse
  or work on a collection: Discover, the library, Your packs, the builder.
- **A centred column** for everything narrower: `width: 100%`, a
  `max-width`, `margin-inline: auto`, never pinned left. Today:
  `.entry-layout` (76 rem), `.attribution` (64), `.pack-page` (60),
  `.discover-asset-page` (48), Account pages and New pack
  (`max-w-3xl mx-auto w-full`), `.remove-page` (30). Add a new column
  page's class to `test_every_column_page_is_centred_like_the_rest`.

**Reuse before inventing:** `.work-toolbar` (a page's controls),
`.builder-section` (a titled box), `.panel-row` + `.panel-row-icon` (side
menu row), `.filter-group` / `.filter-chip` (filters), `.status-chip`,
`.file-badge`, `.card-action`, `btn btn-quiet btn-sm rounded-none`
(secondary actions), one `btn-primary` per area. Item rows (`.pack-item`)
put the thumbnail in the middle of the row, with first text line and
actions on one top edge.

## Shared partials

- `partials/page_header.html` (`label`, `heading`, `lead`, `compact`): on a
  section page two columns (`.page-hero.has-glyph`): the section glyph,
  then `.page-hero-text`: a kicker row (small mark, micro-label, a fading
  `.page-hero-rule`), a `.headline` (`text-[2.25rem] md:text-[2.75rem]`; 2rem
  compact) and a 15 px lead (14 compact). Headline `max-w-3xl`
  (`max-w-2xl` compact), lead `max-w-xl`.
- `partials/empty_state.html` (`title`, `body`, `link_url`, `link_text`): a
  solid `bg-surface` panel, `border-line-strong`, `py-16`.
- `partials/form_fields.html`: form-wide errors first (`#form-errors`
  `.form-alert`, `role="alert"`); each field's errors under it in
  `<ul id="<auto_id>_error" class="field-errors">` matching Django's
  `aria-describedby`; help text `<auto_id>_helptext`; password inputs in
  `.password-field` with a `.password-toggle` (`password-toggle.js`,
  `aria-pressed`); `forgot_url` adds "Forgot password?".
- `partials/icon.html` (`name`, `size`). `partials/crumb.html`.
  `partials/loader.html` ([motion.md](motion.md)).
- **Side-panel rows:** every `.panel-row` starts with a 16 px
  `.panel-row-icon` and may end in `.panel-row-count`. A foldable group is
  `<details class="panel-fold" data-remember="…">` with a `.panel-row`
  summary, `.panel-fold-chevron` and `.panel-fold-rows`. Each
  `.filter-group-title` has a 13 px icon (`FilterGroup.icon`).
  `test_every_side_panel_row_has_an_icon` checks.

## Scroll ruler

On every page, from 80 rem (`hidden xl:flex`), with
`static/js/scroll-ruler.js`.

- `nav#scroll-ruler` (`aria-label="Sections on this page"`,
  `hx-boost="false"`) is fixed down the content's right edge. The content
  and footer (`.content-gutter`) get 6 rem right padding from 80 rem (an
  unlayered rule, as `lg:px-12` would beat a component one).
- **Scale** (`partials/ruler_scale.html`): a minor tick every 2 %, a
  numbered major every 10 %, an ink fill and a cursor (`--ruler-progress`).
  Monochrome.
- **Index:** each page lists sections in `{% block ruler_sections %}`, one
  `partials/ruler_entry.html` (`target`, `label`) each, **under the same
  `{% if %}` as the section**, so an entry exists only when its section
  does. Default: Top (`#page-top`) and End (`#page-footer`). Numbers are a
  CSS counter. Every `[id]` in the content has `scroll-margin-top: 1.5rem`.
- Without JavaScript each entry is a plain `#id` anchor. With it, the
  script follows `#content`'s scroll and each swap: the fill, entries placed
  level with their sections (`--at`, `[data-placed]`, at least 28 px
  apart), missing sections hidden, `aria-current="true"` on the one in view,
  smooth scroll (instant under reduced motion), focus and the `#id` in the
  address bar.
