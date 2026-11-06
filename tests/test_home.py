"""The main page (Phase 9): the four steps and sign-up prompt for visitors only,
the side panel starting collapsed, and the public gallery on the page (cards,
mosaic, HTMX swaps, empty states, and never a private or unlisted pack).

App tests, so provider functions are never reached.
"""

import re

import pytest
from django.test import Client
from django.urls import reverse

from catalog.models import SavedAsset
from packs.models import Pack
from packs.services import add_to_pack, move_item

pytestmark = pytest.mark.django_db

HOME = "/"
TYPE_TOKEN = re.compile(r"\b(?:text|bg|border|fill|stroke)-(?:texture|hdri|model|sound)\b")


@pytest.fixture
def other(django_user_model, password):
    return django_user_model.objects.create_user(username="other_member", password=password)


@pytest.fixture
def make_pack(make_asset):
    """A pack owned by `owner` holding one new asset per kind given, then made `visibility`."""
    counter = iter(range(10_000))

    def make(owner, title, *kinds, tags="", visibility=Pack.Visibility.PUBLIC):
        pack = Pack.objects.create_pack(owner, title, "", tags)
        for kind in kinds:
            number = next(counter)
            asset = make_asset(
                external_id=f"{kind}_{number:03d}",
                kind=kind,
                title=f"{kind.title()} {number:03d}",
                thumbnail_url=f"https://cdn.example.org/thumbs/{kind}_{number:03d}.png",
            )
            add_to_pack(pack, SavedAsset.objects.create(user=owner, asset=asset))
        pack.set_visibility(visibility)
        return pack

    return make


def _content(html):
    return html.split('id="content"', 1)[1].split('id="page-footer"', 1)[0]


def _card(html, pack):
    match = re.search(
        rf'<li class="gallery-card" id="gallery-pack-{pack.pk}">(.*?)</li>', html, re.S
    )
    assert match, f"no gallery card for {pack.title}"
    return match.group(1)


# ------------------------------------------------------------------ visitors and members


def test_a_visitor_sees_the_four_steps_and_both_buttons(client):
    content = _content(client.get(HOME).content.decode())
    steps = content.split('id="home-steps"', 1)[1].split("</section>", 1)[0]
    found = re.findall(
        r'home-step-number micro">(\d\d)</span>.*?home-step-title">(\w+)<', steps, re.S
    )
    assert found == [("01", "Discover"), ("02", "Save"), ("03", "Pack"), ("04", "Export")]
    assert re.search(r'<a href="/accounts/signup/" id="home-signup"[^>]*>Sign up<', content)
    assert re.search(r'<a href="/accounts/login/" id="home-signin"[^>]*>Sign in<', content)


def test_a_member_sees_no_steps_and_no_sign_up_prompt(member_client):
    content = _content(member_client.get(HOME).content.decode())
    assert 'id="home-steps"' not in content
    assert "/accounts/signup/" not in content
    assert 'id="home-signin"' not in content
    assert 'id="gallery"' in content  # the gallery is for everyone


@pytest.mark.parametrize("signed_in", [False, True])
def test_the_main_page_and_its_gallery_work_signed_out_and_in(client, member, signed_in):
    if signed_in:
        client.force_login(member)
    assert client.get(HOME).status_code == 200
    assert client.get(HOME, {"q": "x"}, headers={"HX-Request": "true"}).status_code == 200


# ------------------------------------------------------------------ the side panel


def test_the_side_panel_starts_collapsed_on_the_main_page_only(client):
    home = client.get(HOME).content.decode()
    assert re.search(r'<html [^>]*data-panel-start="collapsed"', home)
    assert re.search(r'<div id="app" [^>]*data-panel-start="collapsed"', home)
    # The head script reads it before first paint, ahead of the saved choice.
    assert 'dataset.panelStart || localStorage.getItem("ax-panel")' in home
    discover = client.get(reverse("catalog:discover")).content.decode()
    assert "data-panel-start" not in discover.split("<head>", 1)[1].split("<script>", 1)[0]
    assert 'id="app" class="h-screen flex flex-col" hx-headers' in discover
    assert not re.search(r'<div id="app" [^>]*data-panel-start', discover)


def test_boosted_swaps_apply_each_pages_panel_start():
    with open("static/js/shell.js") as handle:
        shell = handle.read()
    assert "app.dataset.panelStart" in shell
    # Called on every boosted swap, before the toggle is synced.
    after = shell.split('addEventListener("htmx:afterSwap"', 1)[1]
    assert after.index("applyPanelStart()") < after.index("syncPanel()")


# ------------------------------------------------------------------ the gallery's cards


def test_a_card_shows_the_mosaic_title_owner_tags_and_type_count(client, other, make_pack):
    pack = make_pack(
        other,
        "Medieval Village",
        "texture",
        "texture",
        "hdri",
        "sound",
        "texture",
        "sound",
        tags="Stone, timber",
    )
    card = _card(client.get(HOME).content.decode(), pack)
    assert f'<a href="/packs/{pack.slug}/" class="pack-card-link">Medieval Village</a>' in card
    assert "By other_member" in card
    assert re.findall(r"<span>([a-z ]+)</span>", card.split("pack-card-tags", 1)[1]) == [
        "stone",
        "timber",
    ]
    assert "3 textures · 1 HDRI · 2 sounds" in card


def test_the_mosaic_uses_the_first_four_items_by_position(client, other, make_pack):
    pack = make_pack(other, "Kit", "texture", "hdri", "model", "sound", "texture")
    items = list(pack.ordered_items())
    move_item(items[4], -1)  # the fifth item (a texture) moves to fourth place
    move_item(items[0], 1)  # the first (a texture) swaps with the HDRI
    order = [item.saved_asset.asset for item in pack.ordered_items()]
    card = _card(client.get(HOME).content.decode(), pack)
    thumbs = re.findall(r'<img src="https://cdn.example.org/thumbs/([a-z_0-9]+)\.png"', card)
    assert thumbs == [asset.external_id for asset in order[:4]]
    assert order[4].external_id not in card


def test_a_short_pack_fills_its_mosaic_with_empty_tiles(client, other, make_pack):
    two = make_pack(other, "Two", "sound", "texture")
    empty = make_pack(other, "Empty")
    html = client.get(HOME).content.decode()
    assert _card(html, two).count('class="gallery-tile is-blank"') == 2
    assert _card(html, two).count('class="gallery-tile" data-kind=') == 2
    assert _card(html, empty).count('class="gallery-tile is-blank"') == 4
    assert "No items yet" in _card(html, empty)


def test_the_mosaic_falls_back_to_the_type_icon_and_never_the_logo(client, other, make_pack):
    pack = make_pack(other, "Sounds", "sound")
    asset = pack.ordered_items()[0].saved_asset.asset
    asset.thumbnail_url = ""
    asset.save()
    card = _card(client.get(HOME).content.decode(), pack)
    assert "<img" not in card
    assert 'class="result-fallback text-sound"' in card
    assert "mark" not in card  # the logo never sits on a provider's thumbnail


def test_type_colour_appears_only_on_the_mosaics_type_icons(client, other, make_pack):
    make_pack(other, "Kit", "texture", "hdri", "model", "sound")
    content = _content(client.get(HOME).content.decode())
    gallery = content.split('id="gallery"', 1)[1]
    outside = content.replace(gallery, "")
    assert not TYPE_TOKEN.search(outside)
    tiles = re.findall(
        r'<span class="gallery-tile"[^>]*>.*?</span>\s*(?:<img[^>]*>)?', gallery, re.S
    )
    within = "".join(tiles)
    assert len(TYPE_TOKEN.findall(within)) == 4
    assert len(TYPE_TOKEN.findall(gallery)) == 4  # nowhere else in the gallery


def test_a_card_shows_nothing_from_anyones_library(client, member, other, make_pack):
    pack = make_pack(other, "Kit", "texture")
    entry = pack.ordered_items()[0].saved_asset
    entry.notes = "SENTINEL-NOTE secret plans"
    entry.rating = 2
    entry.status = SavedAsset.Status.REJECTED
    entry.save()
    client.force_login(member)
    card = _card(client.get(HOME).content.decode(), pack)
    assert "SENTINEL-NOTE" not in card
    assert "Rejected" not in card and "star" not in card


# ------------------------------------------------------------------ privacy on the page


@pytest.mark.parametrize("viewer", ["visitor", "owner", "other"])
def test_the_page_never_shows_a_private_or_unlisted_pack(client, member, other, make_pack, viewer):
    """Even to their owner, and for a query matching them: the gallery is public packs."""
    make_pack(other, "Castle walls", "texture", tags="castle")
    make_pack(member, "Castle keep", "texture", "sound", tags="castle", visibility="private")
    make_pack(member, "Castle gate", "texture", "sound", tags="castle", visibility="unlisted")
    if viewer == "owner":
        client.force_login(member)
    elif viewer == "other":
        client.force_login(other)
    for params in ({}, {"q": "castle"}, {"type": "sound"}, {"sort": "items"}):
        page = client.get(HOME, params).content.decode()
        fragment = client.get(HOME, params, headers={"HX-Request": "true"}).content.decode()
        for html in (page, fragment):
            assert "Castle keep" not in html and "Castle gate" not in html
    assert "Castle walls" in client.get(HOME, {"q": "castle"}).content.decode()


# ------------------------------------------------------------------ HTMX and the URL


def test_an_htmx_request_gets_only_the_results_with_the_tidy_url(client, other, make_pack):
    make_pack(other, "Forest sounds", "sound", tags="forest")
    response = client.get(
        HOME, {"q": "  forest ", "type": "sound", "sort": "junk"}, headers={"HX-Request": "true"}
    )
    html = response.content.decode()
    assert html.split("<div", 1)[1].startswith(' id="gallery-results"')  # the fragment alone
    assert "<html" not in html and 'id="gallery-toolbar"' not in html
    assert "Forest sounds" in html
    assert response["HX-Push-Url"] == "/?q=forest&type=sound"


def test_a_direct_or_boosted_visit_gets_the_whole_page_in_the_same_state(client, other, make_pack):
    make_pack(other, "Forest sounds", "sound", tags="forest")
    for headers in ({}, {"HX-Request": "true", "HX-Boosted": "true"}):
        html = client.get(HOME, {"q": "forest", "type": "sound", "sort": "items"}, headers=headers)
        html = html.content.decode()
        assert "<html" in html
        toolbar = html.split('id="gallery-toolbar"', 1)[1].split("</form>", 1)[0]
        assert 'name="q" value="forest"' in toolbar
        assert '<option value="sound" selected>' in toolbar
        assert '<option value="items" selected>' in toolbar
        assert "Forest sounds" in html


def test_the_toolbar_swaps_the_results_and_pushes_the_url(client):
    html = client.get(HOME).content.decode()
    form = re.search(r'<form id="gallery-toolbar"[^>]*>', html).group(0)
    for part in (
        'hx-get="/"',
        'hx-target="#gallery-results"',
        'hx-swap="outerHTML"',
        'hx-push-url="true"',
        "change from:.gallery-control",
        "input changed delay:300ms from:#gallery-search",
    ):
        assert part in form


def test_the_pager_links_are_real_urls_that_swap_the_results(client, other, make_pack):
    for n in range(13):
        make_pack(other, f"Pack {n:02d}")
    html = client.get(HOME, {"sort": "items"}).content.decode()
    pager = html.split('id="gallery-pager"', 1)[1].split("</nav>", 1)[0]
    assert 'href="/?sort=items&amp;page=2"' in pager
    assert 'hx-target="#gallery-results"' in pager and 'hx-push-url="true"' in pager
    assert "Page 1 of 2" in pager
    assert "1–12 of 13 public packs" in html


# ------------------------------------------------------------------ empty states


def test_no_public_packs_says_so_with_the_next_step(client, member, make_pack):
    make_pack(member, "Mine", "texture", visibility="private")
    html = client.get(HOME).content.decode()
    assert "No public packs yet." in html
    assert 'href="/accounts/signup/"' in html.split('id="gallery-results"', 1)[1]
    client.force_login(member)
    results = client.get(HOME).content.decode().split('id="gallery-results"', 1)[1]
    assert "No public packs yet." in results and 'href="/packs/"' in results


def test_no_matches_offers_to_clear_the_filters(client, other, make_pack):
    make_pack(other, "Forest", "sound")
    by_word = Client().get(HOME, {"q": "zzqq"}).content.decode()
    assert "No public pack matches “zzqq”." in by_word
    assert 'href="/#gallery"' in by_word and "Clear filters" in by_word
    by_type = Client().get(HOME, {"type": "model"}).content.decode()
    assert "No public pack holds that type yet." in by_type
