# Packs (server side)

`packs/models.py`, `packs/services.py` (cross-model workflows),
`packs/suggestions.py`, `packs/forms.py`, `packs/views.py`. Templates:
[../frontend/packs.md](../frontend/packs.md). Export, downloads and
credits: [exports.md](exports.md). The pack API: [api.md](api.md).

## Models

- **`Pack`:** `owner`, `title` (up to 120), `slug`, `description`
  ("intended use", up to 2,000), `tags` (to `Tag`), `visibility`
  (`private` default, `unlisted`, `public`; `is_public`, `is_unlisted`),
  `share_token`, `copied_from` (nullable, SET_NULL), created/updated.
- **`PackItem`:** `pack`, `saved_asset`, `preferred_variant` (a variant's
  label), `import_path`, `position`. Unique on (pack, saved_asset). Both
  links CASCADE; `SavedAsset.asset` is still PROTECT, so the Asset stays.
  `default_import_path` is `<kind>s/<external_id>/`.
- `Pack.objects.create_pack(owner, title, description, tags)` writes the
  pack, a free slug and its tags in one transaction. The slug is the
  slugified title, then `-2`, `-3`… (`free_slug()`), never changed on a
  rename. Typed tags go through `tags_from_text()` (split on commas, then
  `Tag.objects.from_names()`).

## Who may read or change a pack

| Manager | Use for |
|---|---|
| `Pack.objects.owned_by(user)` | **changing** a pack: every builder URL. Empty for a visitor |
| `Pack.objects.visible_to(user)` | **reading** by slug or id: public packs plus the caller's own (any visibility). Unlisted packs are left out for everyone but the owner |
| `Pack.objects.public()` | anything listing packs to other people (gallery, `public_featuring()`, the orbit) |
| `Pack.objects.shared_by_link(token)` | reading by share link: unlisted or public, never private |

`get_public_url()` is `/packs/<slug>/`; `get_absolute_url()` is the
builder; `get_share_url()` is `/packs/link/<token>/`; `reader_url` is the
share link while unlisted, otherwise the slug page (used by the manifest's
`source_url`, the API's `page_url`, View pack page and pack cards).

## Unlisted packs

- `share_token` is `secrets.token_urlsafe(16)` (128 bits), unique, stored
  as is so the owner can see the link again. `set_visibility(choice)` makes
  it the first time a pack is unlisted and keeps it through later changes.
  `rotate_share_token()` (New link) replaces it; the old link is a 404 at
  once.
- Slugs come from titles and pks count up, so neither may open an unlisted
  pack: the slug page, its download and the API treat it as private.
- `PackSharedView` / `PackSharedExportView` serve the page and download by
  link (a public pack's link redirects) with `X-Robots-Tag: noindex,
  nofollow`. `Referrer-Policy: same-origin` (SecurityMiddleware) keeps the
  token out of Referer headers to provider sites.

## Services (`packs/services.py`, each one transaction)

- `default_variant(kind, variants)`: a 2K JPG's label (MP3 for sounds)
  when present, else the first variant, else "". Labels are compared
  ignoring case and hyphens (`squeeze_label()`), so "2K-JPG" counts; the
  label is stored as the provider wrote it.
- `add_to_pack(pack, saved_asset)` → `(item, created)`. Raises
  `NotYourEntryError` (writing nothing) unless the entry is the owner's.
  An entry already in the pack returns its item untouched; otherwise it
  goes last (`Max(position) + 1`) on the default variant, blank import path.
- `add_from_provider(pack, provider_key, external_id)`: Discover's Add to
  pack. `save_to_library()` for the owner, then `add_to_pack()`. An
  `UnknownProviderError` or `ProviderError` saves and adds nothing.
- `add_suggestion(pack, asset)` → `(entry, entry_created, item)`:
  `save_asset()` then `add_to_pack()`. Never calls a provider.
- `move_item(item, step)` swaps with a neighbour (`-1`, `1`) and rewrites
  positions 0, 1, 2…, closing gaps. False, writing nothing, at either end.
- `reorder_items(pack, item_ids)` (drag and drop) raises `ReorderError`,
  writing nothing, unless the ids are every item exactly once, so a stale
  page can't lose or duplicate an item.
- `sort_items(pack, sort)`: one of `ITEM_SORTS` (`type` in Discover order,
  `title`, `provider`, `license` with no-credit first); ties by title, id.
- `copy_pack(pack, user)`: a private pack titled `copy_title()` ("<title>
  (copy)", shortened to 120) with `copied_from`, the intended use and tags,
  no share token; then per item in order, `save_asset()` for `user` and a
  PackItem with the original's variant, import path and position. A failure
  part-way leaves nothing. Nothing of the original owner's review comes
  along.

## Suggestions and Find more (`packs/suggestions.py`)

- `suggest_assets(pack, limit=8)`: stored Assets ranked by tags shared with
  the pack (`shared_tags`), ties by title A–Z (case ignored) then id. No
  shared tag, or already in the pack: left out. Reads only `Asset` and
  `Tag`, never a `SavedAsset`, so no member's data reaches it.
- `find_more(pack)` → `FindMore(kind, query, url)` or None without tags:
  up to `FIND_MORE_TAGS` (2) of the pack's tags (most stored assets first,
  then A–Z) and the kind most items have (ties in Discover's order;
  textures when empty), as a `discover_url()`.
- Events: an add replies with the item list and `packItemsChanged` (plus
  the saved count out of band only when a new entry was made). A tags save
  sends `packTagsChanged`, only then. Add from my library listens for
  `packItemsChanged`; the suggestions listen for both.

## Forms

`NewPackForm` (title, intended use, tags). `PackDetailsForm` and
`PackItemForm` bind only posted fields, like `ReviewForm`. A variant must
be one of the asset's labels. An import path is optional, up to 300,
backslashes become `/`, and it must be relative (no leading `/`, no
`C:`) with no `..`. A bad value is a **400** with one sentence.

## Views

- **Members' pages** (`PacksPageMixin`): a visitor goes to sign-in and back
  to `login_return_url()` (the builder for any pack URL, the page a picker
  was on, else the page itself); HTMX gets `HX-Redirect`.
  `OwnPackMixin.get_pack()` reads through `owned_by()` and items through
  that pack; entries come through `for_user()`. So another member's pack,
  item or entry is a **404** before any service runs.
- Builder add, move and remove reply with `packs/partials/items.html` and
  `HX-Trigger: packItemsChanged`. Details, variant and import path reply
  with a status line. Any non-HTMX POST redirects to the builder.
- Add from my library is `filter_library(user, {"q", "page"},
  exclude_entries=<the pack's entries>)`; `show_in=1` includes them marked
  "In pack". It reports how many are hidden.
- `PickerView` takes the member's `entry`, or `provider` and `external_id`,
  checked before any provider call (**400**). It lists `owned_by()` packs
  with item counts, marking those already holding the asset.
  `PickerAddView` adds and replies with the list again, "Added to …", the
  saved count out of band (Discover), or the `ProviderError` message.
- **The pack page** (`PackPageView`, `/packs/<slug>/`): no login mixin,
  read through `visible_to()`. Each item comes from `manifest_item()`, so
  the page shows what the export holds. It never reads a library entry
  (no notes, rating, status, community rating). Only the owner sees Edit in
  builder and the visibility chip. `PackExportView` serves `manifest_for()`
  as an indented JSON download.
- **Save and Copy** (`PackItemSaveView`, copy views,
  `PackReaderWriteMixin`): any signed-in member who can **read** the pack by
  the page's rule (`visible_to()` by slug, `shared_by_link()` by token);
  anything else is a **404** that writes nothing. Unlisted packs are saved
  from and copied through the share link. A visitor goes to sign-in and
  back to the pack's page. Save is `save_asset(user, item.asset)` (no
  provider call), replying with `packs/partials/item_save.html` and the
  saved count out of band for a new entry.
- The builder of a copy names the original (`_copied_from()`), linking to
  it only when the member can still read it by slug.
