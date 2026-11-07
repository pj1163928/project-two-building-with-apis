# Main page, gallery, orbit hero and demo data (server side)

`packs/gallery.py`, `packs/hero.py`, `HomeView` (`packs/views.py`),
`packs/demo.py`. Templates: [../frontend/home.md](../frontend/home.md).

## The gallery: `filter_public_packs(params)`

Returns a `GalleryPage` (one `Page` of 12 and the tidied `GalleryParams`),
like `filter_library()`. It starts from `Pack.objects.public()` and every
parameter only narrows that, so no query can list a private or unlisted
pack (a test builds private and unlisted packs to match every query and
sort first).

- `q`: every word in the title or a tag, ignoring case; words normalized
  before matching tags; tags match through a subquery, so a pack is listed
  once.
- `type`: one of the four kinds; keeps packs holding at least one item of it.
- `sort`: `newest` (default, `created_at`) or `items` (`item_count`, then
  newest). Both end on newest, then id.
- `clean_gallery_params()` never fails; a page past the end is the last.
  `GalleryParams.url()` leaves defaults out, so the whole gallery is `/`.
- **Cards:** each pack is prefetched with owner, tags and `gallery_items`,
  so a page costs a fixed number of queries. `gallery_card(pack)` gives a
  `GalleryCard`: `mosaic` (the first 4 items' Assets), `blanks` (empty
  tiles), `summary` (`type_summary()`: "3 textures · 1 HDRI · 2 sounds" in
  Discover's order, singular or plural, empty types left out, "No items
  yet"). Nothing comes from anyone's library.
- **`HomeView`** (everyone) answers the gallery's HTMX (not boosted, not a
  history restore) with `packs/partials/gallery_results.html` and
  `HX-Push-Url`; anything else gets the whole page with the orbit hero. It
  sets `panel_start = "collapsed"`.

## The orbit hero: `hero_orbit(rng=None)`

Gives a `HeroOrbit` (`OrbitRing`s innermost first, each holding
`OrbitThumb`s; `is_fallback`). **Textures only** (`HERO_KIND`).

- **Only public packs:** the distinct textures held by items of
  `Pack.objects.public()` packs (call `.order_by()` first: PackItem's
  default ordering defeats `DISTINCT`). Each tile links to the **newest
  public pack** holding it (`_newest_public_packs()`), so a private or
  unlisted pack is never shown or linked.
- **The pick:** up to `HERO_SIZE` (18) at random; pass a seeded
  `random.Random` for a repeatable pick.
- **The rings:** `ring_counts(total)` uses one ring per `HERO_MINIMUM`
  tiles (up to three, always the outermost of `RING_SIZES` 46, 66, 86 %),
  each ring's share in proportion to its size, busiest outermost (18 tiles
  are 4, 6, 8). Neighbours turn opposite ways; tiles evenly spaced from a
  random start; `tile_rem` grows outwards. `RING_CLASSES` holds the
  `border-<kind>` classes in full for Tailwind. `OrbitThumb.is_cutout`
  marks a texture with an image (shown with no tile behind).
- **Fallback:** fewer than `HERO_MINIMUM` (6) distinct textures gives
  `FALLBACK_TILES` (6) texture-icon tiles on the outer ring, opening
  Discover's textures.
- Reads Pack, PackItem and Asset only. Gallery HTMX swaps don't build it.

## Demo data

`packs/demo.py`, the committed snapshot `packs/demo_assets.json`, and two
management commands.

- **Definitions:** `DEMO_USERS` (`demo_mira`, `demo_otto`, `demo_juno`,
  password `DEMO_PASSWORD` = `toolbox-demo`, listed in the README);
  `DEMO_PACKS` (six themed public packs and one private, each item naming
  its asset and optional import path); `REVIEWS` and `REVIEW_CYCLE` (every
  status and a range of ratings); `DEMO_SAVES` (entries outside each
  member's packs, so several members rate the same assets);
  `demo_entries(username)` and `demo_asset_refs()` (43 assets).
- **`capture_demo_assets`** (by hand, online, once) calls each provider's
  `fetch_record()` for every demo asset, spacing out Openverse, and writes
  the snapshot (`write_snapshot()`, `record_to_json()`) only if every fetch
  worked.
- **`seed_demo`** → `seed_demo(snapshot=None)`, one transaction, offline:
  1. Check the snapshot holds every asset the demo needs; a gap is a
     `ValueError` before anything is written.
  2. Get or create the users and reset their passwords.
  3. Store each Asset with `Asset.objects.from_record()`.
  4. Save each entry with `save_to_library()` (no provider call; first
     status recorded as on the website).
  5. Find each pack by owner and title (or `create_pack()`), restore its
     description, tags and visibility, `add_to_pack()` each item and set
     its position and import path.

  A second run creates nothing (a row-count test over every table checks).
  Entries a member already has are left as they are.
