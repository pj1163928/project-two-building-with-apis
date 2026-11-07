# Motion and reduced motion

`source.css`'s "Motion" section plus `static/js/motion.js`, which only
marks state for the CSS. Monochrome throughout: ink and the grey tokens,
never a type or drop colour. Transitions between pages:
[htmx.md](htmx.md#page-transitions).

## Branding motion

- **Wordmark:** wipes in from the left on load (`brand-wipe`, a
  `clip-path` on `#brand-link`). Every 12 s from 3 s, the letters dim to
  60 % (`brand-dim`) while an ink band crosses them (`.brand-shine`, masked
  to the wordmark via `--word-url`). The shine hides while the chip is
  hovered or focused (the chip inverts).
- **The mark cuts in** diagonally on load (`.hero-mark`, `mark-cut`).
- **Full loads only:** both intros match `html:not([data-booted])`;
  `motion.js` sets `data-booted` after 1.6 s, so a boosted swap never
  replays them.
- **Parallax:** `.hero-atmosphere` sinks at 0.4× the scroll over the first
  60 rem (a scroll-driven animation on `#content`'s `--page` timeline),
  inside `@supports (animation-timeline: scroll())`. `.content-stage` is
  `overflow-y: clip`, so the sinking layer never adds blank space under the
  footer. On the main page the layer fades in at the top as well, and the
  mark sits 4 rem into it, so it has no hard edge.

## The logo loader

`partials/loader.html`, `.ax-loader`: the mark in grey with a light band
sweeping across (`--loader-band`, `loader-sweep`), with a label or a
screen-reader "Loading". It carries no role (the loading region says so).
**It's the only loading indicator: no spinners.**

- **Status bar:** `#status-loader .status-mark` sweeps while any htmx
  request runs. `motion.js` counts from `htmx:beforeSend` to the request's
  `loadend`, shows it after 150 ms (`<html data-busy>`) and sets
  `aria-busy` on `#content`.
- **A pending shelf:** six `.result-skeleton` cards (a thumbnail block and
  two lines, fading 10 % per card) under `.shelf-loading-badge`, a square
  frosted box centred over them with the loader at 2.5 rem and "Searching
  <provider>". The badge sits beside the `<ul>`, never on a tile, and is
  `aria-hidden` (the shelf is `aria-busy`).
- **In place:** Load more's "Loading…", the picker's "Loading your packs…"
  (`card-actions.js`), the drawer's "Saving…" (`entry-drawer.js`).
- **Never on a thumbnail:** a card's corner Save keeps its pulse; the
  status bar shows the loader.

## Cards

- **Spotlight:** result and library cards, type tiles, gallery cards, pack
  cards and rows. A `::before` holds a 16 rem pool of ink (9 %, 6 % light)
  at `--spot-x` / `--spot-y` on the card `motion.js` marks `data-spot`.
  Mouse only, behind the hover gate, `pointer-events: none`, above the
  thumbnail but under details and corner actions (z-index 1).
- **Lift:** result, library, gallery and pack cards rise 4 px on hover onto
  `--lift-shadow`; a result's thumbnail eases in 7 % over 0.6 s. The edge
  keeps its monochrome hover (no type-coloured glow). The hovered card is
  `z-index: 2` so corner tips stay above neighbours, and a 4 px `::after`
  strip keeps the hover once it has risen off the pointer.
- **Blur up:** cards in `.result-grid`, `.gallery-grid`, `.pack-grid`,
  `.pack-rows` rise out of a 10 px blur (`card-in`, 0.5 s), 40 ms apart,
  counted within each 12 (`:nth-child(12n+k)`) so a Load more batch
  staggers from its own first card. Fill is `backwards` only.

## The main page's cover

With a fine pointer (`@media (hover: hover) and (pointer: fine)`), the
main page (`#app:has(#home-orbit)`) opens on its cover alone, filling the
window above the status bar (`--cover-offset`), with the title bar and
sidebar tucked away. Touch screens keep both bars; other pages are
unchanged.

- `motion.js` sets `<html data-cover="past">` once the cover's bottom edge
  rises above the window's middle and clears it below 60 % (the gap stops
  flicker), listening for scroll in the capture phase and after each swap.
- On the cover the bars still float in while the pointer rests on the edge
  they left (a 0.75 rem `::after` strip, behind the hover gate) or focus is
  inside. The sidebar floats under the title bar, so showing it shows both.
- **In:** the title bar glides down (0.6 s), the sidebar follows 0.08 s
  later, then their items fade and slide in one after another (`--chrome-i`,
  35 ms apart). **Out:** items fade at once, bars slide off after 0.3 s.
- **Nothing shifts:** the bars float (fixed); the stage keeps the sidebar's
  room (`--side-reserve`, 16 rem / 3.5 rem), and the cover is pulled back by
  half of it (`.home-hero { left }`) to stay centred.
- **The orbit answers the scroll** (in the parallax's `@supports` block):
  rings turn on (`orbit-scroll-turn`: 28°, 42°, 58° inside out, reverse
  rings the other way), each texture counter-turns (`orbit-scroll-unturn`),
  the stage eases to 1.16× (`orbit-scroll-zoom`).

## Reduced motion

- A blanket rule (`*, *::before, *::after { animation: none !important;
  transition: none !important; scroll-behavior: auto !important; }`) on
  top of the per-component list, which stays.
- **Every entry animation runs from a `from` state to the element's own
  style**, so with nothing animating, the content shows at rest. Every
  animation must name real keyframes (tested).
- The spotlight isn't lit; a loader's mark holds still in `fg-secondary`
  (that rule comes after the loader's own); the orbit and ruler stay still.
- htmx starts a View Transition only where `document.startViewTransition`
  exists; the parallax needs scroll timelines. Everything else is plain CSS.
