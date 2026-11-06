"""Demo data for graders and manual testing: three demo members, their libraries
and their packs, built offline from a committed snapshot of real provider assets.

- `capture_demo_assets` (a management command, run once by hand, online) calls
  each provider's fetch_record() for every asset named here and writes the
  snapshot, packs/demo_assets.json.
- `seed_demo` (a management command) calls seed_demo() below, which loads the
  snapshot through Asset.objects.from_record() and never contacts a provider.

The credentials are obviously demo values (DEMO_PASSWORD), listed in the README.
"""

import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from django.contrib.auth import get_user_model
from django.db import transaction

from catalog.library import save_to_library
from catalog.models import Asset, SavedAsset
from providers.records import AssetRecord, Variant, VariantFile

from .models import Pack, PackItem, tags_from_text
from .services import add_to_pack

SNAPSHOT_PATH = Path(__file__).with_name("demo_assets.json")
DEMO_PASSWORD = "toolbox-demo"
DEMO_USERS = ("demo_mira", "demo_otto", "demo_juno")

APPROVED = SavedAsset.Status.APPROVED
TESTING = SavedAsset.Status.TESTING
TO_REVIEW = SavedAsset.Status.TO_REVIEW
REJECTED = SavedAsset.Status.REJECTED

Ref = tuple[str, str]  # (provider, external_id)


@dataclass(frozen=True)
class DemoEntry:
    """One asset in a demo member's library, with their review of it."""

    provider: str
    external_id: str
    status: str = TO_REVIEW
    rating: int | None = None
    notes: str = ""

    @property
    def ref(self) -> Ref:
        return (self.provider, self.external_id)


@dataclass(frozen=True)
class DemoItem:
    """One item of a demo pack: an asset from the owner's library, and its import path."""

    provider: str
    external_id: str
    import_path: str = ""

    @property
    def ref(self) -> Ref:
        return (self.provider, self.external_id)


@dataclass(frozen=True)
class DemoPack:
    owner: str
    title: str
    description: str
    tags: str
    items: tuple[DemoItem, ...]
    visibility: str = Pack.Visibility.PUBLIC


@dataclass
class SeedReport:
    """What one seed_demo() run created (zero for whatever already existed)."""

    users: int = 0
    assets: int = 0
    entries: int = 0
    packs: int = 0
    items: int = 0
    usernames: list[str] = field(default_factory=list)


def _items(*refs: tuple[str, str] | tuple[str, str, str]) -> tuple[DemoItem, ...]:
    return tuple(DemoItem(*ref) for ref in refs)


AC, PH, OV = "ambientcg", "polyhaven", "openverse"

DEMO_PACKS: tuple[DemoPack, ...] = (
    DemoPack(
        "demo_mira",
        "Medieval Village",
        "A market square at dusk: cobbled streets, timber and brick, a blacksmith at work.",
        "medieval, village, stone, wood",
        _items(
            (PH, "cobblestone_floor_03"),
            (PH, "church_bricks_03"),
            (AC, "Planks037A"),
            (PH, "rural_landscape"),
            (PH, "wooden_barrels_01", "models/props/barrels/"),
            (PH, "wooden_lantern_01", "models/props/lantern/"),
            (OV, "02f9fe1d-c2cf-4576-a7a6-9a00144c8888", "audio/village/"),
            (OV, "96eea9fb-b01a-437f-b9f6-744f263bcccd", "audio/village/"),
        ),
    ),
    DemoPack(
        "demo_otto",
        "Sci-fi Corridor",
        "Metal walls, harsh work lights and the hum of a ship that never sleeps.",
        "sci-fi, metal, corridor, spaceship",
        _items(
            (AC, "MetalPlates006"),
            (AC, "MetalPlates017A"),
            (PH, "metal_plate_02"),
            (PH, "empty_warehouse_01"),
            (PH, "industrial_pipe_and_valve_01"),
            (OV, "6a48c056-e0ed-413c-83c6-d769d69ede78", "audio/doors/"),
            (OV, "c4d41831-bac8-47a7-96d1-6ed4d302379a", "audio/ambience/"),
            (OV, "667765bf-9223-4e72-b3e9-ef9de7128aca", "audio/ambience/"),
            (OV, "97b26423-3b6a-45e8-8e34-651462783a81", "audio/flyby/"),
        ),
    ),
    DemoPack(
        "demo_juno",
        "Forest Ambience",
        "A quiet walk through an old forest: moss, bark, birdsong and running water.",
        "forest, nature, ambience",
        _items(
            (PH, "forest_ground_04"),
            (PH, "forest_leaves_03"),
            (PH, "bark_brown_01"),
            (AC, "Moss002"),
            (PH, "mossy_forest"),
            (OV, "b30c168a-c76c-4d2f-8ba5-481800ed82c3", "audio/forest/"),
            (OV, "4740f464-a3bf-4a94-ab79-4c5265414e0c", "audio/forest/"),
            (OV, "646c8295-f605-433a-ae64-89d196594ca1", "audio/forest/"),
        ),
    ),
    DemoPack(
        "demo_otto",
        "Desert Outpost",
        "Sun-bleached sandstone and dunes for a lonely trading post.",
        "desert, sand, outpost, stone",
        _items(
            (PH, "old_sandstone_02"),
            (PH, "sandstone_blocks_08"),
            (AC, "Ground054"),
            (PH, "goegap"),
            (PH, "rock_09"),
            (OV, "fd31da2c-4bbf-43a9-8e4c-8a14e100a147", "audio/wind/"),
        ),
    ),
    DemoPack(
        "demo_mira",
        "Golden Hour Skies",
        "Warm evening skies for lighting outdoor scenes.",
        "sky, sunset, lighting",
        _items(
            (PH, "rogland_sunset"),
            (PH, "kiara_8_sunset"),
            (PH, "belfast_sunset"),
            (AC, "EveningSkyHDRI048B"),
            (AC, "DaySkyHDRI069A"),
            (PH, "rural_landscape"),
        ),
    ),
    DemoPack(
        "demo_juno",
        "Bakery Props",
        "Bread, cake and fruit for a village bakery's counter, with the bustle of a market.",
        "food, kitchen, props",
        _items(
            (AC, "3DBread011"),
            (AC, "3DBread007"),
            (PH, "food_apple_01"),
            (PH, "carrot_cake"),
            (AC, "WoodFloor064"),
            (OV, "eef30f33-aae2-4b2d-8e99-e17fb0406a08", "audio/market/"),
        ),
    ),
    DemoPack(
        "demo_mira",
        "Castle Siege (work in progress)",
        "Still collecting: a forge and walls for the siege level.",
        "castle, medieval",
        _items(
            (PH, "church_bricks_03"),
            (OV, "c7aa377b-1297-403b-8df6-2ee5030b65fa"),
        ),
        visibility=Pack.Visibility.PRIVATE,
    ),
)

# Reviews for entries in the demo members' own packs. Anything not listed here
# gets a review from REVIEW_CYCLE, so statuses and ratings vary.
REVIEWS: dict[tuple[str, Ref], tuple[str, int | None, str]] = {
    ("demo_mira", (PH, "cobblestone_floor_03")): (
        APPROVED,
        5,
        "Tiles well at 2K. Used for the main square.",
    ),
    ("demo_mira", (OV, "02f9fe1d-c2cf-4576-a7a6-9a00144c8888")): (
        TESTING,
        4,
        "Needs a trim at the start. Credit phonoflora (CC BY).",
    ),
    ("demo_otto", (OV, "97b26423-3b6a-45e8-8e34-651462783a81")): (
        TESTING,
        3,
        "Sampling+: only use it remixed. Check before shipping.",
    ),
    ("demo_juno", (OV, "eef30f33-aae2-4b2d-8e99-e17fb0406a08")): (
        REJECTED,
        2,
        "Non-commercial license, so it can't ship in the paid build.",
    ),
    ("demo_mira", (OV, "c7aa377b-1297-403b-8df6-2ee5030b65fa")): (
        TO_REVIEW,
        None,
        "Great forge sound, but NC. Look for a CC0 one.",
    ),
}
REVIEW_CYCLE: tuple[tuple[str, int | None], ...] = (
    (APPROVED, 5),
    (TESTING, 4),
    (APPROVED, 4),
    (TO_REVIEW, None),
    (APPROVED, 3),
    (TESTING, None),
    (REJECTED, 2),
    (APPROVED, 5),
)

# More library entries, outside each member's own packs: other members' assets,
# so the community rating has several members behind it.
DEMO_SAVES: dict[str, tuple[DemoEntry, ...]] = {
    "demo_mira": (
        DemoEntry(AC, "MetalPlates006", APPROVED, 4),
        DemoEntry(OV, "b30c168a-c76c-4d2f-8ba5-481800ed82c3", APPROVED, 5, "Lovely morning birds."),
        DemoEntry(PH, "goegap", TESTING),
    ),
    "demo_otto": (
        DemoEntry(PH, "forest_ground_04"),
        DemoEntry(PH, "mossy_forest", APPROVED, 5),
        DemoEntry(PH, "cobblestone_floor_03", TESTING, 3),
        DemoEntry(AC, "3DBread011", REJECTED, 2, "Too many polygons for a background prop."),
    ),
    "demo_juno": (
        DemoEntry(PH, "cobblestone_floor_03", APPROVED, 5),
        DemoEntry(OV, "96eea9fb-b01a-437f-b9f6-744f263bcccd", TESTING, 4),
        DemoEntry(PH, "rogland_sunset", APPROVED, 4),
    ),
}


def demo_entries(username: str) -> list[DemoEntry]:
    """Every library entry `username` gets: their packs' assets (once each, in
    pack order, reviewed from REVIEWS or REVIEW_CYCLE), then DEMO_SAVES."""
    refs: list[Ref] = []
    for pack in DEMO_PACKS:
        if pack.owner == username:
            refs += [item.ref for item in pack.items if item.ref not in refs]
    entries = []
    for index, ref in enumerate(refs):
        status, rating = REVIEW_CYCLE[index % len(REVIEW_CYCLE)]
        status, rating, notes = REVIEWS.get((username, ref), (status, rating, ""))
        entries.append(DemoEntry(*ref, status=status, rating=rating, notes=notes))
    return entries + [entry for entry in DEMO_SAVES.get(username, ()) if entry.ref not in refs]


def demo_asset_refs() -> list[Ref]:
    """Every asset the demo uses, once each, in a stable order: what the snapshot holds."""
    refs: list[Ref] = []
    for username in DEMO_USERS:
        refs += [entry.ref for entry in demo_entries(username) if entry.ref not in refs]
    return refs


# ------------------------------------------------------------------ the snapshot


def record_to_json(record: AssetRecord) -> dict[str, Any]:
    """An AssetRecord as plain JSON data for the snapshot."""
    data = asdict(record)
    data["tags"] = list(record.tags)
    data["variants"] = [variant.as_dict() for variant in record.variants]
    return data


def record_from_json(data: dict[str, Any]) -> AssetRecord:
    """The AssetRecord a snapshot entry describes (record_to_json()'s inverse)."""
    variants = tuple(
        Variant(
            label=variant["label"],
            files=tuple(
                VariantFile(url=file["url"], filename=file["filename"], size=file.get("size"))
                for file in variant["files"]
            ),
        )
        for variant in data.get("variants", ())
    )
    fields = {key: value for key, value in data.items() if key not in ("tags", "variants")}
    return AssetRecord(**fields, tags=tuple(data.get("tags", ())), variants=variants)


def load_snapshot(path: Path = SNAPSHOT_PATH) -> dict[Ref, AssetRecord]:
    """The committed snapshot's records, keyed by (provider, external_id)."""
    with open(path, encoding="utf-8") as handle:
        records = [record_from_json(item) for item in json.load(handle)["assets"]]
    return {(record.provider, record.external_id): record for record in records}


def write_snapshot(records: Iterable[AssetRecord], path: Path = SNAPSHOT_PATH) -> None:
    """Write the snapshot file, one record per asset, in demo_asset_refs() order."""
    document = {
        "about": (
            "Real provider assets for seed_demo, captured once by capture_demo_assets. "
            "Thumbnails and files are the providers' URLs; nothing is copied."
        ),
        "assets": [record_to_json(record) for record in records],
    }
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(document, handle, indent=1, ensure_ascii=False)
        handle.write("\n")


# ------------------------------------------------------------------ seeding


def seed_demo(snapshot: dict[Ref, AssetRecord] | None = None) -> SeedReport:
    """Load the demo members, their libraries and their packs; return what was made.

    Offline: every Asset comes from the snapshot (load_snapshot()), never from a
    provider. Safe to run again: it creates only what's missing, resets the demo
    passwords to DEMO_PASSWORD, and puts each demo pack's details, tags,
    visibility and items (position and import path) back as defined. Entries a
    demo member already has are left as they are. Raises ValueError, before
    writing anything, if the snapshot lacks an asset the demo needs.
    """
    snapshot = load_snapshot() if snapshot is None else snapshot
    missing = [ref for ref in demo_asset_refs() if ref not in snapshot]
    if missing:
        raise ValueError(
            "The demo snapshot lacks "
            + ", ".join(f"{provider} {external_id}" for provider, external_id in missing)
            + ". Run capture_demo_assets."
        )
    report = SeedReport(usernames=list(DEMO_USERS))
    with transaction.atomic():
        users = {}
        for username in DEMO_USERS:
            user, created = get_user_model().objects.get_or_create(username=username)
            user.set_password(DEMO_PASSWORD)
            user.save(update_fields=["password"])
            users[username] = user
            report.users += created

        assets_before = Asset.objects.count()
        for ref in demo_asset_refs():
            Asset.objects.from_record(snapshot[ref])  # stored once, never fetched
        report.assets = Asset.objects.count() - assets_before

        entries: dict[tuple[str, Ref], SavedAsset] = {}
        for username, user in users.items():
            for demo in demo_entries(username):
                # The Asset is stored already, so save_to_library() never calls a provider.
                entry, created = save_to_library(
                    user,
                    *demo.ref,
                    status=demo.status,
                    rating=demo.rating,
                    notes=demo.notes,
                )
                entries[(username, demo.ref)] = entry
                report.entries += created

        for demo_pack in DEMO_PACKS:
            report_pack, report_items = _seed_pack(demo_pack, users[demo_pack.owner], entries)
            report.packs += report_pack
            report.items += report_items
    return report


def _seed_pack(
    demo: DemoPack, owner, entries: dict[tuple[str, Ref], SavedAsset]
) -> tuple[int, int]:
    """Create or restore one demo pack; return (packs created, items created)."""
    pack = Pack.objects.filter(owner=owner, title=demo.title).first()
    created = pack is None
    if created:
        pack = Pack.objects.create_pack(owner, demo.title, demo.description, demo.tags)
    else:
        pack.description = demo.description
        pack.save(update_fields=["description", "updated_at"])
        pack.tags.set(tags_from_text(demo.tags))
    if pack.visibility != demo.visibility:
        pack.set_visibility(demo.visibility)
    items_created = 0
    for position, demo_item in enumerate(demo.items):
        item, item_created = add_to_pack(pack, entries[(demo.owner, demo_item.ref)])
        items_created += item_created
        PackItem.objects.filter(pk=item.pk).update(
            position=position, import_path=demo_item.import_path
        )
    return int(created), items_created
