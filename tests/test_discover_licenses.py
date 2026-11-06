"""Discover's license filters and license symbols (user request, 2026-11-06).

The side panel filters results by license and by whether commercial use is
allowed. ambientCG and Poly Haven are all CC0, so they're kept or dropped
without a request; Openverse is asked for the allowed licenses only. App tests
replace provider functions with `monkeypatch` (docs/TESTING.md); the Openverse
client's own parameter is tested with `responses`.
"""

import re
from urllib.parse import parse_qs, urlparse

import pytest
from django.http import QueryDict
from django.urls import reverse

from catalog.discover import (
    FILTER_LICENSES,
    DiscoverFilters,
    clean_filters,
    discover_url,
    load_shelf,
    search_cache_key,
    shelf_url,
    shuffle_url,
)
from providers import PROVIDERS, AssetRecord, ambientcg, openverse, polyhaven

pytestmark = pytest.mark.django_db

HTMX = {"HX-Request": "true"}


def record(provider="openverse", external_id="rain-1", kind="sound", **fields):
    values = {
        "title": "Rain",
        "author": "InspectorJ",
        "thumbnail_url": "",
        "license": "CC BY 4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "attribution": '"Rain" by InspectorJ, CC BY 4.0',
        "source_url": f"https://freesound.org/s/{external_id}",
    }
    values.update(fields)
    return AssetRecord(provider=provider, external_id=external_id, kind=kind, **values)


@pytest.fixture
def searches(monkeypatch):
    """Replace every provider's search_records; the list records each call's licenses."""
    calls = []

    def fake_for(provider):
        def fake(query, kind, limit=12, page=1, **kwargs):
            calls.append((provider.KEY, kwargs.get("licenses")))
            return [record(provider=provider.KEY, kind=kind)]

        return fake

    for provider in PROVIDERS:
        monkeypatch.setattr(provider, "search_records", fake_for(provider))
    return calls


def query(**params):
    data = QueryDict(mutable=True)
    for key, value in params.items():
        data.setlist(key, value if isinstance(value, list) else [value])
    return data


# ---------------------------------------------------------------- reading the filters


def test_clean_filters_keeps_known_licenses_in_the_guides_order():
    filters = clean_filters(query(license=["by-nc", "cc0", "nope", "unknown"], commercial="1"))
    assert filters == DiscoverFilters(licenses=("cc0", "by-nc"), commercial=True)
    assert clean_filters(query(commercial="yes")) == DiscoverFilters()
    assert not clean_filters(QueryDict()).active
    assert "unknown" not in FILTER_LICENSES


def test_commercial_use_allows_only_licenses_that_say_yes():
    assert DiscoverFilters(commercial=True).allowed == {"cc0", "pdm", "by", "by-sa", "by-nd"}
    # With licenses chosen too, it narrows them; a non-commercial choice drops out.
    assert DiscoverFilters(licenses=("cc0", "by-nc"), commercial=True).allowed == {"cc0"}
    assert DiscoverFilters(licenses=("by-nc",), commercial=True).allowed == frozenset()
    assert DiscoverFilters().allowed is None
    assert DiscoverFilters(licenses=("by",)).allows("CC BY 4.0")
    assert not DiscoverFilters(licenses=("by",)).allows("CC BY-NC 4.0")


def test_every_discover_link_keeps_the_filters():
    filters = DiscoverFilters(licenses=("cc0", "by"), commercial=True)
    for url in (
        discover_url("sound", "rain", filters),
        shelf_url("sound", "openverse", "rain", 2, filters),
        shuffle_url("sound", "rain", filters),
    ):
        params = parse_qs(urlparse(url).query)
        assert params["license"] == ["cc0", "by"] and params["commercial"] == ["1"], url
    assert "license" not in discover_url("sound", "rain")


# ---------------------------------------------------------------- loading shelves


def test_a_cc0_provider_is_searched_when_cc0_is_allowed(searches):
    shelf = load_shelf(polyhaven, "texture", "brick", filters=DiscoverFilters(commercial=True))
    assert shelf.records and not shelf.filtered_out
    # It isn't told about licenses: everything it has is CC0.
    assert searches == [("polyhaven", None)]


def test_a_cc0_provider_is_filtered_out_without_a_request(searches):
    shelf = load_shelf(ambientcg, "texture", "brick", filters=DiscoverFilters(licenses=("by",)))
    assert shelf.loaded and shelf.filtered_out and not shelf.records and not shelf.error
    assert searches == []


def test_openverse_is_asked_for_the_allowed_licenses_only(searches):
    load_shelf(openverse, "sound", "rain", filters=DiscoverFilters(commercial=True))
    assert searches == [("openverse", ("cc0", "pdm", "by", "by-sa", "by-nd"))]


def test_a_combination_no_license_meets_asks_nobody(searches):
    filters = DiscoverFilters(licenses=("by-nc",), commercial=True)
    assert load_shelf(openverse, "sound", "rain", filters=filters).filtered_out
    assert searches == []


def test_each_set_of_filters_is_cached_apart(searches):
    load_shelf(openverse, "sound", "rain")
    load_shelf(openverse, "sound", "rain", filters=DiscoverFilters(licenses=("cc0",)))
    load_shelf(openverse, "sound", "rain", filters=DiscoverFilters(licenses=("cc0",)))
    assert searches == [("openverse", None), ("openverse", ("cc0",))]
    assert search_cache_key("openverse", "sound", "rain") != search_cache_key(
        "openverse", "sound", "rain", licenses="cc0"
    )


def test_openverse_sends_the_licenses_as_one_parameter(mocked_responses):
    mocked_responses.get(openverse.API_URL, json={"results": []})
    openverse.search_records("rain", "sound", licenses=("cc0", "by"))
    sent = parse_qs(urlparse(mocked_responses.calls[0].request.url).query)
    assert sent["license"] == ["cc0,by"]


# ---------------------------------------------------------------- the page


def test_the_side_panel_has_commercial_use_and_license_chips(client):
    html = client.get(reverse("catalog:discover"), {"type": "sound"}).content.decode()
    panel = html.split('id="discover-filters"', 1)[1].split("</section>", 1)[0]
    # Like the library's filters: chips that belong to the command bar's form.
    assert 'form="discover-search"' in panel and "data-autosubmit" in panel
    assert re.search(r'name="commercial" value="1"', panel)
    for key in FILTER_LICENSES:
        assert f'name="license" value="{key}"' in panel
    # Each license chip carries its symbols.
    by_nc = re.search(
        r'<label class="filter-chip has-icons">(?:(?!</label>).)*value="by-nc"'
        r"(?:(?!</label>).)*</label>",
        panel,
        re.S,
    ).group(0)
    assert by_nc.count("<svg") == 2 and "CC BY-NC" in by_nc
    assert "Clear" not in panel  # nothing to clear yet


def test_chosen_filters_show_checked_and_ride_along_on_shelves_and_tiles(client):
    url = reverse("catalog:discover")
    html = client.get(f"{url}?type=sound&q=rain&license=by&commercial=1").content.decode()
    assert re.search(r'name="license" value="by" checked', html)
    assert re.search(r'name="commercial" value="1" checked', html)
    assert 'id="discover-filter-note"' in html and "CC BY, commercial use" in html
    shelf = re.search(r'id="shelf-openverse"[^>]*hx-get="([^"]+)"', html).group(1)
    assert "license=by" in shelf and "commercial=1" in shelf
    tiles = html.split('id="type-tiles"', 1)[1].split("</nav>", 1)[0]
    assert tiles.count("license=by&amp;commercial=1") == 4


def test_a_filtered_out_shelf_says_why_with_clear_filters(client, searches):
    url = reverse("catalog:discover_shelf", args=["texture", "polyhaven"])
    html = client.get(f"{url}?q=brick&license=by", headers=HTMX).content.decode()
    assert "Filtered out" in html
    assert "Every Poly Haven asset is CC0, which your filters leave out." in html
    assert 'href="/discover/?type=texture&amp;q=brick"' in html
    assert searches == []


def test_each_card_shows_its_license_as_symbols(client, monkeypatch):
    monkeypatch.setattr(
        openverse,
        "search_records",
        lambda query, kind, limit=12, page=1, **kw: [record(license="CC BY-NC-SA 3.0")],
    )
    url = reverse("catalog:discover_shelf", args=["sound", "openverse"])
    html = client.get(f"{url}?q=rain", headers=HTMX).content.decode()
    meta = re.search(r'<span class="result-license">.*?</span></span>', html, re.S).group(0)
    assert 'class="license-symbols is-small" role="img"' in meta
    assert 'aria-label="CC BY-NC-SA: Attribution, NonCommercial, ShareAlike"' in meta
    assert meta.count("<svg") == 3
    # The details say whether commercial use is allowed.
    assert "Commercial</dt><dd>Not usable. Non-commercial only.</dd>" in html
