# Library and saving (server side)

`catalog/models.py`, `catalog/library.py` (the service module),
`catalog/forms.py`, `catalog/files.py`. Templates:
[../frontend/library.md](../frontend/library.md). The API over the same
functions: [api.md](api.md).

## Models

- **`Tag`:** a unique, normalized name. `Tag.objects.from_names(names)`
  normalizes (`normalize_tag()`), de-duplicates and creates as needed.
  `Tag.objects.in_library(user)` lists the member's own tags with `uses`,
  most used first.
- **`Asset`:** the shared copy of one provider asset, unique on
  (`provider`, `external_id`). `variants` is JSON:
  `[{"label", "files": [{"url", "filename", "size"}], "total_size"}]`; a
  size the provider doesn't give is `null`.
  `Asset.objects.from_record(record)` stores a fetched `AssetRecord` (tags
  normalized), or returns the stored row, never overwriting it.
- **`SavedAsset`:** one member's entry: `notes`, `rating` (null or 1 to 5,
  a database check), `status` (`SavedAsset.Status`, To review by default),
  `saved_at`. Unique on (`user`, `asset`). The FK to Asset is `PROTECT`, so
  deleting an entry never touches the Asset, and an Asset in anyone's
  library can't be deleted. **`SavedAsset.objects.for_user(user)` is the
  only way pages read entries**; it's empty for a visitor.
- **`StatusChange`:** `entry` (CASCADE), `status`, `changed_by` (SET_NULL,
  shown as "a former member"), `reason` (up to 300), `via` (`site` or
  `api`), `changed_at`, newest first. Each change names the person, ready
  for shared work later.

## Saving

- `get_or_fetch_asset(provider_key, external_id)` reuses a stored Asset or
  calls `fetch_record()` once. An unknown provider is
  `UnknownProviderError`; a `ProviderError` passes through and nothing is
  stored.
- `save_asset(user, asset)` is the create-or-reuse step everything shares:
  the member's entry untouched, or a new To review one with its first
  status record.
- `save_to_library(user, provider_key, external_id, *, via, status_reason,
  **review)` returns `(entry, created)`; `review` (`notes`, `rating`,
  `status`) sets a new entry's review (the API's create passes them). An
  asset the member already has comes back untouched with `created=False`.
- **`SaveAssetView`** checks the provider and a non-blank ID of at most 200
  characters (**400** otherwise) before any provider call. It replies with
  "In library", or the `ProviderError` message and Try again. A signed-out
  POST goes to sign-in with `next` set to the Discover page it came from
  (`HX-Current-URL`; HTMX gets `HX-Redirect`), never to the POST-only URL.

## Browsing: `filter_library(user, params)`

Returns a `LibraryPage`: one Django `Page` of 12 and the tidied
`LibraryParams`. It starts from `for_user(user)`, so no parameter reaches
another member's entries. The page and the API both call it (a QueryDict
or a plain dict). It always annotates the community rating and prefetches
`status_history()`.

- **Parameters:** `q`, `type`, `provider`, `status` and `tag` (each may
  repeat), `min_rating` (1 to 5), `sort` (`newest` default, `oldest`,
  `title`, `rating`, `community`), `page`. Also `exclude_entries=` (Add
  from my library) and `licenses=` (Asset attribution).
- **`clean_library_params()` never fails:** unknown values dropped, unknown
  sort is `newest`, a bad page is 1, a page past the end is the last.
- **Search** (`SavedAssetQuerySet.search()`): every word must match the
  title, a tag or the member's notes, ignoring case. Words go through
  `normalize_tag()` before matching tags ("bricks" finds "brick"). Tags
  match through a subquery, so an entry is never listed twice.
- **Tags** (`tagged()`): an entry needs **every** chosen tag (one subquery
  per tag). Values are normalized, the first 10 read, kept A–Z.
  `filter_groups()` makes the side panel's chips: the first 48 tags
  (`TAG_CHIP_LIMIT`) plus any chosen beyond; a `fold` of 8
  (`TAG_CHIPS_SHOWN`) gives `lead_chips` / `more_chips`, and `more_open` is
  true when a chosen chip is behind the fold.
- **Sorts** (`LIBRARY_SORTS`, `sorted_by()`): title ignores case; rating
  puts unrated last; `community` by average (unrated last), then count.
  Every sort ends on newest saved, then id, so pages never shift.
- `LibraryParams.url(page=None)` is the tidy URL with defaults left out
  (the whole library is `/library/`); `query_string()` is shared with the
  API. `LibraryPage` has `url`, `previous_url`, `next_url`.

## Views

- **`LibraryView`** answers the controls' HTMX (not boosted, not a history
  restore) with `catalog/partials/library_results.html` and `HX-Push-Url`
  holding the tidy URL. Boosted and history-restore requests get the whole
  page. A signed-out fragment request gets `HX-Redirect` to sign-in with
  the full library URL as `next`. Works with every provider down: it reads
  stored Assets only.
- **`EntryView`** (`/library/<id>/`): every entry view and update goes
  through `_own_entry()` (`for_user()` then `get_object_or_404`, prefetching
  its packs), so anything else is a **404**. HTMX (`_wants_fragment()`)
  gets the drawer; a direct visit, boosted link or history restore gets
  `catalog/entry.html`, which makes the link bookmarkable. It adds
  `entry_related()`, the member's `preferences`, `bundle` and
  `bundle_manifest`.
- **`UpdateEntryView`:** `ReviewForm` binds only the posted fields (the
  rest at stored values) and saves only those (`update_fields`), so a notes
  autosave and a status click never overwrite each other. Rating 1 to 5 or
  empty (cleared); status one of four; notes up to `NOTES_MAX_LENGTH`
  (10,000), kept as typed with line breaks stored as LF. `status_reason` is
  its own posted field (`clean_status_reason()`: spaces collapsed, up to
  300). Bad values, or none of the fields, are a **400** with one sentence,
  nothing saved. The reply is `entry_save_status.html`; a status or rating
  change made from the library page (`_from_library()`, via
  `HX-Current-URL`) also sends the card out of band. A signed-out HTMX save
  gets a **401** status line with a sign-in link in a new tab, so the notes
  being typed aren't lost; a plain POST goes to sign-in.
- **`RemoveFromLibraryView`:** GET is the confirm: the title and the packs
  it will leave (its PackItems, A–Z), as the dialog for HTMX or a page.
  POST deletes the entry; its PackItems cascade, the Asset stays. HTMX gets
  `library_results.html` for the view it came from (parameters read from
  `HX-Current-URL` only when that's a library URL) with `HX-Replace-Url`
  and the saved count out of band. A plain or boosted POST redirects to the
  library.

## Review, status history and community rating

- `SavedAsset.save_review(fields, by=, via=, reason=)` saves only `fields`
  and, when the status really changes, records it, in one transaction.
  `ReviewForm.save(by=)` and the API serializer both use it.
- `SavedAsset.explain_status(reason, by=, via=)` puts a reason on the
  latest change when that set the current status (the explainer becomes
  its author), or records the current status with it.
  `latest_status_change` is the record behind the current status, or None.
- **Community rating:** each member's rating stays private, but pages that
  show an asset may show the average of all members' ratings and the count,
  never who rated, nor anyone's notes or status. A count of 1 is shown.
  `with_community_rating()` annotates `community_rating` and
  `community_count` as subqueries (one row per entry);
  `SavedAsset.community` wraps them as `CommunityRating(average, count)` or
  None. Pack pages and the pack API never show it.
- **Saved count and theme:** `config.context_processors.shell` adds
  `saved_count` (own entries, members only) and, for every page,
  `theme_choice` (the `ax-theme` cookie via
  `accounts.theme.theme_choice()`, unknown is `system`), its label and the
  next choice for the title bar's switch.

## Files and bundles

`catalog/files.py`: no models, no requests.

- `describe_variant()` gives a `VariantInfo`: resolution ("2K"), format
  ("JPG", "glTF"; from the label, else the first file's extension),
  package (`maps`, `bundle`, `archive`, `audio`, `files`) and each file's
  `FileInfo` with its `map_key` and role. `map_type(filename, external_id)`
  reads only the part between the asset's ID and the resolution, so
  "rusty_metal_02_rough_2k.jpg" is Roughness, not Metalness.
  `Asset.file_variants` and `Asset.file_filters` wrap them.
- `pick_bundle(kind, variants, prefs)`: format first (the member's, then
  `FORMAT_FALLBACKS`), then resolution (the member's, else nearest below,
  else nearest above). From loose maps only the member's map types are
  kept; a bundle or archive is taken whole. `Bundle.notes` says where it
  had to differ. `Bundle.manifest()` puts every file under one folder named
  for the asset, through `safe_path()` (no `..`, no leading `/`, duplicates
  numbered).
- `bundle_manifest(entry, bundle)` (`catalog/library.py`) is the JSON the
  drawer's Download bundle reads: zip name, provider, each file's URL, path
  and size, credits. None over `BUNDLE_MAX_BYTES` (2 GB) or with nothing to
  bundle. **The member's browser fetches and zips**; the Toolbox never
  downloads, hosts or proxies files (PRD Out of Scope).
- **`DownloadPreferences`** (`accounts/models.py`, one per member):
  `resolution` (1K–8K, 2K default), `texture_format` (JPG), `hdri_format`
  (HDR), `model_format` (glTF), `sound_format` (MP3), `maps` (all by
  default). `DownloadPreferences.objects.for_user(user)` returns the row or
  unsaved defaults, so reading never writes. `DownloadPreferencesForm`
  saves only posted fields; at least one map must stay.

## Around an entry

`entry_related(user, entry)` gives an `EntryRelated`:

- `similar`: `SavedAssetQuerySet.similar_to()` on the member's own entries
  (most shared tags, then same kind, then newest; up to 6, each with
  `shared_tags`)
- `public_packs`: `Pack.objects.public_featuring(asset, exclude_owner=user)`,
  other members' public packs holding the asset, never a private or
  unlisted one
- `find_more_url`: Discover for the kind and the asset's two most widely
  used tags, or its title
