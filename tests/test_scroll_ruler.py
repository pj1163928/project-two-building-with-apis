"""The right-edge scroll ruler with its section index (Phase 12; on every page at
the user's request, 2026-11-06): a scale and plain anchors to sections that exist
on the page, wide screens only, monochrome.

App tests: Discover's page never calls a provider (its shelves load later).
"""

import re

import pytest
from django.conf import settings
from django.test import Client
from django.urls import reverse

from catalog.models import SavedAsset
from packs.models import Pack
from packs.services import add_to_pack

pytestmark = pytest.mark.django_db

TYPE_TOKEN = re.compile(r"\b[\w:-]*-(?:texture|hdri|model|sound)\b")


def _ruler(html):
    match = re.search(r'<nav id="scroll-ruler".*?</nav>', html, re.S)
    assert match, "no scroll ruler"
    return match.group(0)


def _entries(ruler):
    return re.findall(
        r'<a href="#([\w-]+)" class="scroll-ruler-link" data-ruler-target="\1">'
        r'<span class="scroll-ruler-label">([^<]+)</span>',
        ruler,
    )


def _assert_each_entry_jumps_to_its_section(html):
    entries = _entries(_ruler(html))
    assert entries, "an empty section index"
    for section_id, _label in entries:
        assert html.count(f'id="{section_id}"') == 1, f"#{section_id} isn't on the page once"
    return entries


@pytest.fixture
def kit(member, make_asset):
    """A public pack of the member's holding one saved texture, and that entry."""
    entry = SavedAsset.objects.create(user=member, asset=make_asset())
    pack = Pack.objects.create_pack(member, "Brick kit", "Walls.", "brick")
    add_to_pack(pack, entry)
    pack.set_visibility(Pack.Visibility.PUBLIC)
    return pack, entry


def _every_page(kit):
    pack, entry = kit
    return [
        reverse("packs:home"),
        reverse("catalog:discover"),
        reverse("catalog:library"),
        reverse("catalog:entry", args=[entry.pk]),
        reverse("packs:list"),
        reverse("packs:create"),
        reverse("packs:builder", args=[pack.pk]),
        pack.get_public_url(),
        reverse("packs:attribution"),
        reverse("packs:attribution_packs"),
        reverse("packs:attribution_pack", args=[pack.slug]),
        reverse("packs:attribution_assets"),
        reverse("packs:attribution_asset", args=[entry.pk]),
        reverse("accounts:profile"),
        reverse("accounts:settings"),
        reverse("accounts:token"),
    ]


# ------------------------------------------------------------------ on every page


def test_every_page_has_the_ruler_and_each_entry_jumps_to_its_section(member_client, kit):
    for url in _every_page(kit):
        html = member_client.get(url).content.decode()
        assert html.count('id="scroll-ruler"') == 1, url
        _assert_each_entry_jumps_to_its_section(html)


@pytest.mark.parametrize("name", ["accounts:login", "accounts:signup", "packs:attribution"])
def test_signed_out_pages_have_it_too(client, name):
    _assert_each_entry_jumps_to_its_section(client.get(reverse(name)).content.decode())


def test_a_page_without_its_own_sections_gets_top_and_end(member_client):
    html = member_client.get(reverse("accounts:profile")).content.decode()
    assert _assert_each_entry_jumps_to_its_section(html) == [
        ("page-top", "Top"),
        ("page-footer", "End"),
    ]


def test_the_ruler_works_without_javascript_on_wide_screens_only(member_client, kit):
    for url in _every_page(kit):
        ruler = _ruler(member_client.get(url).content.decode())
        # Plain #anchors (never boosted, no htmx request), so the jump needs no script.
        assert 'hx-boost="false"' in ruler
        assert "hx-get" not in ruler and "hx-post" not in ruler
        assert all(href.startswith("#") for href in re.findall(r'href="([^"]*)"', ruler))
        # Hidden below 80 rem.
        assert 'class="scroll-ruler hidden xl:flex"' in ruler
        assert 'aria-label="Sections on this page"' in ruler


def test_the_ruler_is_a_monochrome_scale(member_client, kit):
    for url in _every_page(kit):
        ruler = _ruler(member_client.get(url).content.decode())
        assert not TYPE_TOKEN.search(ruler), url
        assert ruler.count('class="scroll-ruler-major"') == 11
        assert 'class="scroll-ruler-cursor"' in ruler


# ------------------------------------------------------------------ each page's index


def test_the_main_page_index_for_a_visitor(client):
    html = client.get(reverse("packs:home")).content.decode()
    assert _assert_each_entry_jumps_to_its_section(html) == [
        ("home-hero", "Toolbox"),
        ("home-steps", "How it works"),
        ("gallery", "Public packs"),
    ]


def test_a_member_has_no_how_it_works_entry(member_client):
    html = member_client.get(reverse("packs:home")).content.decode()
    assert [entry[0] for entry in _assert_each_entry_jumps_to_its_section(html)] == [
        "home-hero",
        "gallery",
    ]


@pytest.mark.parametrize(
    "kind, shelves",
    [
        ("texture", [("shelf-ambientcg", "ambientCG"), ("shelf-polyhaven", "Poly Haven")]),
        ("model", [("shelf-ambientcg", "ambientCG"), ("shelf-polyhaven", "Poly Haven")]),
        ("sound", [("shelf-openverse", "Openverse Audio")]),
    ],
)
def test_discovers_index_has_search_types_and_each_shelf(client, kind, shelves):
    html = client.get(reverse("catalog:discover"), {"type": kind, "q": "rock"}).content.decode()
    assert _assert_each_entry_jumps_to_its_section(html) == [
        ("discover-search", "Search"),
        ("type-tiles", "Types"),
        *shelves,
    ]


def test_the_builders_and_pack_pages_indexes(member_client, kit):
    pack, _entry = kit
    builder = member_client.get(reverse("packs:builder", args=[pack.pk])).content.decode()
    assert [label for _id, label in _assert_each_entry_jumps_to_its_section(builder)] == [
        "Pack",
        "Details",
        "Items",
        "Suggested",
        "Add from library",
    ]
    page = member_client.get(pack.get_public_url()).content.decode()
    assert [label for _id, label in _assert_each_entry_jumps_to_its_section(page)] == [
        "Pack",
        "Items",
        "Credits",
    ]


def test_an_empty_packs_page_lists_no_items_entry(member, member_client):
    pack = Pack.objects.create_pack(member, "Empty kit", "", "")
    page = member_client.get(pack.get_public_url()).content.decode()
    assert [label for _id, label in _assert_each_entry_jumps_to_its_section(page)] == [
        "Pack",
        "Credits",
    ]
    attribution = member_client.get(
        reverse("packs:attribution_pack", args=[pack.slug])
    ).content.decode()
    assert "Notice" not in [label for _id, label in _entries(_ruler(attribution))]


def test_a_visitor_on_a_public_pack_page_gets_its_index(kit):
    pack, _entry = kit
    html = Client().get(pack.get_public_url()).content.decode()
    _assert_each_entry_jumps_to_its_section(html)


def test_a_gallery_swap_has_no_ruler(client):
    response = client.get(reverse("packs:home"), headers={"HX-Request": "true"})
    assert 'id="gallery-results"' in response.content.decode()
    assert "scroll-ruler" not in response.content.decode()


# ------------------------------------------------------------------ script and styles


def test_the_script_loads_once_and_respects_reduced_motion(client):
    html = client.get(reverse("packs:home")).content.decode()
    assert html.count("js/scroll-ruler.js?v=") == 1
    script = (settings.BASE_DIR / "static" / "js" / "scroll-ruler.js").read_text(encoding="utf-8")
    assert "prefers-reduced-motion: reduce" in script
    assert 'behavior: reduce.matches ? "auto" : "smooth"' in script
    assert "data-scroll-ruler" in script and "htmx.onLoad" in script
    css = (settings.BASE_DIR / "styles" / "source.css").read_text(encoding="utf-8")
    reduced = css.split("@media (prefers-reduced-motion: reduce)")
    assert any(".scroll-ruler-label, .scroll-ruler-tick" in block for block in reduced[1:])


def test_entries_are_numbered_in_order_and_content_keeps_clear(client):
    css = (settings.BASE_DIR / "styles" / "source.css").read_text(encoding="utf-8")
    assert "counter-increment: ruler;" in css
    assert "content: counter(ruler, decimal-leading-zero);" in css
    assert "@media (min-width: 80rem) { .content-gutter { padding-right: 6rem; } }" in css
    html = client.get(reverse("packs:home")).content.decode()
    assert html.count("content-gutter") == 2  # the content and the footer
