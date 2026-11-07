"""The orbit hero on the main page (Phase 12): thumbnails of textures from public
packs only (textures only at the user's request, 2026-11-06), each opening a
public pack that holds it, on rings in the texture colour; the texture-icon
tiles below HERO_MINIMUM textures.

App tests, so provider functions are never reached.
"""

import random
import re
from itertools import pairwise

import pytest

from catalog.models import SavedAsset
from packs.hero import RING_SIZES, hero_orbit, ring_counts
from packs.models import Pack
from packs.services import add_to_pack

pytestmark = pytest.mark.django_db


@pytest.fixture
def owner(django_user_model, password):
    return django_user_model.objects.create_user(username="hero_owner", password=password)


@pytest.fixture
def asset_maker(make_asset):
    """Make `count` new assets of `kind`, each with its own external id."""
    counter = iter(range(10_000))

    def make(kind="texture", count=1):
        assets = []
        for _ in range(count):
            number = next(counter)
            assets.append(
                make_asset(
                    external_id=f"{kind}_{number:03d}",
                    kind=kind,
                    title=f"{kind.title()} {number:03d}",
                )
            )
        return assets

    return make


@pytest.fixture
def pack_of(owner):
    """A pack of `owner`'s holding `assets` (saved to their library as needed)."""

    def make(title, assets, visibility=Pack.Visibility.PUBLIC, user=None):
        user = user or owner
        pack = Pack.objects.create_pack(user, title, "", "")
        for asset in assets:
            entry, _ = SavedAsset.objects.get_or_create(user=user, asset=asset)
            add_to_pack(pack, entry)
        pack.set_visibility(visibility)
        return pack

    return make


def _shown(orbit):
    return {thumb.asset.pk for thumb in orbit.thumbs}


# ------------------------------------------------------------------ TDD 1: public packs only


def test_the_hero_never_draws_from_private_or_unlisted_packs(asset_maker, pack_of):
    public = asset_maker("texture", 6)
    private_only = asset_maker("texture", 4)
    unlisted_only = asset_maker("texture", 4)
    pack_of("Shared kit", public)
    pack_of("Secret kit", private_only, Pack.Visibility.PRIVATE)
    pack_of("Link kit", unlisted_only, Pack.Visibility.UNLISTED)

    for seed in range(5):
        orbit = hero_orbit(random.Random(seed))
        assert not orbit.is_fallback
        assert _shown(orbit) == {asset.pk for asset in public}


# ------------------------------------------------------------------ TDD 2: links to a public pack


def test_each_thumbnail_links_to_a_public_pack_that_holds_it(
    django_user_model, password, asset_maker, pack_of
):
    other = django_user_model.objects.create_user(username="hero_other", password=password)
    assets = asset_maker("texture", 7)
    shared = assets[0]
    # The shared texture sits in a private and an unlisted pack made last, and in two
    # public packs: it must link to a public one, never to the others.
    older = pack_of("Older public kit", assets[:4])
    newer = pack_of("Newer public kit", [shared, *assets[4:]], user=other)
    secret = pack_of("Secret kit", [shared], Pack.Visibility.PRIVATE)
    link_only = pack_of("Link kit", [shared], Pack.Visibility.UNLISTED)

    orbit = hero_orbit(random.Random(1))
    assert len(orbit.thumbs) == len(assets)
    for thumb in orbit.thumbs:
        assert thumb.pack is not None, f"{thumb.asset.title} links to no pack"
        assert thumb.pack.is_public
        assert thumb.pack.items.filter(saved_asset__asset=thumb.asset).exists()
        assert thumb.url == thumb.pack.get_public_url()
        assert thumb.url not in (secret.get_public_url(), link_only.get_public_url())
    by_asset = {thumb.asset.pk: thumb.pack for thumb in orbit.thumbs}
    assert by_asset[shared.pk] == newer  # the newest public pack holding it
    assert by_asset[assets[1].pk] == older


# ------------------------------------------------------------------ TDD 3: threshold and cap


def test_below_six_textures_the_texture_tiles_show_and_above_eighteen_it_caps(asset_maker, pack_of):
    # Five distinct textures, one of them in two public packs, and other kinds that
    # don't count: still five, so texture-icon tiles show, opening Discover's textures.
    five = asset_maker("texture", 5)
    pack_of("Kit one", five + asset_maker("hdri", 3) + asset_maker("model", 3))
    pack_of("Kit two", five[:1])
    orbit = hero_orbit(random.Random(0))
    assert orbit.is_fallback
    assert len(orbit.thumbs) == 6
    for thumb in orbit.thumbs:
        assert thumb.asset is None and thumb.pack is None
        assert thumb.kind == "texture"
        assert thumb.url == "/discover/?type=texture"

    # A sixth distinct texture: the thumbnails show instead.
    pack_of("Kit three", asset_maker("texture", 1))
    orbit = hero_orbit(random.Random(0))
    assert not orbit.is_fallback
    assert len(orbit.thumbs) == 6

    # Far more than eighteen: exactly eighteen distinct textures.
    pack_of("Big kit", asset_maker("texture", 24))
    for seed in range(5):
        orbit = hero_orbit(random.Random(seed))
        shown = [thumb.asset.pk for thumb in orbit.thumbs]
        assert len(shown) == 18
        assert len(set(shown)) == 18


# ------------------------------------------------------------------ the pick and the rings


def test_only_textures_ever_show(asset_maker, pack_of):
    pack_of(
        "Mixed kit",
        asset_maker("texture", 7)
        + asset_maker("hdri", 5)
        + asset_maker("model", 5)
        + asset_maker("sound", 5),
    )
    for seed in range(5):
        orbit = hero_orbit(random.Random(seed))
        assert {thumb.asset.kind for thumb in orbit.thumbs} == {"texture"}
        assert len(orbit.thumbs) == 7
        assert {ring.kind for ring in orbit.rings} == {"texture"}


@pytest.mark.parametrize(
    "total, counts",
    [(6, [6]), (7, [3, 4]), (12, [5, 7]), (13, [3, 4, 6]), (18, [4, 6, 8])],
)
def test_tiles_fill_the_outer_rings_first_the_busiest_outermost(total, counts):
    assert ring_counts(total) == counts


def test_the_rings_are_the_texture_colour_turning_opposite_ways(asset_maker, pack_of):
    pack_of("Kit", asset_maker("texture", 18))
    orbit = hero_orbit(random.Random(3))
    assert [ring.size for ring in orbit.rings] == list(RING_SIZES)
    assert [len(ring.thumbs) for ring in orbit.rings] == [4, 6, 8]
    assert {ring.ring_class for ring in orbit.rings} == {"border-texture"}
    # Neighbouring rings turn opposite ways; tiles are evenly spaced round each.
    assert [ring.reverse for ring in orbit.rings] == [False, True, False]
    angles = sorted(thumb.angle for thumb in orbit.rings[-1].thumbs)
    gaps = [b - a for a, b in pairwise(angles)]
    assert all(abs(gap - 45) < 0.05 for gap in gaps)


# ------------------------------------------------------------------ on the main page


def _orbit_html(html):
    return html.split('<div id="home-orbit"', 1)[1].split("</section>", 1)[0]


@pytest.fixture
def public_kit(asset_maker, pack_of):
    return pack_of("Public kit", asset_maker("texture", 6) + asset_maker("sound", 3))


@pytest.mark.parametrize("signed_in", [False, True])
def test_the_page_shows_the_textures_to_visitors_and_members(client, member, public_kit, signed_in):
    if signed_in:
        client.force_login(member)
    orbit = _orbit_html(client.get("/").content.decode())
    # Six textures, each floating as a cut-out; the pack's sounds never show.
    assert len(re.findall(r'class="orbit-thumb[ "]', orbit)) == 6
    assert orbit.count('class="orbit-thumb is-cutout"') == 6
    assert 'data-kind="sound"' not in orbit
    assert orbit.count(f'href="{public_kit.get_public_url()}"') == 6
    assert 'referrerpolicy="no-referrer"' in orbit


def test_the_legend_and_note_are_gone(client, public_kit):
    orbit = _orbit_html(client.get("/").content.decode())
    assert "home-orbit-legend" not in orbit and "home-orbit-note" not in orbit
    assert "Public packs will orbit here" not in client.get("/").content.decode()


def test_the_orbit_never_carries_a_logo(client, public_kit):
    orbit = _orbit_html(client.get("/").content.decode())
    assert "mark" not in orbit and "wordmark" not in orbit and "brand/" not in orbit


def test_a_private_or_unlisted_packs_texture_never_reaches_the_page(
    client, member, asset_maker, pack_of, public_kit
):
    secret = asset_maker("texture", 1)[0]
    secret.title = "SENTINEL secret texture"
    secret.thumbnail_url = "https://cdn.example.org/SENTINEL.png"
    secret.save()
    private = pack_of("Secret kit", [secret], Pack.Visibility.PRIVATE)
    unlisted = pack_of("Link kit", [secret], Pack.Visibility.UNLISTED)
    for viewer in (None, private.owner, member):
        if viewer:
            client.force_login(viewer)
        orbit = _orbit_html(client.get("/").content.decode())
        assert "SENTINEL" not in orbit
        assert private.slug not in orbit and unlisted.slug not in orbit
        assert unlisted.share_token not in orbit


def test_a_texture_without_an_image_shows_its_icon_in_a_frame(client, public_kit):
    entry = public_kit.ordered_items()[0].saved_asset
    entry.asset.thumbnail_url = ""
    entry.asset.save()
    orbit = _orbit_html(client.get("/").content.decode())
    assert orbit.count("<img") == 5
    assert orbit.count('class="orbit-thumb is-cutout"') == 5
    assert orbit.count('class="orbit-thumb"') == 1


def test_the_orbit_shows_nothing_from_anyones_library(client, public_kit):
    entry = public_kit.ordered_items()[0].saved_asset
    entry.notes = "SENTINEL-NOTE"
    entry.rating = 1
    entry.status = SavedAsset.Status.REJECTED
    entry.save()
    orbit = _orbit_html(client.get("/").content.decode())
    assert "SENTINEL-NOTE" not in orbit and "Rejected" not in orbit and "star" not in orbit


def test_with_few_textures_the_page_shows_texture_tiles(client, asset_maker, pack_of):
    pack_of("Small kit", asset_maker("texture", 5) + asset_maker("model", 4))
    orbit = _orbit_html(client.get("/").content.decode())
    assert 'class="orbit is-fallback"' in orbit
    assert "<img" not in orbit
    assert orbit.count('href="/discover/?type=texture"') == 6


def test_type_colour_in_the_orbit_is_only_the_texture_rings_and_icons(client, public_kit):
    orbit = _orbit_html(client.get("/").content.decode())
    classes = " ".join(re.findall(r'class="([^"]*)"', orbit))
    tokens = re.findall(r"\b[\w:-]*-(?:texture|hdri|model|sound)\b", classes)
    # One ring, six tile icons (under their images).
    assert sorted(set(tokens)) == ["border-texture", "text-texture"]
    assert len(tokens) == 1 + 6


def test_a_gallery_swap_leaves_the_orbit_out(client, public_kit):
    response = client.get("/?q=kit", headers={"HX-Request": "true"})
    assert 'id="gallery-results"' in response.content.decode()
    assert "home-orbit" not in response.content.decode()


def test_the_hero_is_a_cover_with_the_rings_blended_in():
    from django.conf import settings

    css = (settings.BASE_DIR / "styles" / "source.css").read_text(encoding="utf-8")
    hero = re.search(r"\.home-hero \{([^}]*)\}", css).group(1)
    # The window less both bars, or less only the status bar where the title bar and
    # sidebar tuck away (a mouse; user request, 2026-11-06).
    assert "min-height: calc(100dvh - var(--cover-offset, 4.5rem));" in hero
    assert "#app:has(#home-orbit) { --cover-offset: 1.5rem;" in css
    orbit = re.search(r"  \.orbit \{([^}]*)\}", css).group(1)
    assert "mask-image: linear-gradient(" in orbit and "transparent);" in orbit
    assert ".orbit-ring::before {" in css and "opacity: 0.4;" in css


def test_the_orbit_pauses_on_hover_and_focus_and_stills_for_reduced_motion():
    from django.conf import settings

    css = (settings.BASE_DIR / "styles" / "source.css").read_text(encoding="utf-8")
    assert ".orbit:has(.orbit-thumb:hover) .orbit-ring" in css
    assert ".orbit:focus-within .orbit-ring" in css
    assert "animation-play-state: paused" in css
    reduced = css.split("@media (prefers-reduced-motion: reduce)")
    assert any(".orbit-ring, .orbit-face { animation: none; }" in block for block in reduced[1:])
