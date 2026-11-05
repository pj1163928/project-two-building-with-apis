"""Discover: the page, its type tiles and command bar, and the provider shelves.

App tests: provider functions are replaced with `monkeypatch`, never faked at
the HTTP level (see docs/TESTING.md).
"""

import re

import pytest
from django.conf import settings
from django.urls import reverse
from django.utils.html import escape

from providers import PROVIDERS, AssetRecord, ProviderError, ambientcg, openverse, polyhaven

pytestmark = pytest.mark.django_db

HTMX = {"HX-Request": "true"}


def record(provider="polyhaven", external_id="red_brick_03", kind="texture", **fields):
    values = {
        "title": "Red Brick 03",
        "author": "Rob Tuytel",
        "thumbnail_url": f"https://cdn.example/{external_id}.png",
        "license": "CC0",
        "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        "attribution": "Red Brick 03 by Rob Tuytel",
        "source_url": f"https://polyhaven.com/a/{external_id}",
        "tags": ("brick",),
    }
    values.update(fields)
    return AssetRecord(provider=provider, external_id=external_id, kind=kind, **values)


@pytest.fixture
def provider_calls(monkeypatch):
    """Replace every provider's search_records; the list records each call."""
    calls = []

    def fake_for(provider):
        def fake(query, kind, limit=12):
            calls.append((provider.KEY, kind, query))
            return []

        return fake

    for provider in PROVIDERS:
        monkeypatch.setattr(provider, "search_records", fake_for(provider))
    return calls


def shelf_url(kind, provider, query):
    return f"{reverse('catalog:discover_shelf', args=[kind, provider])}?q={query}"


# ---------------------------------------------------------------- shelf URL validation


@pytest.mark.parametrize("as_htmx", [True, False], ids=["htmx", "direct"])
@pytest.mark.parametrize(
    ("kind", "provider", "query", "status"),
    [
        ("textures", "ambientcg", "brick", 404),  # unknown kind
        ("texture", "freesound", "brick", 404),  # unknown provider
        ("texture", "openverse", "brick", 404),  # Openverse has no textures
        ("sound", "polyhaven", "brick", 404),  # Poly Haven has no sounds
        ("texture", "ambientcg", "", 400),  # blank query
        ("texture", "ambientcg", "%20%20", 400),  # whitespace-only query
    ],
)
def test_a_bad_shelf_url_is_refused_before_any_provider_is_called(
    client, provider_calls, kind, provider, query, status, as_htmx
):
    headers = HTMX if as_htmx else {}
    response = client.get(shelf_url(kind, provider, query), headers=headers)
    # Validation comes before the HTMX check: a bad URL is never redirected.
    assert response.status_code == status
    assert provider_calls == []


# ---------------------------------------------------------------- mixed shelves

# Markup and quote characters prove the message is rendered as escaped text.
FAILURE = 'ambientCG said <b onclick="x()">busy</b> & "try later".'


def test_a_failed_shelf_never_affects_the_other_shelf(client, monkeypatch):
    def failing(query, kind, limit=12):
        raise ProviderError(FAILURE)

    monkeypatch.setattr(ambientcg, "search_records", failing)
    monkeypatch.setattr(polyhaven, "search_records", lambda query, kind, limit=12: [record()])
    failed_url = shelf_url("texture", "ambientcg", "brick")
    working_url = shelf_url("texture", "polyhaven", "brick")

    def fetch(url):
        response = client.get(url, headers=HTMX)
        assert response.status_code == 200
        return response.content.decode()

    # Fetched in both orders: neither request changes what the other returns.
    failed, working = fetch(failed_url), fetch(working_url)
    assert (fetch(working_url), fetch(failed_url)) == (working, failed)

    # The failed shelf: its own section, a DaisyUI alert with the message, and
    # a Retry button that re-requests this shelf's URL into this shelf only.
    assert re.match(r'\s*<section id="shelf-ambientcg"', failed)
    alert = re.search(
        r'<div role="alert" class="alert alert-error[^"]*"[^>]*>(.*?)</div>\s*</section>',
        failed,
        re.S,
    )
    assert alert, failed
    # The message shows as text: escaped inside the alert, never raw markup.
    assert escape(FAILURE) in alert.group(1)
    assert FAILURE not in failed
    assert '<b onclick="x()">' not in failed
    # Retry is searched for inside the alert's own markup, so it must sit there.
    retry = re.search(r"<button [^>]*>\s*Retry\s*</button>", alert.group(1))
    assert retry, alert.group(1)
    assert f'hx-get="{failed_url}"' in retry.group(0)
    assert 'hx-target="#shelf-ambientcg"' in retry.group(0)
    assert 'hx-swap="outerHTML"' in retry.group(0)
    assert "Red Brick 03" not in failed

    # The working shelf: its own section and its results, with no alert or Retry.
    assert re.match(r'\s*<section id="shelf-polyhaven"', working)
    assert "Red Brick 03" in working
    assert 'role="alert"' not in working
    assert "Retry" not in working
    assert FAILURE not in working and escape(FAILURE) not in working


# ---------------------------------------------------------------- the Discover page

PRD_SHELVES = {
    "texture": ["ambientcg", "polyhaven"],
    "hdri": ["ambientcg", "polyhaven"],
    "model": ["ambientcg", "polyhaven"],
    "sound": ["openverse"],
}


def discover(client, **params):
    return client.get(reverse("catalog:discover"), params).content.decode()


def pending_shelves(html):
    """(id, hx-get) for every shelf that still has to fetch itself."""
    return re.findall(
        r'<section id="(shelf-\w+)"[^>]*aria-busy="true" hx-get="([^"]+)" hx-trigger="load"',
        html,
    )


@pytest.mark.parametrize("kind", PRD_SHELVES)
def test_each_kind_shows_one_pending_shelf_per_prd_provider(client, provider_calls, kind):
    html = discover(client, type=kind, q="brick")
    assert pending_shelves(html) == [
        (f"shelf-{key}", shelf_url(kind, key, "brick")) for key in PRD_SHELVES[kind]
    ]
    # The page renders without waiting for any provider: shelves load later.
    assert provider_calls == []


def test_the_home_search_lands_in_the_command_bar(client, provider_calls):
    html = discover(client, q="  mossy   rock ")
    form = re.search(r'<form id="discover-search"[^>]*>(.*?)</form>', html, re.S).group(1)
    assert 'name="q" value="mossy rock"' in form
    assert '<input type="hidden" name="type" value="texture">' in form
    assert pending_shelves(html)[0][1] == "/discover/texture/ambientcg/?q=mossy+rock"


def test_an_unknown_type_on_the_page_falls_back_to_textures(client, provider_calls):
    html = discover(client, type="sprites", q="brick")
    assert [shelf for shelf, _ in pending_shelves(html)] == ["shelf-ambientcg", "shelf-polyhaven"]


def test_without_a_query_the_page_asks_for_one_and_loads_no_shelves(client, provider_calls):
    html = discover(client, type="sound")
    assert pending_shelves(html) == []
    assert "Search to fill the shelves." in html
    assert "Sounds come from Openverse Audio." in html


def test_the_query_is_escaped_in_the_command_bar(client, provider_calls):
    html = discover(client, q='"><script>alert(1)</script>')
    assert "<script>alert(1)" not in html
    assert 'value="&quot;&gt;&lt;script&gt;alert(1)&lt;/script&gt;"' in html


def test_type_tiles_switch_kind_and_keep_the_query(client, provider_calls):
    html = discover(client, type="hdri", q="sky")
    tiles = html.split('id="type-tiles"', 1)[1].split("</nav>", 1)[0]
    links = re.findall(r'<a href="([^"]+)" class="type-tile"( aria-current="true")?>', tiles)
    assert [href for href, _ in links] == [
        f"/discover/?type={kind}&amp;q=sky" for kind in ("texture", "hdri", "model", "sound")
    ]
    assert [bool(current) for _, current in links] == [False, True, False, False]
    labels = re.findall(r'<span class="type-tile-label">([^<]+)</span>', tiles)
    assert labels == ["Textures", "HDRIs", "Models", "Sounds"]


def test_slash_focuses_the_search_unless_typing_in_a_text_field(client, provider_calls):
    html = discover(client)
    assert re.search(r'<input id="discover-search-input"[^>]*data-search-shortcut>', html)
    assert '<kbd class="command-key" title="Press / to search">/</kbd>' in html
    shell_js = (settings.BASE_DIR / "static" / "js" / "shell.js").read_text(encoding="utf-8")
    assert 'event.key !== "/"' in shell_js
    assert "inTextField(event.target)" in shell_js
    assert "/^(INPUT|TEXTAREA|SELECT)$/" in shell_js and "isContentEditable" in shell_js
    assert 'document.querySelector("[data-search-shortcut]")' in shell_js
    assert "event.preventDefault();" in shell_js


# ---------------------------------------------------------------- loaded shelves


def fetch_shelf(client, kind, provider, query="brick"):
    response = client.get(shelf_url(kind, provider, query), headers=HTMX)
    assert response.status_code == 200
    return response.content.decode()


def cards(html):
    return re.findall(
        r'<a href="[^"]+" target="_blank"[^>]*class="result-card">.*?</a>', html, re.S
    )


def test_a_normal_shelf_shows_thumbnail_title_author_and_license(client, monkeypatch):
    found = [
        record(external_id="red_brick_03"),
        record(external_id="sky_01", title="Sky 01", author="Greg Zaal"),
    ]
    monkeypatch.setattr(polyhaven, "search_records", lambda query, kind, limit=12: found)
    html = fetch_shelf(client, "texture", "polyhaven")
    assert "2 results" in html
    first, second = cards(html)
    assert 'href="https://polyhaven.com/a/red_brick_03"' in first
    assert '<img src="https://cdn.example/red_brick_03.png" alt="" loading="lazy"' in first
    assert '<h3 class="result-title">Red Brick 03</h3>' in first
    assert "Rob Tuytel" in first and ">CC0<" in first
    assert "Sky 01" in second and "Greg Zaal" in second
    # The logo is never placed on a provider thumbnail.
    assert 'class="mark' not in first


def test_a_shelf_shows_at_most_12_and_uneven_counts_as_returned(client, monkeypatch):
    many = [record(external_id=f"brick_{n:02}") for n in range(15)]
    monkeypatch.setattr(polyhaven, "search_records", lambda query, kind, limit=12: many[:limit])
    monkeypatch.setattr(ambientcg, "search_records", lambda query, kind, limit=12: many[:1])
    assert len(cards(fetch_shelf(client, "model", "polyhaven"))) == 12
    one = fetch_shelf(client, "model", "ambientcg")
    assert len(cards(one)) == 1 and "1 result<" in one


def test_a_result_without_a_thumbnail_shows_no_broken_image(client, monkeypatch):
    found = [record(provider="openverse", kind="sound", thumbnail_url="")]
    monkeypatch.setattr(openverse, "search_records", lambda query, kind, limit=12: found)
    [card] = cards(fetch_shelf(client, "sound", "openverse"))
    assert "<img" not in card


def test_an_empty_shelf_says_no_matches_and_is_not_an_error(client, monkeypatch):
    # Poly Haven's keywordMatches == 0 comes back from search_records as []
    # (tested at the HTTP level in test_provider_records.py).
    monkeypatch.setattr(polyhaven, "search_records", lambda query, kind, limit=12: [])
    html = fetch_shelf(client, "texture", "polyhaven", query="zzqqxx")
    assert 'No Poly Haven matches for <span class="font-mono">“zzqqxx”</span>.' in html
    assert "Try a different or broader phrase." in html
    assert 'role="alert"' not in html and "Retry" not in html


def test_an_error_shelf_shows_the_provider_message_unchanged(client, monkeypatch):
    message = "Openverse Audio did not respond within 10 seconds. Try again in a moment."

    def failing(query, kind, limit=12):
        raise ProviderError(message)

    monkeypatch.setattr(openverse, "search_records", failing)
    html = fetch_shelf(client, "sound", "openverse", query="rain")
    assert "Openverse Audio is unavailable" in html
    assert f'<p class="text-sm text-fg-secondary mt-0.5">{message}</p>' in html


def test_the_shelf_searches_the_cleaned_query_for_its_kind(client, provider_calls):
    fetch_shelf(client, "hdri", "polyhaven", query="%20%20Sunny%20%20%20sky%20")
    assert provider_calls == [("polyhaven", "hdri", "Sunny sky")]


def test_a_long_query_is_cut_to_100_characters(client, provider_calls):
    fetch_shelf(client, "texture", "ambientcg", query="a" * 150)
    assert provider_calls == [("ambientcg", "texture", "a" * 100)]


@pytest.mark.parametrize(
    "headers", [{}, {"HX-Request": "true", "HX-Boosted": "true"}], ids=["direct", "boosted"]
)
def test_a_valid_shelf_opened_directly_goes_to_its_discover_page(client, provider_calls, headers):
    response = client.get(shelf_url("sound", "openverse", "rain storm"), headers=headers)
    assert response.status_code == 302
    assert response.url == "/discover/?type=sound&q=rain+storm"
    assert provider_calls == []


def test_retry_fetches_the_shelf_again(client, monkeypatch):
    answers = iter([ProviderError("Could not connect to Poly Haven."), [record()]])

    def flaky(query, kind, limit=12):
        answer = next(answers)
        if isinstance(answer, Exception):
            raise answer
        return answer

    monkeypatch.setattr(polyhaven, "search_records", flaky)
    failed = fetch_shelf(client, "texture", "polyhaven")
    retry_url = re.search(r'<button [^>]*hx-get="([^"]+)"[^>]*>Retry</button>', failed).group(1)
    recovered = client.get(retry_url, headers=HTMX).content.decode()
    assert "Red Brick 03" in recovered and 'role="alert"' not in recovered
