# HTMX, scripts and page transitions

## Setup

- `{% htmx_script %}` (django-htmx) loads htmx 2; `HtmxMiddleware` sets
  `request.htmx`.
- **Boosted navigation:** `<body hx-boost="true">`. Links and forms fetch
  the next page and swap its body in, so the stylesheet, fonts and scripts
  stay loaded (full reloads made the top bar flash). After a redirect htmx
  puts the final URL in the address bar.
- **htmx-config meta:** `historyCacheSize: 0` (Back refetches instead of
  restoring a stale snapshot); `[45]..` responses swap in, so a 404 or 403
  shows instead of a dead click; `globalViewTransitions`.

## Rules

- **Fragment or page:** a boosted request also carries `HX-Request`. A
  fragment view checks `request.htmx and not request.htmx.boosted`, and
  pages with history also skip `request.htmx.history_restore_request`
  (Back after a swap needs the whole page).
- **CSRF:** `<div id="app" hx-headers='{"X-CSRFToken": "…"}'>` sends the
  token with every HTMX request. It sits on `#app`, not `<body>`, because a
  swap replaces `#app` but keeps `<body>`, and Django rotates the token at
  sign-in. Never exempt a view from CSRF. Scripts posting outside htmx read
  the `csrftoken` cookie (`entry-drawer.js`) or use `htmx.ajax`, which
  inherits the header (`pack-sort.js`).
- **Scripts load once**, in `base.html`'s `<head>`, for every page. A swap
  doesn't run a new page's `<head>`, so there's no per-page scripts block.
  Scripts listen on `document` (delegation) or set up via `htmx.onLoad`,
  never by binding to elements a swap replaces: `shell.js`,
  `password-toggle.js`, `sound-preview.js`, `card-actions.js`,
  `entry-drawer.js`, `entry-files.js`, `bundle-download.js`, `pack-sort.js`,
  `scroll-ruler.js`, `ambient.js`, `motion.js`.
- **Versioned URLs:** the stylesheet and every script load through
  `{% versioned_static %}` (`shell_tags.py`), adding `?v=<last change>`.
  On `htmx:beforeSwap`, `shell.js` compares the arriving page's `<head>`
  `?v=` URLs with the loaded ones; for a GET naming different ones it
  cancels the swap and loads the URL in full. Why: a boosted tab otherwise
  keeps running stale CSS and JS until a hard reload.
- **Preserved:** `#brand-link` is `hx-preserve` (a rebuilt image left a
  blank frame), and its `<img>` has `width`/`height`.
- **Out of band:** the saved count, provider status, cards behind a drawer
  and similar side effects come back with `hx-swap-oob`. Load more appends
  with `<ul hx-swap-oob="beforeend:#…">` (htmx appends the children).
- **No transition for overlays:** drawers, pickers and the builder say
  `transition:false` in `hx-swap`. Why: under global View Transitions the
  whole `#content` faded behind an opening drawer.

## Page transitions

Boosted swaps run through the View Transitions API.

- `#content` (`view-transition-name: content`) fades up and out over
  0.16 s, then the new page rises in over 0.34 s; the rest crossfades in
  0.18 s.
- Each bar's current item has a shared name (`current-act` in the sidebar,
  `current-row` for a page's panel row, `current-chip` in the title bar), so
  the mark glides between items over 0.32 s.
- **A name used twice on a page cancels the whole transition.** Only one
  item per bar may be `aria-current`;
  `test_each_transition_name_is_used_once_per_page` checks.
- **Fragment swaps** (filters, Load more, builder saves): `motion.js` marks
  each swap on `htmx:beforeTransition`: boosted navigation clears `<html
  data-swap>`, anything else sets `fragment`, and `#content` crossfades in
  place over 0.2 s (opacity only). Nothing calls `startViewTransition`
  itself.
- Browsers without View Transitions just swap; reduced motion turns them
  off.
