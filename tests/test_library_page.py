"""The library page lays out its controls before there's anything to control.

Phase 4 wires up search, filters and sorting. Until then (and whenever the
library is empty) the controls render disabled, in the places they'll live.
"""

import re

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


@pytest.fixture
def library_html(member_client):
    return member_client.get(reverse("catalog:library")).content.decode()


def _content(html):
    return html.split('id="content"', 1)[1].split('id="page-footer"', 1)[0]


def test_toolbar_sits_between_the_header_and_the_results(library_html):
    content = _content(library_html)
    header = content.index('class="page-hero')
    toolbar = content.index('id="library-toolbar"')
    results = content.index('id="library-results"')
    assert header < toolbar < results
    assert "Your library is empty." in content[results:]


def test_toolbar_holds_search_sort_and_view_controls_all_disabled(library_html):
    toolbar = _content(library_html).split('id="library-toolbar"', 1)[1].split("</div>\n\n", 1)[0]
    assert 'role="toolbar" aria-label="Library controls" aria-disabled="true"' in toolbar
    assert re.search(r'<input type="search" name="q" placeholder="[^"]+" disabled>', toolbar)
    # The PRD's four sorts, newest saved first (the default).
    sort = re.search(r'<select name="sort" disabled>(.*?)</select>', toolbar, re.S).group(1)
    assert re.findall(r"<option>([^<]+)</option>", sort) == [
        "Newest saved",
        "Oldest",
        "Title A–Z",
        "Rating, high to low",
    ]
    views = re.findall(
        r'<button type="button" disabled aria-pressed="(\w+)" aria-label="([^"]+)"', toolbar
    )
    assert views == [("true", "Grid view"), ("false", "List view")]


def test_filters_live_in_the_side_panel_disabled(library_html):
    panel = library_html.split('id="side-panel"', 1)[1].split("</aside>", 1)[0]
    # The usual navigation rows stay on top.
    assert re.findall(r'<a class="panel-row"[^>]*>([^<]+)</a>', panel) == [
        "Discover",
        "Library",
        "Packs",
    ]
    filters = panel.split('id="library-filters"', 1)[1]
    assert '<fieldset disabled class="' in filters
    groups = dict(
        re.findall(
            r'<div class="filter-group"><p class="micro text-fg-muted">([^<]+)</p>\s*<div[^>]*>(.*?)</div>',
            filters,
            re.S,
        )
    )
    chips = {
        name: re.findall(r'class="filter-chip">([^<]+)<', body) for name, body in groups.items()
    }
    assert chips == {
        "Type": ["Textures", "HDRIs", "Models", "Sounds"],
        "Provider": ["ambientCG", "Poly Haven", "Openverse"],
        "Status": ["To review", "Testing", "Approved", "Rejected"],
        "Minimum rating": ["Any", "1+", "2+", "3+", "4+", "5"],
    }


def test_other_pages_keep_the_plain_side_panel(member_client):
    html = member_client.get(reverse("packs:list")).content.decode()
    assert 'id="library-filters"' not in html


@pytest.mark.parametrize("name", ["catalog:library", "packs:list"])
def test_header_and_content_sit_close_together(member_client, name):
    content = _content(member_client.get(reverse(name)).content.decode())
    section = re.search(r'<section class="([^"]*)">\s*<div class="page-hero', content)
    assert section and section.group(1) == "space-y-5"


def test_empty_state_is_a_solid_bordered_surface(library_html):
    empty = re.search(r'<div class="empty-state ([^"]*)"', library_html).group(1).split()
    assert {"bg-surface", "border", "border-line-strong", "py-16"} <= set(empty)
    assert "border-dashed" not in empty
