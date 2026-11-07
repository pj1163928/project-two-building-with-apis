# Colour, light and dark, fonts and branding

All colour lives in `styles/source.css`. `tests/test_theme.py` and
`tests/test_shell.py` enforce every rule here.

## The palette

- `@theme { --color-*: initial; }` drops Tailwind's palette and
  `@plugin "daisyui" { themes: false; }` drops DaisyUI's themes. The only
  theme is `axcenity` (`<html data-theme="axcenity">`).
- **Utility colours** (from the editor's palette): `app`, `panel`,
  `surface`, `elevated`, `inset`, `control`, `control-hover`,
  `control-active`, `line`, `line-strong`, `fg`, `fg-strong`,
  `fg-secondary`, `fg-weak`, `fg-muted`. `white` and `black` exist, but
  chrome never uses them.
- **Contrast tokens:** `ink` (white on dark, `#18181B` on light) for hover
  inversion, current-page marks, tooltips and the marks; `on-ink` for what
  sits on ink; `shade` behind text over the glow and for backdrops and
  shadows. White is allowed only in highlight `radial-gradient`s. The dot
  grid reads `--grid-dot` (ink at 4 %, 7 % in light).
- **DaisyUI roles:** `primary` is near-white with dark text in dark mode
  and near-black with white text in light; `btn btn-primary` is the main
  action. `success`, `warning`, `error` are the editor's status colours.
  `info` is grey so it can't be mistaken for the HDRI blue.

## Type colours: asset type only

`texture`, `hdri`, `model`, `sound` (e.g. `text-texture`), each with a dark
and a light value. Tailwind emits only used tokens, so write classes in
full. They may appear only on:

- Discover's type tiles (icon and the bar under the current tile)
- an asset's type icon and its fallback icon: result cards, library cards,
  both drawers, an entry's page, builder items, pack-page items, Add from
  my library rows, gallery mosaic tiles
- the orbit hero's texture rings (`border-texture`) and tile icons, never
  its grey guide rings

Never in the chrome, never elsewhere in a page's content.

## Page drop colours: the one exception

Each page's ambient glow ([shell.md](shell.md#ambient-glow)) uses three
vivid colours chosen by `#content[data-drop="<active_nav>"]` rules. They
appear in those rules and nowhere else, never in bars or the side panel,
and never match a type colour. `static/js/ambient.js` names only the tokens
(`var(--drop-a)`…), never a hex value. (The tests still call them
`PAGE_PASTELS`.)

## Light and dark

- **The choice:** System, Light or Dark, stored in the `ax-theme` cookie
  (`accounts/theme.py`) for visitors and members. The server renders
  `<html data-scheme-choice="…">` and, for Light or Dark, `data-scheme`, on
  first paint. For System an inline `<head>` script sets `data-scheme` from
  `matchMedia("(prefers-color-scheme: light)")` before first paint and
  follows it live. Without JavaScript, System is dark.
- **Setting it:** the title bar's `#theme-toggle` (monitor, sun or moon)
  steps System → Light → Dark; Settings' Appearance chips pick one.
  `shell.js` switches at once, writes the cookie (a year, `SameSite=Lax`)
  and keeps every switch in step. Without JavaScript both are forms posting
  `choice` to `accounts:theme`.
- **Dark** is the default (the `@theme` values). **Light** is
  `html[data-scheme="light"] { … }`: a light storm grey (app `#BEC0C2`,
  panel `#CACCCE`, surface `#D3D5D7`), darker text, lines and status
  colours. Body text 10:1 and secondary 6.6:1 on the panel; every text and
  status colour at least 4.5:1 even on the bars (`test_theme.py` checks).
  `shade` is `#2B2D31`, so shadows darken rather than glow.
- In light mode the type colours are the engine's on-light accents
  (`#A8460B`, `#3451D1`, `#1C7547`, `#6741D9`), over 3:1 on the grey; the
  glow blends with `multiply` instead of `screen` at lower strength; the
  white wordmark is inverted through `--logo-filter`.

## Fonts

Served from `static/fonts/`, never a CDN. Sources, pins and licences:
[static/fonts/SOURCES.md](../../static/fonts/SOURCES.md).

| Use | Family | How |
|---|---|---|
| Body | Inter | Default (`font-sans`) |
| Page headlines | Plus Jakarta Sans 700, `-0.025em`, balanced | `.headline` |
| Other display text | Plus Jakarta Sans 800 | `.display` or `--font-display` |
| Micro-labels | JetBrains Mono, uppercase | `.micro` |

- **No late swap:** `base.html` preloads JetBrains Mono Regular, Inter
  Regular and Medium, and Plus Jakarta Sans. JetBrains Mono and Plus
  Jakarta Sans use `font-display: block` (with `swap` the mono labels
  changed width as the font arrived); Inter swaps.
- **Font gate (first load only):** an inline `<head>` script sets
  `<html data-fonts="loading">` until JetBrains Mono is ready (capped at
  3 s), and CSS hides the title-bar chips meanwhile. Why: otherwise their
  fill and underline paint with no text, a stray white bar.

## Branding

- Logo files in `static/brand/` are copied from the engine repo's
  `assets/branding/`. The identity is black, white and grey only.
- **Wordmark:** `wordmark-white.png` in the title bar (`#brand-link`,
  links home) and a small `w-20` `.word` in the footer's brand signature.
  No giant footer watermark.
- **Mark:** `.hero-mark` on every page, above the glow; `.drawer-mark` in
  each drawer. The ghost mark is the empty state. `favicon-32.png` is the
  favicon; `icon-256.png` is unused.
- `.mark` and `.word` are CSS masks taking `currentColor`; their URLs come
  from `{% static %}` through `--mark-url` and `--word-url` on `<html>`.
- **Never put the logo on a provider thumbnail**, and never use it as a
  thumbnail fallback (the type icon is). "In library" is a filled check
  with no mark.
- **Section icons:** each section's line icon (`PAGE_ICONS` and the
  `page_icon` filter on `active_nav`, `catalog/templatetags/shell_tags.py`):
  Discover magnifier, Library books, Packs box, Attribution license,
  Account person, Settings gear. The main page has none.
  - `.page-hero-glyph`: the header's left column (8.5 rem, 6.5 compact,
    4 on a phone), the icon in `fg-secondary` with 1-of-24 strokes in a
    square `line-strong` frame on a 3 % ink fill, ink corner ticks top left
    and bottom right.
  - `.side-watermark`: the same icon at 13 rem in the open sidebar's bottom
    right corner (2.25 rem past the edge), 6 % ink (8 % light), under the
    rows (`z-index: -1`; it clips itself so tooltips still stick out). It
    fades out when the sidebar collapses.
  - Both draw in on each page arrival (`watermark-draw`, 2 s). Monochrome
    only.
