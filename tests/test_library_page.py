"""The library page: its controls, its empty states, its card grid and its HTMX swaps.

The controls (search, sort, and the side panel's filter chips) render
disabled while the library is empty. The grid shows the member's own entries
from the Toolbox's stored Assets, with every provider down if need be.
Search, filters, sorts and pages go through filter_library()
(test_library_filter.py); these tests cover the page around it.
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


def _toolbar(html):
    return _content(html).split('id="library-toolbar"', 1)[1].split("</form>", 1)[0]


def test_toolbar_holds_search_and_sort_disabled_while_empty(library_html):
    toolbar = _toolbar(library_html)
    assert 'role="search" aria-label="Library controls"' in toolbar
    assert 'aria-disabled="true"' in toolbar
    assert re.search(
        r'<input type="search" id="library-search" name="q" value=""[^>]* disabled>', toolbar
    )
    # The PRD's four sorts, newest saved first (the default).
    sort = re.search(
        r'<select name="sort" class="library-control" disabled>(.*?)</select>', toolbar, re.S
    )
    assert re.findall(r'<option value="(\w+)"[^>]*>([^<]+)</option>', sort.group(1)) == [
        ("newest", "Newest saved"),
        ("oldest", "Oldest"),
        ("title", "Title A–Z"),
        ("rating", "Rating, high to low"),
    ]
    # The grid/list toggle is gone: the PRD describes only a card grid.
    assert "Grid view" not in library_html and "List view" not in library_html


def _chips(html):
    """{group title: [(label, input type, value, checked)]} from the side panel's filters."""
    filters = html.split('id="library-filters"', 1)[1].split("</section>", 1)[0]
    groups = re.findall(
        r'<div class="filter-group" role="group" aria-label="([^"]+)">(.*?)</div>\s*</div>',
        filters,
        re.S,
    )
    return {
        title: [
            (label, kind, value, bool(checked))
            for kind, value, checked, label in re.findall(
                r'<label class="filter-chip"><input type="(\w+)" class="library-control sr-only" '
                r'form="library-toolbar" name="\w+" value="([^"]*)"( checked)?><span>([^<]+)</span>',
                body,
            )
        ]
        for title, body in groups
    }


def test_filters_live_in_the_side_panel_disabled_while_empty(library_html):
    panel = library_html.split('id="side-panel"', 1)[1].split("</aside>", 1)[0]
    # The usual navigation rows stay on top.
    assert re.findall(r'<a class="panel-row"[^>]*>([^<]+)</a>', panel) == [
        "Discover",
        "Library",
        "Packs",
    ]
    assert '<fieldset disabled class="' in panel.split('id="library-filters"', 1)[1]
    chips = _chips(library_html)
    assert {title: [chip[0] for chip in group] for title, group in chips.items()} == {
        "Type": ["Textures", "HDRIs", "Models", "Sounds"],
        "Provider": ["ambientCG", "Poly Haven", "Openverse Audio"],
        "Status": ["To review", "Testing", "Approved", "Rejected"],
        "Minimum rating": ["Any", "1+", "2+", "3+", "4+", "5"],
    }
    # Type, provider and status are checkboxes; minimum rating is one radio choice, Any by default.
    assert {chip[1] for title in ("Type", "Provider", "Status") for chip in chips[title]} == {
        "checkbox"
    }
    assert [(chip[1], chip[2], chip[3]) for chip in chips["Minimum rating"]] == [
        ("radio", "", True),
        ("radio", "1", False),
        ("radio", "2", False),
        ("radio", "3", False),
        ("radio", "4", False),
        ("radio", "5", False),
    ]


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


def test_controls_switch_on_once_the_library_has_entries(entries, member_client):
    html = member_client.get(reverse("catalog:library")).content.decode()
    toolbar = _toolbar(html)
    assert "aria-disabled" not in toolbar and " disabled" not in toolbar
    assert '<fieldset class="' in html.split('id="library-filters"', 1)[1]


# ---------------------------------------------------------------- browsing (Phase 4)

HTMX = {"HX-Request": "true", "HX-Target": "library-results"}


@pytest.fixture
def many(make_asset, member):
    """14 of the member's textures and 1 HDRI: two pages, newest saved first."""
    from catalog.models import SavedAsset

    for n in range(14):
        SavedAsset.objects.create(
            user=member,
            asset=make_asset(external_id=f"brick_{n:02}", title=f"Brick {n:02}"),
            status=SavedAsset.Status.APPROVED if n % 2 else SavedAsset.Status.TO_REVIEW,
            rating=(n % 5) + 1,
            saved_at=timezone.now() - timedelta(days=n),
        )
    SavedAsset.objects.create(
        user=member,
        asset=make_asset(external_id="sky", kind="hdri", title="Sky"),
        saved_at=timezone.now() - timedelta(days=30),
    )


def _titles(html):
    return [re.search(r'class="result-link">([^<]+)<', card).group(1) for card in _cards(html)]


def test_an_htmx_request_returns_only_the_results_fragment(many, member_client):
    response = member_client.get(reverse("catalog:library") + "?q=brick", headers=HTMX)
    html = response.content.decode()
    assert response.status_code == 200
    assert html.strip().startswith('<div id="library-results"')
    assert "<html" not in html and 'id="side-panel"' not in html
    assert 'id="library-toolbar"' not in html
    assert len(_cards(html)) == 12


def test_a_normal_request_for_the_same_query_string_is_the_full_page_in_the_same_state(
    many, member_client
):
    query = "?q=brick&type=texture&status=approved&min_rating=2&sort=title&page=1"
    fragment = member_client.get(reverse("catalog:library") + query, headers=HTMX)
    page = member_client.get(reverse("catalog:library") + query)
    html = page.content.decode()
    assert "<html" in html
    # The same cards, in the same order.
    assert _titles(html) == _titles(fragment.content.decode())
    assert _titles(html) == ["Brick 01", "Brick 03", "Brick 07", "Brick 09", "Brick 11", "Brick 13"]
    # And the controls show the state the URL asked for.
    toolbar = _toolbar(html)
    assert 'name="q" value="brick"' in toolbar
    assert '<option value="title" selected>' in toolbar
    checked = {
        title: [chip[0] for chip in group if chip[3]] for title, group in _chips(html).items()
    }
    assert checked == {
        "Type": ["Textures"],
        "Provider": [],
        "Status": ["Approved"],
        "Minimum rating": ["2+"],
    }


@pytest.mark.parametrize(
    "headers",
    [
        {"HX-Request": "true", "HX-Boosted": "true"},  # a boosted link to the library
        {"HX-Request": "true", "HX-History-Restore-Request": "true"},  # Back after a swap
    ],
)
def test_boosted_and_history_restore_requests_get_the_full_page(many, member_client, headers):
    response = member_client.get(reverse("catalog:library") + "?q=brick&page=2", headers=headers)
    html = response.content.decode()
    assert "<html" in html and 'id="library-toolbar"' in html
    assert "HX-Push-Url" not in response.headers
    assert _titles(html) == ["Brick 12", "Brick 13"]


def test_the_pushed_url_holds_the_search_filters_sort_and_page(many, member_client):
    # As the toolbar's form sends it: every field, blanks and defaults included.
    query = (
        "?q=+brick+&sort=rating&type=texture&status=approved&status=to_review"
        "&provider=polyhaven&min_rating=&page=2"
    )
    response = member_client.get(reverse("catalog:library") + query, headers=HTMX)
    assert response["HX-Push-Url"] == (
        "/library/?q=brick&type=texture&provider=polyhaven&status=to_review&status=approved"
        "&sort=rating&page=2"
    )
    # Defaults and junk are left out, so the plain library is plain /library/.
    plain = member_client.get(
        reverse("catalog:library") + "?q=&sort=newest&min_rating=&type=planet", headers=HTMX
    )
    assert plain["HX-Push-Url"] == "/library/"


def test_the_toolbar_and_filters_swap_only_the_results_and_push_the_url(many, member_client):
    html = member_client.get(reverse("catalog:library")).content.decode()
    form = re.search(r'<form id="library-toolbar"[^>]*>', html, re.S).group(0)
    assert 'hx-get="/library/"' in form
    assert 'hx-target="#library-results"' in form and 'hx-swap="outerHTML"' in form
    assert 'hx-push-url="true"' in form
    # Typing searches after a pause; a chip or the sort select applies at once.
    assert "input changed delay:300ms from:#library-search" in form
    assert "change from:.library-control" in form
    # Every side-panel chip belongs to that form.
    filters = html.split('id="library-filters"', 1)[1].split("</section>", 1)[0]
    assert filters.count('form="library-toolbar"') == filters.count("<input") == 17


def test_the_pager_links_to_each_page_with_the_same_view(many, member_client):
    first = member_client.get(reverse("catalog:library") + "?sort=oldest").content.decode()
    assert "1–12 of 15 entries" in first
    pager = first.split('id="library-pager"', 1)[1].split("</nav>", 1)[0]
    assert "Page 1 of 2" in pager
    assert (
        '<span class="btn btn-quiet btn-sm btn-disabled" aria-disabled="true">Previous</span>'
        in pager
    )
    next_link = re.search(
        r'<a href="([^"]+)" hx-get="\1" hx-target="#library-results"[^>]*hx-push-url="true" rel="next"',
        pager,
    )
    assert next_link.group(1) == "/library/?sort=oldest&amp;page=2"

    second = member_client.get("/library/?sort=oldest&page=2", headers=HTMX).content.decode()
    assert "13–15 of 15 entries" in second
    assert _titles(second) == ["Brick 02", "Brick 01", "Brick 00"]
    pager = second.split('id="library-pager"', 1)[1].split("</nav>", 1)[0]
    assert re.search(r'<a href="/library/\?sort=oldest" [^>]*rel="prev"', pager)
    assert "Next</span>" in pager


def test_one_page_has_no_pager(entries, member_client):
    html = member_client.get(reverse("catalog:library")).content.decode()
    assert "1–3 of 3 entries" in html
    assert 'id="library-pager"' not in html


def test_an_empty_library_links_to_discover(member_client):
    for headers in ({}, HTMX):
        html = member_client.get(reverse("catalog:library") + "?q=brick", headers=headers)
        results = html.content.decode().split('id="library-results"', 1)[1]
        assert "Your library is empty." in results
        assert (
            '<a href="/discover/" class="btn btn-quiet btn-sm mt-5">Go to Discover</a>' in results
        )


def test_no_matches_offers_to_clear_the_search_and_filters(entries, member_client):
    searched = member_client.get("/library/?q=granite", headers=HTMX).content.decode()
    assert "Nothing in your library matches “granite”." in searched
    assert '<a href="/library/" class="btn btn-quiet btn-sm mt-5">Clear filters</a>' in searched
    assert "Your library is empty." not in searched

    filtered = member_client.get("/library/?type=model&min_rating=5").content.decode()
    results = filtered.split('id="library-results"', 1)[1]
    assert "Nothing in your library matches these filters." in results
    assert '<a href="/library/" class="btn btn-quiet btn-sm mt-5">Clear filters</a>' in results
    # The controls stay on, so the member can loosen the filters instead.
    assert '<fieldset class="' in filtered.split('id="library-filters"', 1)[1]


def test_a_search_is_shown_escaped(entries, member_client):
    html = member_client.get("/library/?q=<script>x</script>").content.decode()
    assert "<script>x</script>" not in html
    assert "&lt;script&gt;x&lt;/script&gt;" in html
