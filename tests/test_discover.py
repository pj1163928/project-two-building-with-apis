"""Discover: the page, its type tiles and command bar, and the provider shelves.

App tests: provider functions are replaced with `monkeypatch`, never faked at
the HTTP level (see docs/TESTING.md).
"""

import re
from urllib.parse import parse_qs, urlparse

import pytest
from django.conf import settings
from django.core.cache import cache
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import escape

from catalog import discover as discover_module
from providers import (
    PROVIDERS,
    PROVIDERS_BY_KEY,
    AssetRecord,
    ProviderError,
    ambientcg,
    openverse,
    polyhaven,
)

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
        def fake(query, kind, limit=12, page=1):
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

# The ProviderError message each failure gives (story 83), as get_json() words
# it, with {name} for the provider. test_provider_failures.py proves each one
# at the HTTP level; here they're raised directly. "markup" holds markup and
# quote characters, to prove a message is rendered as escaped text.
FAILURES = {
    "timeout": "{name} did not respond within 10 seconds. Try again in a moment.",
    "connection": "Could not connect to {name}. Check your internet connection.",
    "rate_limit": (
        "{name} is rate-limiting requests (HTTP 429). The server asked to wait 30 seconds. "
        "Openverse allows anonymous clients 20 requests per minute and 200 per day, "
        "so wait a minute and try again."
    ),
    "server_error": "{name} had a server error (HTTP 500). Try again later.",
    "not_found": (
        "{name} has nothing at that address (HTTP 404). "
        "If you entered an asset ID, check it and try again."
    ),
    "markup": '{name} said <b onclick="x()">busy</b> & "try later".',
}
SHELF_PAIRS = [("ambientcg", "polyhaven"), ("polyhaven", "ambientcg")]


def raising(message):
    def fake(query, kind, limit=12, page=1):
        raise ProviderError(message)

    return fake


@pytest.mark.parametrize(("failing", "working"), SHELF_PAIRS, ids=["acg-fails", "ph-fails"])
@pytest.mark.parametrize("failure", FAILURES)
def test_a_failed_shelf_never_affects_the_other_shelf(
    client, monkeypatch, failure, failing, working
):
    failing_provider, working_provider = PROVIDERS_BY_KEY[failing], PROVIDERS_BY_KEY[working]
    message = FAILURES[failure].format(name=failing_provider.NAME)
    monkeypatch.setattr(failing_provider, "search_records", raising(message))
    monkeypatch.setattr(
        working_provider, "search_records", lambda query, kind, limit=12, page=1: [record()]
    )
    failed_url = shelf_url("texture", failing, "brick")
    working_url = shelf_url("texture", working, "brick")

    def fetch(url):
        response = client.get(url, headers=HTMX)
        assert response.status_code == 200
        return response.content.decode()

    # Fetched in both orders: neither request changes what the other returns.
    failed, worked = fetch(failed_url), fetch(working_url)
    assert (fetch(working_url), fetch(failed_url)) == (worked, failed)

    # The failed shelf: its own section, a DaisyUI alert with the message, and
    # a Retry button that re-requests this shelf's URL into this shelf only.
    assert re.match(rf'\s*<section id="shelf-{failing}"', failed)
    alert = re.search(
        r'<div role="alert" class="alert alert-error[^"]*"[^>]*>(.*?)</div>\s*<p class="shelf-credit"',
        failed,
        re.S,
    )
    assert alert, failed
    # The message shows unchanged, as text: escaped inside the alert, never raw markup.
    assert escape(message) in alert.group(1)
    assert '<b onclick="x()">' not in failed
    # Retry is searched for inside the alert's own markup, so it must sit there.
    retry = re.search(r"<button [^>]*>\s*Retry\s*</button>", alert.group(1))
    assert retry, alert.group(1)
    assert f'hx-get="{failed_url}"' in retry.group(0)
    assert f'hx-target="#shelf-{failing}"' in retry.group(0)
    assert 'hx-swap="outerHTML"' in retry.group(0)
    assert "Red Brick 03" not in failed

    # The working shelf: its own section and its results, with no alert or Retry.
    assert re.match(rf'\s*<section id="shelf-{working}"', worked)
    assert "Red Brick 03" in worked
    assert 'role="alert"' not in worked
    assert "Retry" not in worked
    assert escape(message) not in worked


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


def test_without_a_query_the_shelves_show_a_random_pick(client, provider_calls, monkeypatch):
    monkeypatch.setattr(discover_module.random, "choice", lambda choices: choices[-1])
    html = discover(client, type="sound")
    # The pick fills the shelves, but not the command bar: nobody typed it.
    assert pending_shelves(html) == [("shelf-openverse", shelf_url("sound", "openverse", "fire"))]
    assert 'name="q" value=""' in html
    pick = re.search(r'<div id="featured-pick"[^>]*>(.*?)</div>', html, re.S).group(1)
    assert "Random pick" in pick and 'Sounds for <span class="font-mono">“fire”</span>' in pick
    assert "Sounds come from Openverse Audio." in pick
    # The page still waits for no provider.
    assert provider_calls == []


def test_every_random_pick_is_one_of_the_kinds_featured_searches(client, provider_calls):
    for kind, choices in discover_module.FEATURED_QUERIES.items():
        for _ in range(10):
            [(_, url)] = pending_shelves(discover(client, type=kind))[:1]
            assert parse_qs(urlparse(url.replace("&amp;", "&")).query)["q"][0] in choices


def test_shuffle_always_picks_a_different_search(client, provider_calls):
    html = discover(client, type="model")
    shuffle = re.search(r'<a href="([^"]+)" class="btn btn-sm btn-quiet">Shuffle</a>', html)
    current = re.search(r'Models for <span class="font-mono">“(\w+)”', html).group(1)
    assert shuffle.group(1) == f"/discover/?type=model&amp;shuffle={current}"
    for _ in range(10):
        shuffled = discover(client, type="model", shuffle=current)
        assert f"“{current}”" not in shuffled.split('id="featured-pick"', 1)[1].split("</div>")[0]


def test_a_search_shows_no_random_pick(client, provider_calls):
    html = discover(client, type="texture", q="brick")
    assert 'id="featured-pick"' not in html


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
    return re.findall(r'<li class="result-card" data-kind="\w+"[^>]*>.*?</li>', html, re.S)


def test_a_normal_shelf_shows_thumbnail_title_author_and_license(client, monkeypatch):
    found = [
        record(external_id="red_brick_03"),
        record(external_id="sky_01", title="Sky 01", author="Greg Zaal"),
    ]
    monkeypatch.setattr(polyhaven, "search_records", lambda query, kind, limit=12, page=1: found)
    html = fetch_shelf(client, "texture", "polyhaven")
    assert "2 results" in html
    first, second = cards(html)
    # The title's link opens the result in Discover's drawer (as a plain link, its own
    # page); CSS stretches it over the card. User request, 2026-11-06.
    assert (
        '<h3 class="result-title"><a href="/discover/asset/polyhaven/red_brick_03/" '
        'hx-get="/discover/asset/polyhaven/red_brick_03/" hx-target="#discover-drawer" '
        'hx-swap="innerHTML transition:false" aria-haspopup="dialog" class="result-link">'
        "Red Brick 03</a></h3>"
    ) in first
    # The provider's page is still a click away, in the corner, in a new tab.
    assert (
        '<a href="https://polyhaven.com/a/red_brick_03" target="_blank" '
        'rel="noopener noreferrer" class="card-action"'
    ) in first
    assert '<img src="https://cdn.example/red_brick_03.png" alt="" loading="lazy"' in first
    assert "Rob Tuytel" in first and ">CC0<" in first
    assert "Sky 01" in second and "Greg Zaal" in second
    # The logo is never placed on a provider thumbnail.
    assert 'class="mark' not in first


def test_a_shelf_shows_at_most_12_and_uneven_counts_as_returned(client, monkeypatch):
    many = [record(external_id=f"brick_{n:02}") for n in range(15)]
    monkeypatch.setattr(
        polyhaven, "search_records", lambda query, kind, limit=12, page=1: many[:limit]
    )
    monkeypatch.setattr(ambientcg, "search_records", lambda query, kind, limit=12, page=1: many[:1])
    assert len(cards(fetch_shelf(client, "model", "polyhaven"))) == 12
    one = fetch_shelf(client, "model", "ambientcg")
    assert len(cards(one)) == 1 and "1 result<" in one


def thumb(card):
    return re.search(r'<div class="result-thumb">(.*?)</div>', card, re.S).group(1)


@pytest.mark.parametrize(
    ("kind", "provider", "icon_class"),
    [
        ("texture", "ambientcg", "text-texture"),
        ("hdri", "polyhaven", "text-hdri"),
        ("model", "ambientcg", "text-model"),
        ("sound", "openverse", "text-sound"),
    ],
)
def test_a_result_without_a_thumbnail_shows_its_type_icon(
    client, monkeypatch, kind, provider, icon_class
):
    found = [record(provider=provider, kind=kind, thumbnail_url="")]
    monkeypatch.setattr(
        PROVIDERS_BY_KEY[provider], "search_records", lambda q, k, limit=12, page=1: found
    )
    [card] = cards(fetch_shelf(client, kind, provider))
    assert "<img" not in card
    icon = re.search(
        r'<span class="result-fallback ([\w-]+)" aria-hidden="true">(.*?)</span>', thumb(card), re.S
    )
    assert icon and icon.group(1) == icon_class
    expected = render_to_string("partials/icon.html", {"name": kind, "size": 28}).strip()
    assert icon.group(2).strip() == expected
    # The logo never stands in for a thumbnail.
    assert "mark" not in thumb(card)


def test_a_thumbnail_that_fails_to_load_is_swapped_for_the_type_icon(client, monkeypatch):
    monkeypatch.setattr(
        polyhaven, "search_records", lambda query, kind, limit=12, page=1: [record()]
    )
    [card] = cards(fetch_shelf(client, "texture", "polyhaven"))
    # The type icon sits under the image, and the image is marked for removal on error.
    inside = thumb(card)
    assert 'class="result-fallback text-texture"' in inside
    assert re.search(r'<img src="[^"]+"[^>]*data-thumb-fallback>', inside)
    assert inside.index("result-fallback") < inside.index("<img")
    assert "mark" not in inside
    shell_js = (settings.BASE_DIR / "static" / "js" / "shell.js").read_text(encoding="utf-8")
    # Image errors don't bubble, so the listener must run in the capture phase (true).
    listener = re.search(
        r'document\.addEventListener\(\s*"error",(.*?)\},\s*true\s*\);', shell_js, re.S
    )
    assert listener, "no capture-phase error listener in shell.js"
    assert 'image.hasAttribute("data-thumb-fallback")' in listener.group(1)
    assert "image.remove()" in listener.group(1)
    css = (settings.BASE_DIR / "styles" / "source.css").read_text(encoding="utf-8")
    assert re.search(r"\.result-thumb img \{ position: absolute; inset: 0;", css)


def test_an_empty_shelf_says_no_matches_and_is_not_an_error(client, monkeypatch):
    # Poly Haven's keywordMatches == 0 comes back from search_records as []
    # (tested at the HTTP level in test_provider_records.py).
    monkeypatch.setattr(polyhaven, "search_records", lambda query, kind, limit=12, page=1: [])
    html = fetch_shelf(client, "texture", "polyhaven", query="zzqqxx")
    assert 'No Poly Haven matches for <span class="font-mono">“zzqqxx”</span>.' in html
    assert "Try a different or broader phrase." in html
    assert 'role="alert"' not in html and "Retry" not in html


def test_an_error_shelf_shows_the_provider_message_unchanged(client, monkeypatch):
    message = "Openverse Audio did not respond within 10 seconds. Try again in a moment."

    def failing(query, kind, limit=12, page=1):
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

    def flaky(query, kind, limit=12, page=1):
        answer = next(answers)
        if isinstance(answer, Exception):
            raise answer
        return answer

    monkeypatch.setattr(polyhaven, "search_records", flaky)
    failed = fetch_shelf(client, "texture", "polyhaven")
    retry_url = re.search(r'<button [^>]*hx-get="([^"]+)"[^>]*>Retry</button>', failed).group(1)
    recovered = client.get(retry_url, headers=HTMX).content.decode()
    assert "Red Brick 03" in recovered and 'role="alert"' not in recovered


# ---------------------------------------------------------------- caching


def test_a_repeated_search_calls_the_provider_once(client, provider_calls):
    # The same search three times, differing only in case and whitespace.
    for query in ("Mossy Rock", "mossy%20rock", "%20%20MOSSY%20%20%20rock%20"):
        fetch_shelf(client, "texture", "polyhaven", query=query)
    assert provider_calls == [("polyhaven", "texture", "Mossy Rock")]


def test_a_failure_is_never_cached_and_a_success_on_retry_is(client, monkeypatch):
    answers = iter([ProviderError("Could not connect to Poly Haven."), [record()]])
    calls = []

    def flaky(query, kind, limit=12, page=1):
        calls.append(query)
        answer = next(answers)
        if isinstance(answer, Exception):
            raise answer
        return answer

    monkeypatch.setattr(polyhaven, "search_records", flaky)
    failed = fetch_shelf(client, "texture", "polyhaven")
    retried = fetch_shelf(client, "texture", "polyhaven")
    repeated = fetch_shelf(client, "texture", "polyhaven")

    assert 'role="alert"' in failed
    # Retry reached the provider again, and its success is shown...
    assert "Red Brick 03" in retried and 'role="alert"' not in retried
    # ...and cached: the third request is served without calling the provider.
    assert repeated == retried
    assert calls == ["brick", "brick"]


# ---------------------------------------------------------------- provider status


def status_bar(html):
    """{provider key: (data-status, title)} for each provider in the status bar."""
    bar = html.split('id="status-bar"', 1)[1]
    return {
        key: (status, title)
        for key, status, title in re.findall(
            r'<span id="status-(\w+)" data-status="(\w+)" title="([^"]+)"', bar
        )
    }


def test_shelf_outcomes_set_the_status_bar_and_unused_providers_are_unknown(client, monkeypatch):
    def failing(query, kind, limit=12, page=1):
        raise ProviderError("Could not connect to ambientCG.")

    monkeypatch.setattr(ambientcg, "search_records", failing)
    monkeypatch.setattr(
        polyhaven, "search_records", lambda query, kind, limit=12, page=1: [record()]
    )
    before = status_bar(discover(client))
    fetch_shelf(client, "texture", "ambientcg")
    fetch_shelf(client, "texture", "polyhaven")
    after = status_bar(discover(client))

    assert before == {
        "ambientcg": ("unknown", "ambientCG: status unknown"),
        "polyhaven": ("unknown", "Poly Haven: status unknown"),
        "openverse": ("unknown", "Openverse Audio: status unknown"),
    }
    assert after == {
        "ambientcg": ("error", "ambientCG: error on the last search"),
        "polyhaven": ("ok", "Poly Haven: OK"),
        "openverse": ("unknown", "Openverse Audio: status unknown"),
    }


@pytest.mark.parametrize("failure", FAILURES)
def test_a_failure_message_reaches_the_alert_unchanged_and_never_the_cache(
    client, monkeypatch, failure
):
    message = FAILURES[failure].format(name=openverse.NAME)
    monkeypatch.setattr(openverse, "search_records", raising(message))
    html = fetch_shelf(client, "sound", "openverse", query="rain")
    assert f'<p class="text-sm text-fg-secondary mt-0.5">{escape(message)}</p>' in html
    assert cache.get(discover_module.search_cache_key("openverse", "sound", "rain")) is None


def test_a_successful_search_is_cached_for_an_hour(client, monkeypatch):
    stored = []
    real_set = discover_module.cache.set

    def spy(key, value, timeout=None):
        stored.append((key, timeout))
        real_set(key, value, timeout)

    monkeypatch.setattr(discover_module.cache, "set", spy)
    monkeypatch.setattr(
        polyhaven, "search_records", lambda query, kind, limit=12, page=1: [record()]
    )
    fetch_shelf(client, "texture", "polyhaven")
    search_key = discover_module.search_cache_key("polyhaven", "texture", "brick")
    assert (search_key, 60 * 60) in stored


# ---------------------------------------------------------------- credits


@pytest.mark.parametrize(
    ("kind", "provider", "credit", "home"),
    [
        ("texture", "ambientcg", "Assets from ambientCG · CC0", "https://ambientcg.com"),
        ("hdri", "polyhaven", "Powered by Poly Haven", "https://polyhaven.com"),
        ("sound", "openverse", "Made with Openverse", "https://openverse.org"),
    ],
)
@pytest.mark.parametrize("outcome", ["results", "empty", "error"])
def test_every_shelf_credits_its_provider(
    client, monkeypatch, kind, provider, credit, home, outcome
):
    answers = {
        "results": lambda query, k, limit=12, page=1: [record(provider=provider, kind=kind)],
        "empty": lambda query, k, limit=12, page=1: [],
        "error": raising("Could not connect."),
    }
    monkeypatch.setattr(PROVIDERS_BY_KEY[provider], "search_records", answers[outcome])
    expected = (
        f'<p class="shelf-credit"><a href="{home}" target="_blank" '
        f'rel="noopener noreferrer">{credit}</a></p>'
    )
    assert expected in fetch_shelf(client, kind, provider)
    # The pending shelf on the page carries it too.
    assert expected in discover(client, type=kind, q="brick")


# ---------------------------------------------------------------- status bar, out of band


def oob_status(html):
    return re.findall(
        r'<span id="status-(\w+)" data-status="(\w+)" title="[^"]+" class="status-item" '
        r'hx-swap-oob="true">',
        html,
    )


def test_a_loaded_shelf_updates_the_status_bar_out_of_band(client, monkeypatch):
    monkeypatch.setattr(ambientcg, "search_records", raising("Could not connect to ambientCG."))
    monkeypatch.setattr(
        polyhaven, "search_records", lambda query, kind, limit=12, page=1: [record()]
    )
    assert oob_status(fetch_shelf(client, "texture", "ambientcg")) == [("ambientcg", "error")]
    assert oob_status(fetch_shelf(client, "texture", "polyhaven")) == [("polyhaven", "ok")]
    # The page's pending shelves send no status: nothing has been asked yet.
    assert oob_status(discover(client, type="texture", q="brick")) == []


def test_a_cached_shelf_leaves_the_last_known_status_alone(client, monkeypatch):
    answers = iter([[record()], ProviderError("Could not connect to Poly Haven.")])

    def answer(query, kind, limit=12, page=1):
        value = next(answers)
        if isinstance(value, Exception):
            raise value
        return value

    monkeypatch.setattr(polyhaven, "search_records", answer)
    fetch_shelf(client, "texture", "polyhaven", query="brick")  # ok, cached
    fetch_shelf(client, "texture", "polyhaven", query="sky")  # error
    cached = fetch_shelf(client, "texture", "polyhaven", query="brick")
    # The cached shelf shows its results, and the bar keeps the newest real outcome.
    assert "Red Brick 03" in cached
    assert oob_status(cached) == [("polyhaven", "error")]
    assert status_bar(discover(client))["polyhaven"][0] == "error"


# ---------------------------------------------------------------- Load more


def bricks(start, count):
    return [
        record(external_id=f"brick_{n:02}", title=f"Brick {n:02}")
        for n in range(start, start + count)
    ]


@pytest.fixture
def paged(monkeypatch):
    """Poly Haven with 30 bricks, served 12 per page; the list records each page asked for."""
    pages = []

    def fake(query, kind, limit=12, page=1):
        pages.append(page)
        start = (page - 1) * limit
        return bricks(start, max(0, min(limit, 30 - start)))

    monkeypatch.setattr(polyhaven, "search_records", fake)
    return pages


def more_slot(html):
    return re.search(r'<div id="shelf-polyhaven-more" class="shelf-more">(.*?)\n</div>', html, re.S)


def appended_cards(html):
    block = re.search(
        r'<ul hx-swap-oob="beforeend:#shelf-polyhaven-results">(.*?)</ul>', html, re.S
    )
    return cards(block.group(1)) if block else []


def test_a_full_first_page_ends_with_load_more(client, paged):
    html = fetch_shelf(client, "texture", "polyhaven")
    assert '<ul id="shelf-polyhaven-results" class="result-grid">' in html
    assert len(cards(html)) == 12
    button = re.search(r"<button [^>]*>.*?</button>", more_slot(html).group(1), re.S).group(0)
    assert f'hx-get="{shelf_url("texture", "polyhaven", "brick")}&amp;page=2"' in button
    assert 'hx-target="#shelf-polyhaven-more"' in button and 'hx-swap="outerHTML"' in button
    assert "Load 12 more" in button


def test_a_short_first_page_has_no_load_more(client, monkeypatch):
    monkeypatch.setattr(
        polyhaven, "search_records", lambda query, kind, limit=12, page=1: bricks(0, 5)
    )
    html = fetch_shelf(client, "texture", "polyhaven")
    assert "shelf-polyhaven-more" not in html and "Load" not in html


def test_load_more_appends_the_next_page_and_updates_the_count(client, paged):
    html = fetch_shelf(client, "texture", "polyhaven", query="brick&page=2")
    assert paged == [2]
    # The reply's main content is the new slot, with a button for page 3...
    assert html.lstrip().startswith('<div id="shelf-polyhaven-more"')
    assert "page=3" in more_slot(html).group(1)
    # ...the 12 new cards go to the end of the grid, and the count and status follow.
    assert [re.search(r"Brick \d+", card).group(0) for card in appended_cards(html)] == [
        f"Brick {n:02}" for n in range(12, 24)
    ]
    assert (
        '<span id="shelf-polyhaven-count" class="micro text-fg-weak" hx-swap-oob="true">'
        "24 results</span>"
    ) in html
    assert oob_status(html) == [("polyhaven", "ok")]


def test_the_last_page_ends_with_a_note_instead_of_load_more(client, paged):
    html = fetch_shelf(client, "texture", "polyhaven", query="brick&page=3")
    assert len(appended_cards(html)) == 6
    assert "30 results</span>" in html
    slot = more_slot(html).group(1)
    assert "<button" not in slot
    assert (
        'That\'s everything from Poly Haven for <span class="font-mono">“brick”</span>.'
    ) in slot


def test_an_empty_next_page_just_ends_the_shelf(client, monkeypatch):
    monkeypatch.setattr(polyhaven, "search_records", lambda query, kind, limit=12, page=1: [])
    html = fetch_shelf(client, "texture", "polyhaven", query="brick&page=2")
    assert appended_cards(html) == [] and "shelf-polyhaven-count" not in html
    assert "That's everything from Poly Haven" in more_slot(html).group(1)


def test_a_failed_next_page_offers_retry_in_place_and_keeps_the_cards(client, monkeypatch):
    message = "Could not connect to Poly Haven. Check your internet connection."
    monkeypatch.setattr(polyhaven, "search_records", raising(message))
    html = fetch_shelf(client, "texture", "polyhaven", query="brick&page=2")
    slot = more_slot(html).group(1)
    assert 'role="alert"' in slot and message in slot
    retry = re.search(r"<button [^>]*>\s*Retry\s*</button>", slot).group(0)
    assert f'hx-get="{shelf_url("texture", "polyhaven", "brick")}&amp;page=2"' in retry
    assert 'hx-target="#shelf-polyhaven-more"' in retry
    assert appended_cards(html) == [] and oob_status(html) == [("polyhaven", "error")]
    assert cache.get(discover_module.search_cache_key("polyhaven", "texture", "brick", 2)) is None


def test_each_page_is_cached_on_its_own(client, paged):
    for query in ("brick", "brick&page=2", "Brick&page=2", "brick"):
        fetch_shelf(client, "texture", "polyhaven", query=query)
    assert paged == [1, 2]


def test_load_more_stops_at_page_20(client, monkeypatch):
    monkeypatch.setattr(
        polyhaven, "search_records", lambda query, kind, limit=12, page=1: bricks(0, 12)
    )
    html = fetch_shelf(client, "texture", "polyhaven", query="brick&page=20")
    assert "<button" not in more_slot(html).group(1)


@pytest.mark.parametrize("as_htmx", [True, False], ids=["htmx", "direct"])
@pytest.mark.parametrize("page", ["0", "21", "two", "-1", ""])
def test_a_bad_page_is_refused_before_any_provider_is_called(client, provider_calls, page, as_htmx):
    url = shelf_url("texture", "polyhaven", "brick") + f"&page={page}"
    response = client.get(url, headers=HTMX if as_htmx else {})
    assert response.status_code == 400
    assert provider_calls == []


def test_a_later_page_opened_directly_goes_to_its_discover_page(client, provider_calls):
    response = client.get(shelf_url("texture", "polyhaven", "brick") + "&page=2")
    assert response.status_code == 302 and response.url == "/discover/?type=texture&q=brick"
    assert provider_calls == []


# ---------------------------------------------------------------- sound previews

PREVIEW = "https://cdn.freesound.org/previews/345/345560_5121236-hq.mp3"


def test_a_sound_card_has_a_play_button_for_its_preview(client, monkeypatch):
    found = [
        record(provider="openverse", kind="sound", title="Rain & Thunder", preview_url=PREVIEW)
    ]
    monkeypatch.setattr(openverse, "search_records", lambda query, kind, limit=12, page=1: found)
    [card] = cards(fetch_shelf(client, "sound", "openverse", query="rain"))
    thumbnail = card.split('<div class="result-body">', 1)[0]
    button = re.search(r"<button [^>]*>", thumbnail).group(0)
    assert f'data-sound-preview="{PREVIEW}"' in button
    assert 'aria-pressed="false"' in button
    assert 'aria-label="Play a preview of Rain &amp; Thunder"' in button
    # The button sits in the thumbnail, outside the title's link, so it plays
    # rather than opening the result's drawer.
    link = re.search(r'<a [^>]*class="result-link">.*?</a>', card, re.S).group(0)
    assert "<button" not in link
    assert '<span class="sound-progress" aria-hidden="true"></span>' in card


def test_only_cards_with_a_preview_get_a_play_button(client, monkeypatch):
    monkeypatch.setattr(
        polyhaven, "search_records", lambda query, kind, limit=12, page=1: [record()]
    )
    monkeypatch.setattr(
        openverse,
        "search_records",
        lambda query, kind, limit=12, page=1: [record(provider="openverse", kind="sound")],
    )
    assert "data-sound-preview" not in fetch_shelf(client, "texture", "polyhaven")
    assert "data-sound-preview" not in fetch_shelf(client, "sound", "openverse")


def test_the_sound_script_loads_on_every_page_and_plays_one_preview_at_a_time(client):
    html = client.get(reverse("packs:home")).content.decode()
    assert re.search(r'<script src="/static/js/sound-preview\.js\?v=\d+" defer></script>', html)
    script = (settings.BASE_DIR / "static" / "js" / "sound-preview.js").read_text(encoding="utf-8")
    # Delegated, so cards that arrive later (shelves, Load more) work too.
    assert 'document.addEventListener("click"' in script
    assert 'event.target.closest("[data-sound-preview]")' in script
    assert "new Audio(button.dataset.soundPreview)" in script
    # Starting a new preview stops the old one; a swapped-away card stops its sound.
    assert "stop();\n    start(button);" in script
    assert 'document.addEventListener("htmx:afterSwap"' in script
    assert "!document.contains(current.button)" in script


# ---------------------------------------------------------------- card details on hover


def test_hovering_a_card_shows_its_full_details(client, monkeypatch):
    long_author = "Greg Zaal, Rico Cilliers, Jenelle van Heerden"
    found = [
        record(
            title="Moon 03",
            author=long_author,
            tags=("moon", "rock", "crater", "space", "grey", "rough", "dust"),
        )
    ]
    monkeypatch.setattr(polyhaven, "search_records", lambda query, kind, limit=12, page=1: found)
    [card] = cards(fetch_shelf(client, "texture", "polyhaven", query="moon"))
    # The author line is cut with an ellipsis by CSS. The body's one column must
    # be allowed to shrink (minmax(0, 1fr)), or the line overflows the card.
    assert f'<span class="result-author">{long_author}</span>' in card
    css = (settings.BASE_DIR / "styles" / "source.css").read_text(encoding="utf-8")
    assert re.search(r"\.result-body \{[^}]*grid-template-columns: minmax\(0, 1fr\);", css)
    assert (
        ".result-author { min-width: 0; overflow: hidden; text-overflow: ellipsis; "
        "white-space: nowrap; }"
    ) in css
    # ...and the details panel shows everything, every tag included.
    details = re.search(r'<div class="result-details" aria-hidden="true">(.*?)</dl>', card, re.S)
    text = " ".join(re.sub(r"<[^>]+>", " ", details.group(1)).split())
    assert text == (
        f"Moon 03 By {long_author} License CC0 Commercial Usable. No conditions. "
        "From Poly Haven Tags moon, rock, crater, space, grey, rough, dust"
    )
    assert "html[data-pointer] .result-card:hover .result-details" in css
    # The panel lets clicks through to the card's link.
    assert re.search(r"\.result-details \{[^}]*pointer-events: none;", css)


def test_the_details_go_away_after_a_click_unless_details_keeps_them_open(client, monkeypatch):
    """Clicking a card (or Save) leaves mouse focus inside it. Only keyboard focus
    (:focus-visible) shows the panel, so it goes once the pointer leaves, unless
    the card's Details button keeps it open."""
    monkeypatch.setattr(
        polyhaven, "search_records", lambda query, kind, limit=12, page=1: [record()]
    )
    [card] = cards(fetch_shelf(client, "texture", "polyhaven"))
    css = (settings.BASE_DIR / "styles" / "source.css").read_text(encoding="utf-8")
    assert ".result-card:focus-within" not in css
    assert ".result-card:has(:focus-visible) .result-details" in css
    assert (
        '.result-card[data-details="open"] .result-details { opacity: 1; transform: none; }' in css
    )
    # Details: a toggle in the card's corner, wired by card-actions.js (loaded in base.html).
    actions = re.search(r'<div class="card-actions">(.*?)</div>\n', card, re.S).group(1)
    assert re.search(
        r'<button type="button" class="card-action" data-card-details aria-pressed="false" '
        r'aria-label="Keep the details of Red Brick 03 open">',
        actions,
    )
    script = (settings.BASE_DIR / "static" / "js" / "card-actions.js").read_text(encoding="utf-8")
    assert 'card.dataset.details = "open"' in script
    assert 'button.setAttribute("aria-pressed", String(open))' in script
    page = client.get(reverse("catalog:discover")).content.decode()
    assert "js/card-actions.js" in page


def test_a_textures_thumbnail_is_square_and_shown_whole(client, monkeypatch):
    monkeypatch.setattr(
        polyhaven, "search_records", lambda query, kind, limit=12, page=1: [record()]
    )
    [card] = cards(fetch_shelf(client, "texture", "polyhaven"))
    assert card.startswith('<li class="result-card" data-kind="texture">')
    css = (settings.BASE_DIR / "styles" / "source.css").read_text(encoding="utf-8")
    assert '.result-card[data-kind="texture"] .result-thumb { aspect-ratio: 1 / 1; }' in css
    assert '.result-card[data-kind="texture"] .result-thumb img { object-fit: contain; }' in css


def test_each_card_has_its_actions_in_the_corner_and_never_the_logo(member_client, monkeypatch):
    monkeypatch.setattr(
        polyhaven, "search_records", lambda query, kind, limit=12, page=1: [record()]
    )
    [card] = cards(fetch_shelf(member_client, "texture", "polyhaven"))
    actions = re.search(r'<div class="card-actions">(.*?)</div>\n', card, re.S).group(1)
    tips = re.findall(
        r'<span class="card-tip" aria-hidden="true">(.*?)</span>(?:</button>|</a>)', actions
    )
    tips = [re.sub(r"<[^>]+>", "", tip).replace("Saving…", "") for tip in tips]
    assert tips == ["Save to library", "Add to pack", "View on Poly Haven", "Details"]
    assert 'data-picker="pack-picker" data-picker-asset="Red Brick 03"' in actions
    # The corner sits on the provider's thumbnail, so the logo mark never appears there.
    assert "mark" not in actions
    # The old full-width Save row at the card's foot is gone.
    assert "result-actions" not in card
    # A member's Discover page holds the pack picker the buttons open.
    page = member_client.get(reverse("catalog:discover")).content.decode()
    assert page.count('<dialog id="pack-picker" class="picker-dialog"') == 1
    assert "collection" not in page.lower()
