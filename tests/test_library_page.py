"""The library page: its controls, its empty state and its card grid.

Phase 4 wires up search, filters and sorting. Until then (and whenever the
library is empty) the controls render disabled, in the places they'll live.
Phase 3's grid shows the member's own entries from the Toolbox's stored
Assets, with every provider down if need be.
"""

import re
from datetime import timedelta

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from providers import PROVIDERS, ProviderError

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


# ---------------------------------------------------------------- the grid (Phase 3)


@pytest.fixture
def entries(make_asset, member):
    """Three of the member's entries, saved oldest to newest, across three kinds."""
    from catalog.models import SavedAsset

    made = [
        SavedAsset.objects.create(
            user=member,
            asset=make_asset(external_id="red_brick_03", title="Red Brick 03"),
            saved_at=timezone.now() - timedelta(days=2),
        ),
        SavedAsset.objects.create(
            user=member,
            asset=make_asset(
                external_id="sunset_sky",
                kind="hdri",
                title="Sunset Sky",
                thumbnail_url="",
            ),
            rating=3,
            status=SavedAsset.Status.APPROVED,
            saved_at=timezone.now() - timedelta(days=1),
        ),
        SavedAsset.objects.create(
            user=member,
            asset=make_asset(
                provider="openverse",
                external_id="a8783d20",
                kind="sound",
                title="Footsteps",
                thumbnail_url="https://api.openverse.org/v1/audio/a8783d20/thumb/",
                source_url="https://freesound.org/s/345560/",
            ),
        ),
    ]
    return made


def _cards(html):
    return re.findall(r'<li class="result-card library-card" id="entry-\d+">.*?</li>', html, re.S)


def test_the_grid_shows_each_entry_newest_saved_first(entries, member_client):
    html = _content(member_client.get(reverse("catalog:library")).content.decode())
    assert "Your library is empty." not in html
    titles = [re.search(r'class="result-link">([^<]+)<', card).group(1) for card in _cards(html)]
    assert titles == ["Footsteps", "Sunset Sky", "Red Brick 03"]


def test_each_card_shows_thumbnail_type_title_status_and_rating(entries, member_client):
    html = _content(member_client.get(reverse("catalog:library")).content.decode())
    footsteps, sunset, brick = _cards(html)
    # Type: the singular label, beside its icon in the type colour.
    assert '<span class="micro">Texture</span>' in brick
    assert '<span class="library-type-icon text-texture"' in brick
    assert '<span class="micro">HDRI</span>' in sunset
    assert '<span class="micro">Sound</span>' in footsteps
    # Status and rating: a new entry is To review and unrated.
    assert 'data-status="to_review">To review</span>' in brick
    assert "Not rated" in brick
    assert 'data-status="approved">Approved</span>' in sunset
    assert 'role="img" aria-label="Rated 3 out of 5"' in sunset
    assert sunset.count('class="star is-on"') == 3
    assert sunset.count('class="star"') == 2
    # The title opens the provider's page.
    assert 'href="https://freesound.org/s/345560/" target="_blank"' in footsteps


def test_thumbnails_are_the_providers_urls_never_a_local_copy(entries, member_client):
    html = _content(member_client.get(reverse("catalog:library")).content.decode())
    srcs = re.findall(r'<img src="([^"]+)"[^>]*data-thumb-fallback>', html)
    assert srcs == [
        "https://api.openverse.org/v1/audio/a8783d20/thumb/",
        "https://cdn.polyhaven.com/thumbs/red_brick_03.png",
    ]
    assert 'referrerpolicy="no-referrer"' in html
    assert "/media/" not in html


def test_a_card_with_no_thumbnail_shows_its_type_icon(entries, member_client):
    html = _content(member_client.get(reverse("catalog:library")).content.decode())
    _, sunset, _ = _cards(html)
    thumb = sunset.split('<div class="result-thumb">', 1)[1].split("</div>", 1)[0]
    assert '<span class="result-fallback text-hdri" aria-hidden="true">' in thumb
    assert "<img" not in thumb
    assert "mark" not in thumb  # never the logo


def test_the_grid_renders_from_local_data_with_every_provider_down(
    entries, member_client, monkeypatch
):
    def down(*args, **kwargs):
        raise ProviderError("Every provider is down.")

    for provider in PROVIDERS:
        for name in ("search", "get_details", "search_records", "fetch_record"):
            monkeypatch.setattr(provider, name, down)
    response = member_client.get(reverse("catalog:library"))
    assert response.status_code == 200
    html = _content(response.content.decode())
    assert len(_cards(html)) == 3
    assert "Every provider is down." not in html


def test_a_member_sees_only_their_own_entries(entries, member_client, django_user_model, password):
    from catalog.models import SavedAsset

    other = django_user_model.objects.create_user("other_member", password=password)
    SavedAsset.objects.create(user=other, asset=entries[0].asset)
    theirs = Client()
    theirs.force_login(other)
    html = _content(theirs.get(reverse("catalog:library")).content.decode())
    assert len(_cards(html)) == 1
    assert "Sunset Sky" not in html and "Footsteps" not in html
    # And the member's own page never holds the other member's entry twice over.
    mine = _content(member_client.get(reverse("catalog:library")).content.decode())
    assert len(_cards(mine)) == 3


def test_controls_stay_disabled_until_phase_four(entries, member_client):
    html = member_client.get(reverse("catalog:library")).content.decode()
    toolbar = _content(html).split('id="library-toolbar"', 1)[1].split("</div>\n\n", 1)[0]
    assert 'aria-disabled="true"' in toolbar
    assert '<fieldset disabled class="' in html.split('id="library-filters"', 1)[1]
