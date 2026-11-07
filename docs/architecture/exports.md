# Export, downloads, licenses and credits (server side)

`packs/manifest.py`, `packs/downloads.py`, `catalog/licenses.py`,
`packs/credits.py`, `packs/attribution.py`. Templates:
[../frontend/attribution.md](../frontend/attribution.md) and
[../frontend/packs.md](../frontend/packs.md).

## Export manifest

`build_manifest(pack, *, source_url, exported_at=None)` is the one
builder. `packs.views.manifest_for(request, pack)` calls it with the
absolute URL of the pack's page, for the website download and the API
export alike. The shape is the PRD's Option A, locked by
`tests/golden/pack_manifest.json`.

- **Top level:** `format` (`"axcenity-pack"`), `version` (1), `exported_at`
  (ISO 8601, UTC, to the second), `pack` (`title`, `slug`, `author` = the
  owner's username, `description`, `tags` A–Z, `source_url`), `items` in
  position order, `credits`.
- **Each item** (`manifest_item()`): `name`, `kind`, `provider`,
  `external_id`, `variant`, `files` (`url`, `filename`, `size`),
  `total_size`, `license`, `license_url`, `author`, `attribution`,
  `source_url`, `import_path` (the owner's, or `<kind>s/<external_id>/`).
- **The variant** (`chosen_variant()`): `preferred_variant` looked up by
  exact label; an unknown label falls back to `default_variant()`. No
  variants gives `variant: null`, `files: []`, `total_size: null`. Missing
  sizes stay `null`.
- **Credits:** each item whose license isn't CC0 (`is_cc0()`: starts with
  "CC0", ignoring case) gives `credit_line()`: its attribution, or
  `"<title>" by <author>, <license>`. Each line once, in item order.

## Download files

`pack_download()` and `item_download()` only **list** the providers' URLs,
each with its path in the zip, for `static/js/bundle-download.js` to fetch
and zip in the browser. The Toolbox never downloads, hosts or proxies.

- Each item's chosen variant's files (from `manifest_item()`) go under its
  import path via `safe_path()`; repeated names get `-2`, `-3`…. Unzipped at
  a project's root, every file lands where the manifest says.
- The pack is always `<slug>.zip`, with `CREDITS.txt` and
  `<slug>.axcenity-pack.json` at the top. One item: a single file is saved
  as is (`zip: false`); several are zipped with the item's own CREDITS.txt.
- No files, or over `BUNDLE_MAX_BYTES` (2 GB), returns `{"error": …}`.
- `PackFilesView` reads through `visible_to()`, `PackSharedFilesView`
  through `shared_by_link()` (noindex).

## Licenses

`catalog/licenses.py`. Not legal advice; each card links to the deed.

- `license_key()` reads a license as the providers write it ("CC0 1.0",
  "CC BY-NC-SA 3.0", "Public Domain Mark", "CC SAMPLING+ 1.0"…, ignoring
  case, spacing, "CC" and the version). Anything else is `unknown`.
- `license_info()` returns a `LicenseInfo`: name, plain summary, credit
  (`required`, `listed` for PDM, `optional` for CC0), commercial use and
  changes (yes, no, or `None` for partly/unknown), share-alike, steps to
  meet it, deed URL, `permits` / `requires` / `prohibits`, `SYMBOLS` (icon,
  name, meaning). `Asset.license_info` reads it.
- **Uses:** `USES` = commercial, personal, internal.
  `LicenseInfo.use_status(use)` → (`ok` / `caution` / `blocked`, note): NC
  blocks commercial and limits internal to private testing; ND and SA add
  conditions; Sampling+ allows commercial only remixed; unknown blocks both
  public uses. `.uses` lists the three `UseVerdict`s.

## Credits and the notice

`packs/credits.py`. Reads only PackItems and Assets (anything with `.asset`
works, so a library entry gets the same treatment).

- `pack_credits(items)` groups items by license (credit-needing first):
  `required` is exactly the manifest's `credits`, `optional` thank-you
  lines for CC0, warnings for NC, ND, SA, Sampling+ and unknown.
- `compatibility(groups)` gives a `UseCheck` per use: the most restrictive
  status (`worse()`) and one reason per limiting license, blocking first.
  `PackCredits.compatibility`, `.blocked_uses`, `.has_conditions` read it.
  The builder's item list carries the credits, so the check follows every
  add, move or remove.
- `PackCredits.notice(subject, *, compiled_by, source_url, prepared)` is the
  formal Attribution and License Notice, wrapped at 78 columns: who it
  covers and who compiled it, that assets belong to their creators, then
  1. Required attribution, 2. License terms (per license: deed, items, You
  may / You must / You may not), 3. Restrictions in force and Permitted
  uses, 4. Optional acknowledgements, and a disclaimer. It's the CREDITS.txt
  in every download and the text the attribution pages copy.
  `pack_notice(pack, credits, source_url)` fills it in for a pack;
  `credit_lines()` is the short version.

## The Attribution center (`packs/attribution.py`)

| View | Path | Reads through |
|---|---|---|
| `AttributionGuideView` | `/attribution/` | everyone |
| `AttributionPacksView` | `/attribution/packs/` | `owned_by()` + `pack_credits()` |
| `PackAttributionView` / `SharedPackAttributionView` | `/attribution/packs/<slug>/`, by link | `visible_to()` / `shared_by_link()` (noindex; a public pack's link redirects) |
| `AttributionAssetsView` | `/attribution/assets/` | `filter_library(..., licenses=license_filter(user, keys, credits))` |
| `AssetAttributionView` | `/attribution/assets/<id>/` | the member's own entry, **404** otherwise |

`license_filter()` turns chosen license types and credit rules into the
license strings in that library matching both (None when nothing is
chosen); `license_choices()` gives the chips with counts;
`clean_license_params()` drops unknown values. All in `catalog/library.py`.
