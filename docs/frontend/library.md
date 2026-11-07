# Library page, cards, dialogs and drawer (templates and HTMX)

`catalog/library.html` and its partials, a work surface. Server side:
[../architecture/library.md](../architecture/library.md).

## Layout

The controls show even when the library is empty (disabled), so the layout
is set before any assets arrive.

- `#library-toolbar`: a GET `<form>` (`.work-toolbar`, `role="search"`)
  under the header with the search (`#library-search`, `q`) and the sort
  select. A card grid only (no grid/list toggle).
- `#library-filters`: the library's panel in the sidebar. `.filter-group`s
  of square `.filter-chip`s from `FilterChip` / `FilterGroup`
  (`catalog/filters.py`, shared with Discover) rendered by
  `catalog/partials/filter_chip.html` (`form_id`, `control`, `autosubmit`,
  `icons`). Type, Provider, Status and Tags are checkboxes; Minimum rating
  is a radio group (Any, 1+ … 5). Tags show counts
  (`.filter-chip-count`); the first 8 show and the rest fold into
  `<details class="filter-more">` ("Show N more"), forced open
  (`data-forced-open`) when a chosen tag is behind the fold, otherwise
  reopened as last left (`data-remember`). Each chip is a `<label>` around
  an `sr-only` input (keyboard focus ring on the chip; on = inverted). The
  inputs carry `form="library-toolbar"`.
- `#library-results` (`catalog/partials/library_results.html`): the count
  ("13–15 of 15 entries"), the grid of `library_card.html`, and
  `#library-pager`. Or an empty state: "Your library is empty." with Go to
  Discover, or "Nothing in your library matches …" with Clear filters.

**Swapping only the results:** the form `hx-get`s `/library/` into
`#library-results` (`outerHTML`, `hx-push-url="true"`) on submit, 300 ms
after typing (`input changed delay:300ms from:#library-search`), and on any
chip or the sort (`change from:.library-control`; side-panel events don't
bubble to the form, hence `from:`). `hx-sync="this:replace"` drops stale
requests. The view's `HX-Push-Url` overrides the raw query. Pager links are
real URLs with the same `hx-get` and `show:#library-toolbar:top`. Back gets
the whole page. **Clear filters** is a plain boosted link to `/library/`,
so the controls reset too.

## Library cards

`<li class="result-card library-card" id="entry-<pk>" data-kind="<kind>">`
reuses the result card's frame, thumbnail, stretched link, corner actions
and details ([discover.md](discover.md#result-cards)).

- Type icon in the type colour, then the singular label in mono.
- The title opens the drawer; as a plain link it's the entry's page, so
  Ctrl-click and Copy link work.
- `.library-meta`: a monochrome `.status-chip` (`data-status`; Approved
  inverted, Rejected struck through) and five stars (`.star-rating`,
  `.is-on`, `role="img"` "Rated N out of 5") or "Not rated". **Never name it
  `.rating`**: DaisyUI's `.rating *` paints each star as a grey block.
- `.library-community`: once anyone has rated, "Community" with
  `catalog/partials/community_rating.html` (a grey star, the average to one
  decimal, "· N ratings"). Grey, so it never reads as the member's stars;
  never names who rated.
- Sounds: `sound_play.html` on the thumbnail, `data-sound-card` on the
  `<li>`.
- **Corner actions:** Add to pack, Details (provider and tags), Remove.

## Pack picker

`catalog/partials/pack_picker.html`: one `<dialog id="pack-picker"
class="picker-dialog">` on the library and a member's Discover page.

- An Add to pack button (`catalog/partials/pack_button.html`) carries
  `data-picker="pack-picker"`, `data-picker-asset="<title>"` and
  `data-picker-url` (`packs:picker` with `?entry=` or `?provider=&external_id=`).
  `card-actions.js` writes the title, loads the URL into
  `#pack-picker-list` (`htmx.ajax`, "Loading your packs…") and calls
  `showModal()`, so the list is always current.
- `packs/partials/picker_list.html`: each pack a full-width `.picker-pack`
  button with its count, posting to `packs:picker_add` and swapping the
  list ("Added to …", or the provider's message in `.picker-alert`). A pack
  already holding the asset shows "In pack". Then New pack; with none,
  "You don't have any packs yet."
- Square, panel colour, `shade` backdrop. Backdrop click, Close, × or
  Escape shuts it. × and Close sit in their own `method="dialog"` forms.
  Swaps say `transition:false`.

## Remove dialog

`<dialog id="remove-dialog" class="picker-dialog">`, once on the library.
A card's Remove (`catalog/partials/remove_button.html`) or the drawer's
Delete `hx-get`s `catalog:remove` into it
(`catalog/partials/remove_dialog.html`); `card-actions.js` opens any
`.picker-dialog` htmx has just filled. It shows the title, "It will also
leave these N packs:" (`#remove-packs`) or "It isn't in any of your
packs.", and a note that notes, rating and status go too. Its form posts
into `#library-results` with `data-drawer-remove` (closes an open drawer)
and `data-dialog-done` (closes on success). With `as_page` it's the confirm
page (`catalog/remove_confirm.html`, `.remove-page`).

## Library drawer

A card's title `hx-get`s `/library/<id>/` into `<dialog id="library-drawer"
class="drawer-dialog">` (`innerHTML`); `entry-drawer.js` calls
`showModal()` after the swap.

- **Panel** (`catalog/partials/entry_drawer.html`): full height,
  `min(34rem, 100vw)`, right edge, slides in over 0.28 s over `shade`. A
  sticky head: "Library entry", **Open as page**, Close. The address bar
  doesn't change. Every swap says `transition:false`.
- **Full page** (`catalog/entry.html`): `.entry-layout` (centred 76 rem),
  "Back to your library", the body in `.entry-page`, and a sticky
  `.entry-aside` with `entry_related.html` on wide screens.
- **Body** (`catalog/partials/entry_detail.html`): thumbnail over the type
  icon, type and provider, title (`h2` drawer, `h1` page), author, then:
  - **Your review:** status chips (`.filter-chip` radios), five star radios
    (`.rate-star`, hover preview) with "Clear rating" (`.rate-clear`), the
    notes box, `#entry-save-status`, and `#entry-community` (re-sent out of
    band on a rating change).
  - **Status note:** `#entry-status-note` ("Approved by you · 5 Nov 2026,
    14:02", "· via the API", the reason, a folded "History · N changes"),
    then `#entry-status-reason`, one line posting only `status_reason`
    (`data-autosave="reason"`). A status change re-sends the note and an
    empty reason box; a reason re-sends only the note, so the box being
    typed in is never replaced.
  - **License and credit:** license (linking to its guide card with the
    credit rule), attribution, View on <provider>, tags, saved date.
  - **Your packs** (`#entry-packs`), each to its builder with the variant.
  - **Files** (`catalog/partials/entry_files.html`): **Your bundle**
    (`#entry-bundle`: resolution and format `.file-badge`s, package, count,
    size, map types, notes where it had to differ, "Defaults: …" linking to
    Settings). One file is a plain Download link; several are **Download
    bundle** (`btn-primary`): `bundle-download.js` reads the `json_script`
    `entry-bundle-data`, fetches each file from the provider, and saves a
    stored zip with `CREDITS.txt` (and `MISSING.txt` for refused files),
    progress in `[data-bundle-status]` and a 2 px bar; over 2 GB it says to
    use the links. Then Resolution and Format filter chips
    (`[data-file-filters]`, shown by `entry-files.js`) and one `<details>`
    per variant ("Your default" inverted on the bundle's), each file row
    starting with its role (Color, Normal GL, Roughness…).
  - **Remove from library** (`entry_remove.html`): the dialog in the
    drawer, the confirm page from the full page.
- **Around the entry** (`entry_related.html`): Similar in your library
  (`#entry-similar`, up to 6, "N shared tags"; in the drawer they open in
  the drawer), Find more like this on Discover, Featured in public packs
  (`#entry-featured`).

**Saving:** status, rating and notes are three forms, each posting only
its field to `catalog:update`. Status and rating on `change`; notes 0.7 s
after typing stops and on leaving the box (`input changed delay:700ms,
change`, `hx-sync="this:queue last"`, 15 s timeout). No Save button. Each
reply replaces only `#entry-save-status` ("Changes save as you make them.",
"Saving…", "Saved", or an error with **Try again**). A status or rating
change from the library also swaps the card out of band.

**Notes are never lost** (`entry-drawer.js`):

- the text is kept in `localStorage` (`data-draft-key`, `ax-notes-<id>`)
  from the first keystroke until a save of that exact text succeeds; a
  draft found on reopening is restored and saved
- on a 400 or 401 the Toolbox's own status line swaps in; on any other
  error page, a dropped connection or a timeout the script writes
  "Couldn't reach the Toolbox…" or "Something went wrong…" with Try again,
  and retries on `online`
- the CSRF token comes from the `csrftoken` cookie, so saving survives a
  sign-in in another tab
- it asks before closing, opening another entry, navigating or unloading
  while the notes differ from the last confirmed text and no save is
  pending

Escape in `card-actions.js` ignores every open dialog, the drawer included.
