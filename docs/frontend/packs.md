# Packs (templates and HTMX)

Work surfaces. Server side: [../architecture/packs.md](../architecture/packs.md).
Attribution pages and license partials: [attribution.md](attribution.md).

Every packs page's side panel is `packs/partials/pack_nav.html`: "Your
packs" with a small **New** (`.panel-action`), then one `.panel-row` per
pack (`#pack-nav-<id>`), the open one current; with none, "The packs you
create are listed here." A visitor on a pack page gets "Shared pack"
(`#pack-visitor-panel`) with Sign up.

## Your packs and New pack

- **Your packs** (`packs/pack_list.html`): the header, a `.work-toolbar`
  with the count, **Grid / List** (`#pack-layout`, a `.layout-switch` of two
  `.layout-option` links, `?layout=`, current inverted with
  `aria-current="true"`, remembered by `packs.views.pack_layout()`) and
  **New pack** (`btn-primary`).
  - Grid: `#pack-list` is a `.pack-grid` of `.pack-card`s: visibility
    `.status-chip`, item count, title (stretched `.pack-card-link` to the
    builder), intended use (two lines), tags, date, and **View page**
    (`.pack-card-page`, raised above the stretched link).
  - List: `.pack-rows` of `.pack-row`s with the same facts on one line; one
    column on a phone.
  - Empty: "You have no packs yet." with New pack.
- **New pack** (`packs/pack_new.html`, centred `max-w-3xl`): a `novalidate`
  form via `partials/form_fields.html` (tags' tidying rule as help),
  **Create pack** and Cancel.

## The builder (`packs/builder.html`)

"Pack builder" over `#pack-title`, then a toolbar: the visibility switch,
Download files, Download manifest, **View pack page** (`#pack-page-link`)
and **Delete pack** (opens `#pack-delete-dialog` via `data-dialog-open`; a
plain boosted POST). Below, `.builder-grid`: details and items on the left,
**Add from my library** on the right (sticky on wide screens). **Every
builder swap says `transition:false`. There's no Save button anywhere.**

- **Visibility** (`#pack-visibility`, `packs/partials/visibility.html`):
  three chips (Private, Unlisted, Public); the block swaps on change. Lines:
  "Only you can see it.", "Anyone with the link can view and export it. It
  isn't listed anywhere.", "Anyone can view and export it."
- **Share link** (`#pack-share`, `packs/partials/share_link.html`, while
  unlisted): the link in a read-only mono `#pack-share-url`, **Copy link**
  (`data-copy`, `card-actions.js`: the clipboard, or the text selected with
  "Press Ctrl+C") and **New link**, opening `#pack-rotate-dialog`; its form
  (`data-dialog-done`) swaps `#pack-share` ("New link made. The old one no
  longer works."). Unlisted chips are outlined in `fg-secondary`
  (`.status-chip[data-visibility="unlisted"]`).
- **Details:** title, intended use and tags, three forms posting only their
  field on `change` to `packs:details`. The reply replaces
  `#pack-save-status`; a rename also swaps `#pack-title` and the panel row
  out of band.
- **Copied from:** a copy's builder shows `#pack-copied-from` ("Copied from
  <title> by <owner>", `copy` icon), the title a link only when readable by
  slug.
- **Items** (`#pack-items`, `packs/partials/items.html`): the count, an
  `.ax-select` **Auto sort** (two or more items) with "Sorted: …", the
  compatibility block ([attribution.md](attribution.md#license-partials)),
  then one `.pack-item` per item:
  - a grip (`.pack-item-grip`, `[data-drag-handle]`): `pack-sort.js` makes
    the row draggable from its grip only, moves it live (`[data-dragging]`
    dims it), puts it back on Escape, and posts `order` with `htmx.ajax`
  - thumbnail over the type icon, type and provider, title
  - **Variant** `.ax-select` (options "2K JPG · 3 files · 24.1 MB") and
    **Import path** (placeholder `<kind>s/<external_id>/`, a hint under it),
    each its own form posting on `change` into `#item-<id>-status`
  - Move up / Move down (disabled at the ends), Remove and Download
    (`.card-action`s); move and remove swap the whole list
- **Add from my library** (`#pack-library-form`): the search, "Show ones
  already in this pack" (`show_in`) and a hidden `page`
  (`#pack-library-page`, re-sent out of band so `packItemsChanged` refreshes
  the same page). It `hx-get`s `packs:library_search` on load, 300 ms after
  typing and on `packItemsChanged`, into `#pack-library-results`. Typing or
  the checkbox asks for page 1 (`hx-vals`). Rows (`.pack-pick`): a 2.75 rem
  thumbnail with an 11 rem preview on hover (`.pack-pick-zoom`, gated),
  title, type, provider, license, and Add or "In pack".
  `.pack-picks-pager`: arrow `.card-action`s and "Page N of M · X assets".
- **Suggested for this pack** (`#pack-suggestions`,
  `packs/partials/suggestions.html`, a `.builder-section` under the items):
  up to 8 `.pack-pick` rows, two a line from 48 rem (no hover preview here:
  it would open over the side panel), with "N shared tags", "In your
  library" for the owner's own, and **Add** (posting `asset` to
  `packs:suggestion_add`, swapping `#pack-items`), noting that adding saves
  it as To review. It `hx-get`s itself on `packItemsChanged from:body` and
  `packTagsChanged from:body`. Then **Find more from providers**
  (`#pack-find-more`) with "Searches Discover for “…”.". No tags: "Add tags
  to this pack to see suggestions." and `#pack-find-more-hint`; no match:
  "No other assets share this pack's tags yet."
- **"What's an import path?"** (`packs/partials/import_path_help.html`,
  `#import-path-help`): a `<details>` with an example tree, above the items
  on the builder and the pack page, outside `#pack-items` so a swap never
  closes it. The pack page's "What's this?" opens it (`data-open-details`).

## A pack's page (`packs/pack_page.html`)

`/packs/<slug>/` or the share link; a work surface, `.pack-page` (centred
60 rem).

- "Public pack" / "Unlisted pack" / "Private pack" over
  `#pack-page-title`, "By <owner> · N items · Changed …", intended use, tags.
- `#pack-page-actions`: **Download files** (`btn-primary`) and **Download
  manifest** (`hx-boost="false"` and `download`, since a boosted link would
  swap the JSON into the page); `#pack-page-own` with, for the owner only,
  the visibility chip and **Edit in builder**; then **Copy pack**
  (`#pack-copy-button`) opening `#pack-copy-dialog` ("Make a private copy?",
  `#pack-copy-missing`: "N assets you don't have yet go into your library as
  To review." or "Everything in it is already in your library, and stays as
  it is."), a plain boosted POST to the copy's builder. A visitor gets
  **Sign in to copy**, no dialog. By share link, both use the link's URLs.
- Compatibility, then items (`#pack-page-items`): the builder's rows made
  read-only (`.pack-item-read`): thumbnail, type, provider, title, author,
  `.pack-item-facts` (License, "no credit needed" or the Credit line, Files
  as a `.file-badge`, Import path in mono, Source). Each
  `.pack-item-download` row starts with `packs/partials/item_save.html`
  (`.item-save`): **Save to library** (`hx-post`, swaps itself,
  `transition:false`), **In your library** (check, inverted, linking to the
  reader's entry) or **Sign in to save**; then the item's Download.
- **Credits** (`packs/partials/credits.html`, `#pack-page-credits`): how
  many need credit, `.credits-warnings` (a 2 px ink edge), one
  `.credits-summary` row per license (a `.license-chip` to its guide card,
  a `.status-chip`: required inverted, recommended outlined, optional
  plain), then **Full attribution and license notice**.
- **No edit controls, for the owner too.** Save and Copy are the only
  forms. Nothing from anyone's library except the reader's own "In your
  library".

## Rows, thumbnails and downloads

- On the builder, the pack page and Asset attribution (`.lookup-item`), a
  thumbnail sits in the middle of its row (as in every thumbnail list); the
  grip matches the thumbnail's height; actions stay on the title's line; an
  idle status line is hidden. A thumbnail's frame is a 1 px border on an
  `::after` above the image (the image used to hide the inset shadow). The
  empty-thumbnail type icon is 24 px. A sound's item has `data-sound-card`
  and a small centred play button (`.sound-play.is-small`).
- **Download buttons** carry `data-bundle-download` and `data-bundle-url`
  and fetch the list from `packs:files` when pressed, so it follows the
  latest variants and paths. The status line is the `[data-bundle-status]`
  in the nearest `[data-bundle-box]` (`#pack-downloads` or the item). One
  file is a plain link to the provider.
- **`.ax-select`:** `appearance: none`, a `chevron-down` icon in place of
  the arrow, options in the elevated colours.
- Type colour: only the type icons.
