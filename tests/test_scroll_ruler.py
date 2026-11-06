"""The right-edge scroll ruler with its section index (Phase 12), on the main page
and Discover: plain anchors to sections that exist on the page, wide screens
only, monochrome, and nowhere else.

App tests: Discover's page never calls a provider (its shelves load later).
"""

import re

import pytest
from django.conf import settings
from django.urls import reverse

pytestmark = pytest.mark.django_db

TYPE_TOKEN = re.compile(r"\b[\w:-]*-(?:texture|hdri|model|sound)\b")


def _ruler(html):
    match = re.search(r'<nav id="scroll-ruler".*?</nav>', html, re.S)
    assert match, "no scroll ruler"
    return match.group(0)


def _entries(ruler):
    return re.findall(
        r'<a href="#([\w-]+)" class="scroll-ruler-link" data-ruler-target="\1">'
        r'<span class="scroll-ruler-label">([^<]+)</span><span class="scroll-ruler-number">(\d\d)</span>',
        ruler,
    )


def _assert_each_entry_jumps_to_its_section(html, ruler):
    for section_id, _label, _number in _entries(ruler):
        assert html.count(f'id="{section_id}"') == 1, f"#{section_id} isn't on the page once"


def test_the_main_page_index_for_a_visitor(client):
    html = client.get(reverse("packs:home")).content.decode()
    ruler = _ruler(html)
    assert _entries(ruler) == [
        ("home-hero", "Toolbox", "01"),
        ("home-steps", "How it works", "02"),
        ("gallery", "Public packs", "03"),
    ]
    _assert_each_entry_jumps_to_its_section(html, ruler)


def test_a_member_has_no_how_it_works_entry(member_client):
    html = member_client.get(reverse("packs:home")).content.decode()
    ruler = _ruler(html)
    assert [entry[0] for entry in _entries(ruler)] == ["home-hero", "gallery"]
    assert 'id="home-steps"' not in html
    _assert_each_entry_jumps_to_its_section(html, ruler)


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
    ruler = _ruler(html)
    entries = [(section_id, label) for section_id, label, _number in _entries(ruler)]
    assert entries == [("discover-search", "Search"), ("type-tiles", "Types"), *shelves]
    _assert_each_entry_jumps_to_its_section(html, ruler)


@pytest.mark.parametrize("name", ["packs:home", "catalog:discover"])
def test_the_ruler_works_without_javascript_on_wide_screens_only(client, name):
    ruler = _ruler(client.get(reverse(name)).content.decode())
    # Plain #anchors (never boosted, no htmx request), so the jump needs no script.
    assert 'hx-boost="false"' in ruler
    assert "hx-get" not in ruler and "hx-post" not in ruler
    assert all(href.startswith("#") for href in re.findall(r'href="([^"]*)"', ruler))
    # Hidden below 80 rem.
    assert 'class="scroll-ruler hidden xl:flex"' in ruler
    assert 'aria-label="Sections on this page"' in ruler


@pytest.mark.parametrize("name", ["packs:home", "catalog:discover"])
def test_the_ruler_is_monochrome(client, name):
    ruler = _ruler(client.get(reverse(name)).content.decode())
    assert not TYPE_TOKEN.search(ruler)


@pytest.mark.parametrize(
    "name", ["catalog:library", "packs:list", "packs:attribution", "accounts:settings"]
)
def test_no_other_page_has_a_ruler(member_client, name):
    assert 'id="scroll-ruler"' not in member_client.get(reverse(name)).content.decode()


def test_a_gallery_swap_has_no_ruler(client):
    response = client.get(reverse("packs:home"), headers={"HX-Request": "true"})
    assert 'id="gallery-results"' in response.content.decode()
    assert "scroll-ruler" not in response.content.decode()


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
