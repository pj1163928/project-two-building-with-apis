# Discover (templates and HTMX)

`catalog/discover.html`, a showcase surface. Server side:
[../architecture/discover.md](../architecture/discover.md).

## The page

- **Header**, then the **command bar** (`#discover-search`, `.command-bar`):
  a GET form with a hidden `type` and `q` (`#discover-search-input`). The
  home hero search lands here. The input has `data-search-shortcut`;
  `shell.js` focuses it on `/` unless the cursor is in an input, textarea,
  select or editable element, or Ctrl, Alt or Meta is held. `.command-key`
  shows the hint.
- **Type tiles** (`#type-tiles`): four `.type-tile` links keeping the
  query. The current one is `aria-current="true"`, never `"page"` (that
  belongs to the bars). Its icon and 2 px `.type-tile-bar` take the type
  colour; the classes are written in full in `catalog/discover.py`
  (`KindTile`).
- **Random pick** (no query): `#featured-pick` shows "Random pick",
  "<Type> for “<pick>”", Shuffle and the providers hint.
- **Shelves:** `#discover-shelves`, one `catalog/partials/shelf.html` per
  provider.
- **Scroll ruler:** Search, Types, then each `#shelf-<provider>`.

## Shelves

`<section id="shelf-<provider>">`, replaced whole.

| State | What shows |
|---|---|
| Pending | `aria-busy`, `hx-get` of its own URL, `hx-trigger="load"`, `hx-swap="outerHTML"`, the loader badge over six skeletons ([motion.md](motion.md#the-logo-loader)) |
| Results | `.result-grid` (`#shelf-<provider>-results`) of result cards, then Load more when the page came back full |
| No matches | `.shelf-empty`: "No <provider> matches for “q”." |
| Failed | `alert alert-error` (`.shelf-alert`, square, error colour only on the icon) with the `ProviderError` message and Retry, which `hx-get`s the shelf into `#shelf-<provider>` |
| Filtered out | "Filtered out" and e.g. "Every Poly Haven asset is CC0, which your filters leave out." with Clear filters |

- The header shows a number (`01`), the provider, a rule, and "Searching",
  "Unavailable" or the count. Every state ends with a `.shelf-credit` line
  ("Assets from ambientCG · CC0", "Powered by Poly Haven", "Made with
  Openverse").
- A loaded shelf also carries its provider's status bar item
  (`hx-swap-oob="true"`).
- **Load more** (`catalog/partials/load_more.html`): a full-width square
  `btn-quiet` in `#shelf-<provider>-more`, "Load 12 more". The reply
  (`shelf_more.html`): the new slot (next button, "That's everything from
  <provider> for “q”.", or an alert whose Retry asks the same page), the new
  cards in `<ul hx-swap-oob="beforeend:#shelf-<provider>-results">`, and the
  count and status out of band. A failed page leaves shown cards in place.

## Result cards

`catalog/partials/result_card.html`: `<li class="result-card"
data-kind="<kind>">`.

- **Whole-card link:** the title's `.result-link` opens Discover's drawer;
  its `::after` stretches over the card. As a plain link it's
  `catalog:discover_asset`. The play button and corner actions sit above it
  (higher `z-index`). Keyboard focus draws a 2 px ink ring on the card.
- **Thumbnail:** the provider's URL (`referrerpolicy="no-referrer"`,
  `data-thumb-fallback`) over the type icon (`.result-fallback`, in the
  type colour). With no URL there's no `<img>`; a failed image is removed
  by `shell.js`'s capture-phase `error` listener, uncovering the icon. 4:3
  with `object-fit: cover`, except textures: square with `contain`, showing
  the whole tile.
- **Author:** `.result-author` ellipsis; `.result-body`'s column is
  `minmax(0, 1fr)` so long author lists can't overflow the card.
- **License:** symbols (`license_symbols.html` with `small`) beside the
  short name (`.result-license`, via the `license_info` filter). Community
  rating under the author (`.result-community`).
- **Corner actions** (`.card-actions`, `.card-action` 1.75 rem squares, top
  right, `z-index: 3`): Save, Add to pack, View on <provider> (`external`
  icon, new tab), Details. Each inverts on hover with a mono `.card-tip`
  after 0.2 s. The row lets the pointer through between squares; forms
  inside are `display: contents`.
- **Details panel** (`.result-details`, `aria-hidden`, `pointer-events:
  none`): rises over the lower thumbnail with the full title, author,
  license, Commercial verdict, source and tags. Shows on hover (gated) or
  `:has(:focus-visible)`, not `:focus-within` (it stuck after a mouse click).
  **Details** (`data-card-details`, `aria-pressed`) keeps it open
  (`data-details="open"`, `card-actions.js`) until pressed again or Escape;
  kept open it takes the pointer so long tag lists scroll.
- **Save** (`catalog/partials/save_button.html`): a member gets
  `<form class="save-slot">` that `hx-post`s to `catalog:save` and swaps
  itself (it pulses meanwhile) for `in_library.html` (a filled check, no
  logo) plus the saved count out of band. On a `ProviderError`,
  `save_error.html`: Try again (alert icon in the error colour) with the
  message (`role="alert"`) on its own line and the details hidden. An asset
  already saved renders "In library" at once. A visitor gets a sign-in link
  back to this search (so does Add to pack).
- **Sound preview** (`catalog/partials/sound_play.html`, shared with
  library cards, drawers and pack items): a square ink `.sound-play` at the
  thumbnail's top left and a 2 px `.sound-progress`. `sound-preview.js`
  plays one at a time (`new Audio(url)`), sets the nearest
  `[data-sound-card]`'s `data-sound` (`loading`, `playing`, `paused`,
  `idle`, `error`) and `--progress`, keeps `aria-pressed` / `aria-label` in
  step, disables a preview that can't load ("Preview unavailable"), and
  stops when its card leaves (`htmx:afterSwap`) or its dialog closes.

## License filters (side panel)

`#discover-filters`: a "Filters" title (Clear while any is on), then
**Commercial use** ("Allowed only") and **License** (one chip per license
but unknown, with symbols, `.filter-chip.has-icons`). The chips belong to
the command bar's form (`form="discover-search"`) and carry
`data-autosubmit`, so `shell.js` submits it (boosted) on change; a
`<noscript>` Apply stands in. While any is on, `#discover-filter-note`
says which ("Only CC0 or CC BY, commercial use results.") with Clear
filters. An empty filtered shelf suggests other licenses.

## Discover's drawer

`<dialog id="discover-drawer" class="drawer-dialog">`, once on the page,
filled by a card's title (`catalog/partials/discover_drawer.html`) and
opened by `entry-drawer.js` (which works on the page's one
`dialog.drawer-dialog`). Like the library drawer: sticky head ("Discover
result", View on <provider>, Open as page, Close), the cropped mark,
`transition:false`. The body (`catalog/partials/discover_detail.html`; also
the full page `catalog/discover_asset.html`, a centred 48 rem column with
"Back to Discover"):

- thumbnail over the type icon (sounds get the play button), type and
  provider, title, author, community rating
- `#preview-actions`: **View on <provider>** (`btn-primary`, new tab), Save
  (`preview_save.html`, posts `slot=drawer`, swaps to "In your library"
  inverted or Try again; a visitor gets Sign in to save) and Add to pack
  (`data-picker`)
- **License:** large symbols, the deed link and title, the credit chip, the
  summary, "Can I use it?" (`license_uses.html`) and the attribution
- **Details** (source, tags) and **Downloads** (each variant's badges,
  package, file count and size, `.preview-variants`, with a note that saving
  lets you pick and download)
- a `ProviderError`: the alert with Retry (into the drawer) and Go to
  <provider>
