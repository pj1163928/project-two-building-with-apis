# Test files

Which file covers what, grouped by area. Put a new test in the file whose
area it belongs to; add a row here when you create a file. "TDD" marks
files whose core behaviours were built test-first.

## Cross-cutting

| File | Covers |
|---|---|
| `test_access_control.py` | The access rules page by page: who gets 200, who is sent to sign-in (and comes back), POST-only sign-out, CSRF rejections; saving, the saved count and library parameters never reaching another member; the drawer and every update (404 for another member's entry, a visitor's HTMX save a 401 that keeps the text); the token page; every pack URL (sign-in, 404 for another member's pack or entry, CSRF required and accepted with the page's header). The API's own rules are in `test_api_library.py` |
| `test_network_guard.py` | The guard blocks every kind of unmocked request |
| `test_console_regression.py` | The console script and each provider's `search()` / `get_details()` |
| `test_library_client.py` | `library_client.py` with `responses`: a status change with reason, a rating cleared, PATCH body and token header, every page followed, every error message, `TOOLBOX_URL` / `TOOLBOX_TOKEN`; end to end through Django's test client |
| `test_tags.py` | `normalize_tag()`, rule by rule |

## Shell, theme and motion

| File | Covers |
|---|---|
| `test_shell.py` | Every page in the shell; column pages centred; side-panel rows and filter groups with icons; the sidebar; branding, fonts, static files; type colour kept out of the chrome and limited to the allowed places; surfaces; boosting, the hover and font gates; the ambient glow (one layer, transforms only, tokens only, still under reduced motion); versioned URLs; the mark above the glow; side-panel inputs kept inside their chips |
| `test_theme.py` | `source.css` holds only `axcenity` colours, every block closed once, the light block's values and contrast |
| `test_theme_switch.py` | Light and dark: the cookie's scheme on first paint, the switch stepping System → Light → Dark, the Settings chips, the cookie (a year, Lax), same-site redirect, HTMX's 204, a 400 for an unknown choice, CSRF, POST only |
| `test_motion.py` | `motion.js` on every page; the logo loader (status bar, pending shelf, Load more, picker, drawer; never on a thumbnail; no spinner classes); the wordmark's wipe and shine; the mark's cut-in and parallax; the spotlight; cards blurring up; fragment crossfades; no direct `startViewTransition`; reduced motion turning everything off with entry animations ending at rest and real keyframes |
| `test_scroll_ruler.py` | The ruler on every page: plain `#anchor` entries to ids present once, Top and End by default, `hx-boost="false"`, wide screens only, the monochrome scale, each page's index, none in a gallery swap, reduced motion, the CSS counter and gutter |
| `test_auth_pages.py` | Sign-in and sign-up: layout, top-bar actions, password toggles, Forgot password, focus and error styling |
| `test_accounts.py` | Sign-up and sign-in flows and their validation errors |

## Providers and Discover

| File | Covers |
|---|---|
| `test_provider_records.py` | `search_records()` and `AssetRecord`: the PRD mapping and filters, every field, the 12 limit, Poly Haven's `/info` calls and 12 h cache, paging, malformed answers, safe messages with details logged |
| `test_provider_fetch.py` | `fetch_record()` per provider (`responses`): fields and variants, every file URL, the cached `/info`, safe messages for an unknown ID, a malformed answer or a non-slug ID |
| `test_provider_failures.py` | Story 83 at the HTTP level: timeout, connection error, 429, Openverse's HTML 500, Poly Haven's 404 and `keywordMatches == 0`, each with its exact message and no leaked text |
| `test_discover.py` | Shelf URL validation, mixed shelves for every failure, pending shelves, tiles, command bar and `/`, each shelf state, the search cache, credits, fallback icons, provider status, the random pick and Shuffle, Load more, sound previews, hover details and the Details toggle, square texture thumbnails, corner actions. Defines `provider_calls` |
| `test_discover_licenses.py` | `clean_filters()`, commercial use narrowing the allowed set, links keeping filters, CC0 providers filtered out with no request, Openverse's `license=`, each set cached apart, the chips, the note, the filtered-out shelf, each card's symbols and verdict |
| `test_discover_drawer.py` | The drawer and full page, nothing saved and the record cached, a stored Asset shown without a provider call, 400s before any provider, `ProviderError` with Retry, a visitor's sign-in links, saving from the drawer (`slot=drawer`), a sound playing, "In your library" for the caller only |

## Library

| File | Covers |
|---|---|
| `test_library_save.py` | Saving: the shared Asset reused, one entry per member, nothing on a `ProviderError`, To review by default, model constraints, the save view's replies and 400s, "In library" on shelves (never the logo) |
| `test_library_filter.py` | `filter_library()` directly: own entries only, each search field, filter and sort, pages of 12, combinations, fallbacks, the tidy URL; tags (every chosen tag, tidied, `in_library()`, the chips) |
| `test_library_page.py` | The toolbar and chips (disabled while empty), the grid and cards, rendering with providers down, fragment versus page, boosted and history-restore requests, the pushed URL, the pager, both empty states, corner actions, stars clear of DaisyUI's `.rating`, Remove |
| `test_library_drawer.py` | The drawer and entry page: details, license, files, the review, one field per form, saving only the posted field, rating rules, 400s, the card out of band, notes surviving a reload, Remove |
| `test_status_history.py` | The first status on save, changes from the drawer and the API (`via`), no record for the same status, reasons, the 300 limit, the note and history, 404 and CSRF |
| `test_community_rating.py` | Averages over every member, unrated skipped, one row per entry, the Discover lookup, the `community` sort, cards, drawer and results showing average and count, never who or their notes |
| `test_entry_related.py` | Similar entries, public packs featuring the asset (never private or the member's own), Find more, the centred page, the folding Tags list |
| `test_downloads.py` | Files and bundles: map types from file names, resolution / format / package, `pick_bundle()` (preferences, nearest below then above, fallbacks, maps, bundles whole, limits), safe zip paths; download defaults (Settings chips, each group saving itself, at least one map, 400s, sign-in, CSRF); the drawer's bundle data |
| `test_sound_playback.py` | `Asset.preview_url`, the play button on library cards, the drawer, builder items and pack pages, `[data-sound-card]` |

## Packs

| File | Covers |
|---|---|
| `test_packs.py` | TDD: `add_to_pack()` (once per entry, refuses another member's), `default_variant()`, `add_from_provider()` (To review first, reuse untouched, nothing on `ProviderError`). Also tags, private-by-default, unique slugs surviving a rename, `move_item()`, what deletes cascade |
| `test_pack_builder.py` | Your packs and the side panel, New pack, the builder (no Save button, nothing private), each autosave and its 400s, visibility, Delete, variants, import-path rules, moves and removes, Add from my library (hiding pack items, paging), the picker on library and Discover, the Remove dialog, drag and drop (`reorder_items()`, stale orders a 400), auto sort, the variant select, the import-path help |
| `test_pack_layout.py` | Your packs as a grid or a list, the choice remembered, thumbnails centred with whole frames |
| `test_pack_public.py` | TDD: `visible_to()`; the manifest against `tests/golden/pack_manifest.json`; the sentinel (no owner's review or anyone's rating in the page, either export or the API, for anyone). Also the read-only page, the owner's controls, item facts, the unboosted download, reserved slugs, stale variants, `exported_at` in UTC |
| `test_api_packs.py` | The pack API and the PRD's pack access rows on site and API: private pack 404s by session or token, public packs for everyone, the list and `?mine=1`, pages, fields, detail items, the same manifest on both, 405 for every write |
| `test_pack_share.py` | Unlisted packs: the token (128 bits, kept, rotated), links opening unlisted or public but never private, unlisted packs hidden from `visible_to()`, `public()` and "Featured", the link's page and download (noindex, `Referrer-Policy`), 404 by slug and id to others, `link` reserved, the builder's chips and share box, New link, POST and CSRF |
| `test_pack_downloads.py` | Download files: paths under import paths, provider URLs only, CREDITS.txt and the manifest at the top, repeated names, the 2 GB limit, one item zipped or saved as is, another pack's item 404, private and unlisted access, never the owner's review, GET only, the buttons |
| `test_pack_suggestions.py` | TDD: `suggest_assets()` order and exclusions; `add_suggestion()` with every provider failing if called. Also the transaction, limits, `find_more()`, the builder section and hints, the fragment, Add through the view, the two events, sign-in, 404, CSRF |
| `test_pack_copy.py` | TDD: `copy_pack()` (missing assets To review, the copier's entries untouched, the owner's never touched, no provider calls), a part-way failure leaving nothing, Save and Copy following the reader rule. Also the copy's fields, long titles, empty packs, deleting the original, "Copied from", saving one item, the page's buttons per reader, the share link's URLs, CSRF |
| `test_attribution.py` | `license_key()` for every provider spelling; `pack_credits()` (groups, required equal to the manifest's credits, CC0 thank-yous, warnings); You may / must / may not; the notice (sections, 78 columns); every attribution page and its access rule; Asset attribution's filters and chips; compatibility per use and its warnings; the guide's legend, table and cards; centred pages; "On this page" folding |

## Main page and demo data

| File | Covers |
|---|---|
| `test_gallery.py` | TDD: private and unlisted packs built to match every query are never listed; `type_summary()`. Also search, type filter, sorts, pages, fallbacks, the tidy URL, a QueryDict |
| `test_home.py` | The four steps and buttons for visitors only, the gallery fragment versus the page, the panel starting collapsed, each card (mosaic, title, owner, tags, type count), nothing from anyone's library, no private or unlisted pack for anyone, both empty states |
| `test_home_hero.py` | TDD: `hero_orbit()` never using private or unlisted packs' textures, linking to the newest public pack, the fallback below 6, the cap of 18. Also textures only, `ring_counts()`, ring sizes, colour, directions, the page for visitors and members, cut-outs, no logo, the pause and reduced motion |
| `test_seed_demo.py` | With every provider failing: TDD idempotence (row counts equal after two runs). Also the sign-ins and the README listing them, statuses and ratings, themes, a second run restoring demo packs but keeping members' edits, a snapshot gap writing nothing, the capture command, every Tier 1 feature working offline |

## APIs and tokens

| File | Covers |
|---|---|
| `test_token_page.py` | The token page: created once, own only, never cached, the header example, the token signing requests, the panel rows; New token (dialog, old key 401, new key working, one-time message, a first token, others untouched, POST, CSRF, sign-in) |
| `test_api_library.py` | The library API: 404 for another member's entry on every method, duplicate save 400, `ProviderError` 502, create (reuse vs fetch, review, validation first), the list matching the page per parameter, pages and links, PATCH / PUT (only review fields), DELETE (Asset stays), 401 signed out, session writes needing CSRF while token writes succeed |

`tests/urls_with_password_reset.py` is a test-only URLconf: the real URLs
plus a stand-in `accounts:password_reset`. Use it with
`@pytest.mark.urls(...)` to test UI that appears only once a URL exists.
