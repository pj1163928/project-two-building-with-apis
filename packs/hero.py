"""The main page's orbit hero: thumbnails of assets from public packs, circling
on rings coloured by type, each one opening a public pack that holds it.

Only public packs feed it (Pack.objects.public()), never a private or
unlisted one. With fewer than HERO_MINIMUM such assets, the hero shows one
type-icon tile per type instead, each opening Discover for that type.
"""

import random
from dataclasses import dataclass, field
from typing import Any

from catalog.discover import KIND_TILES, TILES_BY_KIND, KindTile, discover_url
from catalog.models import Asset
from providers import KINDS

from .models import Pack, PackItem

# How many thumbnails the hero shows at most, and how many distinct assets it
# needs before it shows thumbnails rather than the type-icon tiles.
HERO_SIZE = 18
HERO_MINIMUM = 6

# The ring sizes, as a percentage of the orbit's width: the outermost, and the
# step in to the next.
OUTER_RING = 86
RING_STEP = 14

# Kinds whose thumbnails are renders on a transparent background.
CUTOUT_KINDS = ("texture", "model")

# Each ring's outline is its type's colour. Written out in full so Tailwind
# finds them; type colours mean the asset's type and nothing else.
RING_CLASSES = {
    "texture": "border-texture",
    "hdri": "border-hdri",
    "model": "border-model",
    "sound": "border-sound",
}


@dataclass(frozen=True)
class OrbitThumb:
    """One tile on a ring: an asset's thumbnail opening a public pack that
    holds it, or (in the fallback) a type icon opening Discover for that type."""

    kind: str
    url: str
    label: str
    angle: float
    asset: Any = None
    pack: Any = None

    @property
    def tile(self) -> KindTile:
        return TILES_BY_KIND[self.kind]

    @property
    def is_cutout(self) -> bool:
        """Whether the thumbnail is a render on a transparent background (the
        providers' texture spheres and model renders), shown with no tile
        behind it so the asset itself floats on the ring."""
        return bool(
            self.asset is not None and self.kind in CUTOUT_KINDS and self.asset.thumbnail_url
        )


@dataclass(frozen=True)
class OrbitRing:
    """One type's ring: its tiles, its size (a percentage of the orbit's
    width), how long one turn takes and which way it turns."""

    kind: str
    size: int
    spin: int
    reverse: bool
    thumbs: list[OrbitThumb] = field(default_factory=list)

    @property
    def tile(self) -> KindTile:
        return TILES_BY_KIND[self.kind]

    @property
    def ring_class(self) -> str:
        return RING_CLASSES[self.kind]

    @property
    def tile_rem(self) -> float:
        """How big this ring's tiles are, in rem: bigger further out, so the
        orbit reads with some depth."""
        return round(2.4 + self.size / 22, 2)


@dataclass(frozen=True)
class HeroOrbit:
    """The hero's rings, innermost first, and the counts its note gives:
    distinct assets in public packs, and public packs holding any."""

    rings: list[OrbitRing]
    is_fallback: bool
    asset_count: int = 0
    pack_count: int = 0

    @property
    def thumbs(self) -> list[OrbitThumb]:
        """Every tile on every ring."""
        return [thumb for ring in self.rings for thumb in ring.thumbs]


def _public_assets() -> dict[int, str]:
    """Every distinct Asset held by a public pack, as {asset id: kind}.

    Starts from Pack.objects.public(), so a private or unlisted pack's
    assets never get in."""
    rows = (
        PackItem.objects.filter(pack__in=Pack.objects.public())
        .values_list("saved_asset__asset_id", "saved_asset__asset__kind")
        .distinct()
    )
    return dict(rows)


def _newest_public_packs(asset_ids: list[int]) -> dict[int, Pack]:
    """For each asset id, the newest public pack holding it (ties by id).

    Reads only public packs, so a private or unlisted pack holding the same
    asset is never the link, however new it is."""
    items = (
        PackItem.objects.filter(pack__in=Pack.objects.public(), saved_asset__asset_id__in=asset_ids)
        .select_related("pack", "saved_asset")
        .order_by("-pack__created_at", "-pack_id")
    )
    packs: dict[int, Pack] = {}
    for item in items:
        packs.setdefault(item.saved_asset.asset_id, item.pack)
    return packs


def _rings(chosen: dict[str, list[OrbitThumb]]) -> list[OrbitRing]:
    """One ring per kind with tiles, the busiest outermost (ties in Discover's
    order), each a step smaller than the one outside it, alternating direction."""
    kinds = sorted(chosen, key=lambda kind: (len(chosen[kind]), KINDS.index(kind)))
    count = len(kinds)
    return [
        OrbitRing(
            kind=kind,
            size=OUTER_RING - (count - 1 - index) * RING_STEP,
            spin=70 + index * 20,
            reverse=index % 2 == 1,
            thumbs=chosen[kind],
        )
        for index, kind in enumerate(kinds)
    ]


def _spread(placed: list[tuple[Any, Pack]], rng: random.Random) -> list[OrbitThumb]:
    """Space a ring's (asset, pack) tiles evenly around it, from a random
    starting angle. Each opens its pack's public page."""
    start = rng.uniform(0, 360)
    step = 360 / len(placed) if placed else 0
    return [
        OrbitThumb(
            kind=asset.kind,
            url=pack.get_public_url(),
            label=f"{asset.title}, in {pack.title}",
            angle=round((start + n * step) % 360, 2),
            asset=asset,
            pack=pack,
        )
        for n, (asset, pack) in enumerate(placed)
    ]


def _pick(available: dict[int, str], rng: random.Random) -> list[int]:
    """Up to HERO_SIZE asset ids, taken from each kind in turn (Discover's
    order), each kind's own ids shuffled, so no type crowds out the others:
    a kind runs out only when it has no more assets."""
    queues: dict[str, list[int]] = {kind: [] for kind in KINDS}
    for asset_id in sorted(available):
        queues[available[asset_id]].append(asset_id)
    for ids in queues.values():
        rng.shuffle(ids)
    picked: list[int] = []
    while len(picked) < HERO_SIZE and any(queues.values()):
        for kind in KINDS:
            if queues[kind] and len(picked) < HERO_SIZE:
                picked.append(queues[kind].pop())
    return picked


def _fallback(rng: random.Random) -> HeroOrbit:
    """The type-icon tiles: one ring per type, each with one tile opening
    Discover for that type."""
    chosen = {
        tile.key: [
            OrbitThumb(
                kind=tile.key,
                url=discover_url(tile.key),
                label=f"Discover {tile.label.lower()}",
                angle=round(rng.uniform(0, 360), 2),
            )
        ]
        for tile in KIND_TILES
    }
    return HeroOrbit(rings=_rings(chosen), is_fallback=True)


def hero_orbit(rng: random.Random | None = None) -> HeroOrbit:
    """The orbit hero for the main page.

    Up to HERO_SIZE distinct assets from public packs, chosen at random but
    from each type in turn, on one ring per type (the busiest outermost).
    Each tile opens the newest public pack holding its asset. Private and
    unlisted packs never feed it: not an asset, not a link. With fewer than
    HERO_MINIMUM distinct assets, it's the type-icon tiles instead (one per
    type, opening Discover). Pass `rng` for a repeatable pick.
    """
    rng = rng or random.Random()
    available = _public_assets()
    if len(available) < HERO_MINIMUM:
        return _fallback(rng)
    ids = _pick(available, rng)
    assets = Asset.objects.in_bulk(ids)
    packs = _newest_public_packs(ids)
    by_kind: dict[str, list[tuple[Any, Pack]]] = {}
    for asset_id in ids:
        by_kind.setdefault(available[asset_id], []).append((assets[asset_id], packs[asset_id]))
    chosen = {kind: _spread(placed, rng) for kind, placed in by_kind.items()}
    pack_count = Pack.objects.public().filter(items__isnull=False).distinct().count()
    return HeroOrbit(
        rings=_rings(chosen),
        is_fallback=False,
        asset_count=len(available),
        pack_count=pack_count,
    )
