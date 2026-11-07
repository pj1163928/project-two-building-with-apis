# Main page (templates and HTMX)

`packs/home.html`, a showcase surface. Server side:
[../architecture/home-and-demo.md](../architecture/home-and-demo.md). The
cover's scroll behaviour: [motion.md](motion.md#the-main-pages-cover).

## From the top

- **Orbit hero** (`#home-hero`, `#home-orbit`,
  `packs/partials/hero_orbit.html`): fills the first screen
  (`min-height: calc(100dvh - 4.5rem)`) from the content's top edge (an
  unlayered `margin-top`, as `space-y-8` would reset a component one). The
  text is centred in front (`#home-hero-text`: header, search and buttons on
  a soft pool of the panel colour) and comes first in the HTML, so the
  keyboard reaches the search before the orbit.
  - **Search:** `#hero-search`, a square 56 px bar sending `q` to
    `catalog:discover`. Its Search is the page's only `btn-primary`. Under it
    `.btn-quiet` buttons: Browse Discover and Open your library (members) or
    Sign up (`#home-signup`) and Sign in (`#home-signin`).
  - **Rings:** a square stage wider than the window (`min(max(96vw,
    150dvh), 140rem)`, 160vw on a phone). Faint grey `.orbit-guide` rings
    (some dashed); over them up to three texture rings (46, 66, 86 %), each
    line a 40 % `::before` in `border-texture`, turning once per `--spin`
    (90, 120, 150 s), neighbours opposite (`.is-reverse`). The orbit fades
    down its lower half (a mask on `.orbit`, whose layer reaches past the
    hero's sides) and `.content-stage` is `overflow-x: clip` here.
  - **Tiles:** textures only, `--tile` rem (`OrbitRing.tile_rem`; × 0.62 on
    a phone). `.orbit-arm` (`--angle`) turns `.orbit-thumb` to its place;
    `.orbit-face` counter-spins to stay upright. A texture with an image is
    a cut-out (`.is-cutout`: the sphere render on its transparent
    background, 1.3×, no tile, a shape-following drop-shadow); with no image
    (or a failed one) the framed tile and icon show (`:has(img)`). Images
    load eagerly (`referrerpolicy="no-referrer"`, `data-thumb-fallback`).
    Each tile links to the newest public pack holding it, named in
    `aria-label` and `title`.
  - **Pausing:** hovering a tile (`.orbit:has(.orbit-thumb:hover)`) or focus
    inside pauses every ring and face; reduced motion stills them. Only
    tiles take the pointer.
  - **No logo in the orbit**, no legend, no caption. The page's `.hero-mark`
    moves below the hero (`translate: 0 calc(100dvh - 4.5rem)`).
  - **Fallback** (`.orbit.is-fallback`): six texture-icon tiles on the outer
    ring, opening Discover's textures.
- **How it works** (`#home-steps`, visitors only): "Four steps from search
  to engine.", four `.home-step` boxes (01 Discover, 02 Save, 03 Pack, 04
  Export: number in mono, monochrome icon, title, one line), and a note that
  browsing needs no account. No second primary button. Members see neither
  the steps nor any sign-up prompt.
- **Gallery** (`#gallery`, everyone): "Public packs", "See what others have
  built.", then `#gallery-toolbar`, a `.work-toolbar` GET form: search
  (`#gallery-search`) and two `.gallery-control` selects (`type`: Any type
  or "Containing textures"…; `sort`: Newest or Most items). Controls sit in
  the page because the panel starts collapsed here.
  - It `hx-get`s `/` into `#gallery-results` (`outerHTML`, `hx-push-url`) on
    submit, 300 ms after typing, or a select's change. Pager links use the
    same swap. A `<noscript>` Apply submits without JavaScript.
  - **Results** (`packs/partials/gallery_results.html`): "1–12 of N public
    packs", `.gallery-grid`, `#gallery-pager`. Empty states: "No public
    packs yet." (Go to your packs / Sign up); "No public pack matches “q”."
    or "No public pack holds that type yet." with Clear filters
    (`/#gallery`).
  - **A card** (`packs/partials/gallery_card.html`, `.gallery-card`): a 2 × 2
    `.gallery-mosaic` of the first four items (each `.gallery-tile` the
    provider's image over the type icon, square; empty `.is-blank` tiles),
    the title (stretched `.pack-card-link` to the pack's page), "By
    <owner>", tags (`.pack-card-tags`), the type count in mono. Nothing from
    anyone's library; the edge inverts on hover (gated).
- **Scroll ruler:** Toolbox (`#home-hero`), How it works (visitors only),
  Public packs (`#gallery`).

## The side panel starts collapsed here

Whatever the member chose elsewhere (PRD):

- `HomeView` sets `panel_start = "collapsed"`; `base.html` writes it as
  `data-panel-start` on `<html>` (first paint) and on `#app` (boosted swaps
  replace `#app`, not `<html>`). The head script uses it ahead of
  `localStorage["ax-panel"]`.
- After each boosted swap, `shell.js`'s `applyPanelStart()` sets the panel
  to the arriving page's start or back to the saved choice. The toggle
  still works here and still saves.
