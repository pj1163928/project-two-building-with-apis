"""The main page's orbit hero: thumbnails of textures from public packs, circling
on rings in the texture colour, each one opening a public pack that holds it.

Textures only (user request, 2026-11-06: they look the best). Only public packs
feed it (Pack.objects.public()), never a private or unlisted one. With fewer
than HERO_MINIMUM such textures, the hero shows texture-icon tiles instead,
each opening Discover's textures.
"""

import random
from dataclasses import dataclass, field
from typing import Any

from catalog.discover import TILES_BY_KIND, KindTile, discover_url
from catalog.models import Asset

from .models import Pack, PackItem

# The one kind the hero shows.
HERO_KIND = "texture"

# How many thumbnails the hero shows at most, and how many distinct textures it
# needs before it shows thumbnails rather than the texture-icon tiles.
HERO_SIZE = 18
HERO_MINIMUM = 6

# The rings, innermost first: each one's size (a percentage of the orbit's
# width) and how long one turn takes (seconds). Up to HERO_MINIMUM tiles use
# the outermost ring alone; more fill the rings inwards, each ring's share in
# proportion to its size, so the busiest is outermost.
RING_SIZES = (46, 66, 86)
RING_SPINS = (90, 120, 150)

# The fallback: this many texture-icon tiles on the outermost ring.
FALLBACK_TILES = 6

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
    """One tile on a ring: a texture's thumbnail opening a public pack that
    holds it, or (in the fallback) a texture icon opening Discover's textures."""

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
        providers' texture spheres), shown with no tile behind it so the
        texture itself floats on the ring."""
        return bool(self.asset is not None and self.asset.thumbnail_url)


@dataclass(frozen=True)
class OrbitRing:
    """One ring: its tiles, its size (a percentage of the orbit's width), how
    long one turn takes and which way it turns."""

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
        return round(2 + self.size / 26, 2)


@dataclass(frozen=True)
class HeroOrbit:
    """The hero's rings, innermost first."""

    rings: list[OrbitRing]
    is_fallback: bool

    @property
    def thumbs(self) -> list[OrbitThumb]:
        """Every tile on every ring."""
        return [thumb for ring in self.rings for thumb in ring.thumbs]


def _public_textures() -> list[int]:
    """Every distinct texture held by a public pack, as asset ids in order.

    Starts from Pack.objects.public(), so a private or unlisted pack's
    textures never get in."""
    rows = (
        PackItem.objects.filter(pack__in=Pack.objects.public(), saved_asset__asset__kind=HERO_KIND)
        .order_by()  # PackItem's default ordering would defeat DISTINCT
        .values_list("saved_asset__asset_id", flat=True)
        .distinct()
    )
    return sorted(set(rows))


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


def ring_counts(total: int) -> list[int]:
    """How many of `total` tiles each ring holds, innermost first.

    One ring per HERO_MINIMUM tiles (at least one, at most len(RING_SIZES)),
    always the outermost ones; each ring's share is in proportion to its size,
    any remainder going to the outer rings, so the busiest is outermost."""
    count = max(1, min(len(RING_SIZES), -(-total // HERO_MINIMUM)))
    sizes = RING_SIZES[-count:]
    shares = [total * size // sum(sizes) for size in sizes]
    for index in range(total - sum(shares)):
        shares[-1 - index % count] += 1
    return shares


def _rings(placed: list[tuple[str, str, Any, Any]], rng: random.Random) -> list[OrbitRing]:
    """Lay (url, label, asset, pack) tiles out on the rings, innermost first,
    each ring's tiles evenly spaced from a random start, neighbours turning
    opposite ways."""
    counts = ring_counts(len(placed))
    first = len(RING_SIZES) - len(counts)
    rings, start = [], 0
    for offset, count in enumerate(counts):
        index = first + offset
        tiles = placed[start : start + count]
        start += count
        begin, step = rng.uniform(0, 360), 360 / count
        rings.append(
            OrbitRing(
                kind=HERO_KIND,
                size=RING_SIZES[index],
                spin=RING_SPINS[index],
                reverse=index % 2 == 1,
                thumbs=[
                    OrbitThumb(
                        kind=HERO_KIND,
                        url=url,
                        label=label,
                        angle=round((begin + n * step) % 360, 2),
                        asset=asset,
                        pack=pack,
                    )
                    for n, (url, label, asset, pack) in enumerate(tiles)
                ],
            )
        )
    return rings


def hero_orbit(rng: random.Random | None = None) -> HeroOrbit:
    """The orbit hero for the main page.

    Up to HERO_SIZE distinct textures from public packs, picked at random, on
    up to three rings (the busiest outermost). Each tile opens the newest
    public pack holding its texture. Private and unlisted packs never feed it:
    not a texture, not a link. Other kinds never show. With fewer than
    HERO_MINIMUM distinct textures, it's FALLBACK_TILES texture-icon tiles
    instead, opening Discover's textures. Pass `rng` for a repeatable pick.
    """
    rng = rng or random.Random()
    available = _public_textures()
    if len(available) < HERO_MINIMUM:
        url = discover_url(HERO_KIND)
        placed = [(url, "Discover textures", None, None)] * FALLBACK_TILES
        return HeroOrbit(rings=_rings(placed, rng), is_fallback=True)
    ids = rng.sample(available, min(HERO_SIZE, len(available)))
    assets = Asset.objects.in_bulk(ids)
    packs = _newest_public_packs(ids)
    placed = [
        (
            packs[asset_id].get_public_url(),
            f"{assets[asset_id].title}, in {packs[asset_id].title}",
            assets[asset_id],
            packs[asset_id],
        )
        for asset_id in ids
    ]
    return HeroOrbit(rings=_rings(placed, rng), is_fallback=False)
