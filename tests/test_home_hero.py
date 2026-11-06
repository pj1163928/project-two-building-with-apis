"""The orbit hero on the main page (Phase 12): thumbnails of assets from public
packs only, each opening a public pack that holds it, on rings coloured by
type; the type-icon tiles below HERO_MINIMUM assets.

App tests, so provider functions are never reached.
"""

import random
from itertools import pairwise

import pytest

from catalog.models import SavedAsset
from packs.hero import hero_orbit
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
    public = asset_maker("texture", 3) + asset_maker("hdri", 3)
    private_only = asset_maker("model", 4)
    unlisted_only = asset_maker("sound", 4)
    pack_of("Shared kit", public)
    pack_of("Secret kit", private_only, Pack.Visibility.PRIVATE)
    pack_of("Link kit", unlisted_only, Pack.Visibility.UNLISTED)

    for seed in range(5):
        orbit = hero_orbit(random.Random(seed))
        assert not orbit.is_fallback
        assert _shown(orbit) == {asset.pk for asset in public}
        assert {ring.kind for ring in orbit.rings} == {"texture", "hdri"}


# ------------------------------------------------------------------ TDD 2: links to a public pack


def test_each_thumbnail_links_to_a_public_pack_that_holds_it(
    django_user_model, password, asset_maker, pack_of
):
    other = django_user_model.objects.create_user(username="hero_other", password=password)
    assets = asset_maker("texture", 4) + asset_maker("model", 3)
    shared = assets[0]
    # The shared asset sits in a private and an unlisted pack made last, and in two
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


def test_below_six_assets_the_type_tiles_show_and_above_eighteen_it_caps(asset_maker, pack_of):
    # Five distinct assets, one of them in two public packs: still five, so the
    # four type-icon tiles show, one per type, each opening Discover for it.
    five = asset_maker("texture", 3) + asset_maker("sound", 2)
    pack_of("Kit one", five)
    pack_of("Kit two", five[:1])
    orbit = hero_orbit(random.Random(0))
    assert orbit.is_fallback
    assert [ring.kind for ring in orbit.rings] == ["texture", "hdri", "model", "sound"]
    for ring in orbit.rings:
        assert len(ring.thumbs) == 1
        (thumb,) = ring.thumbs
        assert thumb.asset is None and thumb.pack is None
        assert thumb.kind == ring.kind
        assert thumb.url == f"/discover/?type={ring.kind}"

    # A sixth distinct asset: the thumbnails show instead.
    pack_of("Kit three", asset_maker("hdri", 1))
    orbit = hero_orbit(random.Random(0))
    assert not orbit.is_fallback
    assert len(orbit.thumbs) == 6

    # Far more than eighteen: exactly eighteen distinct assets, each on its
    # own type's ring.
    pack_of("Big kit", asset_maker("texture", 20) + asset_maker("model", 6))
    for seed in range(5):
        orbit = hero_orbit(random.Random(seed))
        shown = [thumb.asset.pk for thumb in orbit.thumbs]
        assert len(shown) == 18
        assert len(set(shown)) == 18
        for ring in orbit.rings:
            assert ring.thumbs
            assert {thumb.asset.kind for thumb in ring.thumbs} == {ring.kind}


# ------------------------------------------------------------------ the pick and the rings


def test_thumbnails_are_spread_across_the_types_not_crowded_by_textures(asset_maker, pack_of):
    pack_of(
        "Mixed kit",
        asset_maker("texture", 30)
        + asset_maker("hdri", 3)
        + asset_maker("model", 3)
        + asset_maker("sound", 3),
    )
    for seed in range(5):
        orbit = hero_orbit(random.Random(seed))
        counts = {ring.kind: len(ring.thumbs) for ring in orbit.rings}
        # Every other type shows all it has; textures fill the rest of the 18.
        assert counts == {"hdri": 3, "model": 3, "sound": 3, "texture": 9}


def test_the_busiest_ring_is_outermost_and_each_ring_is_its_type_colour(asset_maker, pack_of):
    pack_of(
        "Kit",
        asset_maker("sound", 1)
        + asset_maker("model", 4)
        + asset_maker("texture", 2)
        + asset_maker("hdri", 3),
    )
    orbit = hero_orbit(random.Random(3))
    assert [ring.kind for ring in orbit.rings] == ["sound", "texture", "hdri", "model"]
    sizes = [ring.size for ring in orbit.rings]
    assert sizes == sorted(sizes) and sizes[-1] == 100 and len(set(sizes)) == 4
    assert [ring.ring_class for ring in orbit.rings] == [
        "border-sound",
        "border-texture",
        "border-hdri",
        "border-model",
    ]
    # Neighbouring rings turn opposite ways; tiles are evenly spaced round each.
    assert [ring.reverse for ring in orbit.rings] == [False, True, False, True]
    model = orbit.rings[-1]
    angles = sorted(thumb.angle for thumb in model.thumbs)
    gaps = [b - a for a, b in pairwise(angles)]
    assert all(abs(gap - 90) < 0.05 for gap in gaps)


def test_the_centre_counts_the_assets_and_packs(asset_maker, pack_of):
    assets = asset_maker("texture", 7)
    pack_of("One", assets[:4])
    pack_of("Two", assets[3:])
    pack_of("Empty", [])
    pack_of("Secret", asset_maker("model", 2), Pack.Visibility.PRIVATE)
    orbit = hero_orbit(random.Random(0))
    assert (orbit.asset_count, orbit.pack_count) == (7, 2)


# ------------------------------------------------------------------ on the main page


def _orbit_html(html):
    return html.split('<div id="home-orbit"', 1)[1].split("</section>", 1)[0]


@pytest.fixture
def public_kit(asset_maker, pack_of):
    return pack_of("Public kit", asset_maker("texture", 4) + asset_maker("sound", 3))


@pytest.mark.parametrize("signed_in", [False, True])
def test_the_page_shows_the_orbit_to_visitors_and_members(client, member, public_kit, signed_in):
    if signed_in:
        client.force_login(member)
    orbit = _orbit_html(client.get("/").content.decode())
    assert orbit.count('class="orbit-thumb"') == 7
    assert orbit.count(f'href="{public_kit.get_public_url()}"') == 7
    assert 'referrerpolicy="no-referrer"' in orbit
    assert "7 assets from 1 public pack, one ring per type." in orbit
    assert 'id="home-orbit-legend"' in orbit and "Textures" in orbit and "Sounds" in orbit


def test_the_orbit_never_carries_a_logo(client, public_kit):
    orbit = _orbit_html(client.get("/").content.decode())
    assert "mark" not in orbit and "wordmark" not in orbit and "brand/" not in orbit


def test_a_private_or_unlisted_packs_asset_never_reaches_the_page(
    client, member, asset_maker, pack_of, public_kit
):
    secret = asset_maker("model", 1)[0]
    secret.title = "SENTINEL secret model"
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


def test_a_thumbnail_without_an_image_shows_its_type_icon(client, public_kit):
    entry = public_kit.ordered_items()[0].saved_asset
    entry.asset.thumbnail_url = ""
    entry.asset.save()
    orbit = _orbit_html(client.get("/").content.decode())
    assert orbit.count("<img") == 6
    assert orbit.count('class="result-fallback text-texture"') == 4


def test_the_orbit_shows_nothing_from_anyones_library(client, public_kit):
    entry = public_kit.ordered_items()[0].saved_asset
    entry.notes = "SENTINEL-NOTE"
    entry.rating = 1
    entry.status = SavedAsset.Status.REJECTED
    entry.save()
    orbit = _orbit_html(client.get("/").content.decode())
    assert "SENTINEL-NOTE" not in orbit and "Rejected" not in orbit and "star" not in orbit


def test_with_few_assets_the_page_shows_the_four_type_tiles(client, asset_maker, pack_of):
    pack_of("Small kit", asset_maker("texture", 5))
    orbit = _orbit_html(client.get("/").content.decode())
    assert 'class="orbit is-fallback"' in orbit
    assert "<img" not in orbit
    for kind in ("texture", "hdri", "model", "sound"):
        assert f'href="/discover/?type={kind}"' in orbit
    assert "Public packs will orbit here" in orbit


def test_type_colour_in_the_orbit_is_only_its_rings_icons_and_legend(client, public_kit):
    import re

    orbit = _orbit_html(client.get("/").content.decode())
    classes = " ".join(re.findall(r'class="([^"]*)"', orbit))
    tokens = re.findall(r"\b[\w:-]*-(?:texture|hdri|model|sound)\b", classes)
    # Two rings, seven tile icons, two legend icons.
    assert sorted(set(tokens)) == ["border-sound", "border-texture", "text-sound", "text-texture"]
    assert len(tokens) == 2 + 7 + 2


def test_a_gallery_swap_leaves_the_orbit_out(client, public_kit):
    response = client.get("/?q=kit", headers={"HX-Request": "true"})
    assert 'id="gallery-results"' in response.content.decode()
    assert "home-orbit" not in response.content.decode()


def test_the_orbit_pauses_on_hover_and_focus_and_stills_for_reduced_motion():
    from django.conf import settings

    css = (settings.BASE_DIR / "styles" / "source.css").read_text(encoding="utf-8")
    assert ".orbit:hover .orbit-ring" in css and ".orbit:focus-within .orbit-ring" in css
    assert "animation-play-state: paused" in css
    reduced = css.split("@media (prefers-reduced-motion: reduce)")
    assert any(".orbit-ring, .orbit-face { animation: none; }" in block for block in reduced[1:])
