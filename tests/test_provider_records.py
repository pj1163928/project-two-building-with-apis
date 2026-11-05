"""The Toolbox's provider record functions: `search_records()` and `AssetRecord`.

These sit next to the console script's `search()` and `get_details()`, which
test_console_regression.py locks. HTTP is faked with `responses`.
"""

import dataclasses
import logging
import re
from urllib.parse import parse_qs, urlparse

import pytest
import requests
import responses

from providers import (
    AssetRecord,
    ProviderError,
    ambientcg,
    openverse,
    polyhaven,
    providers_for_kind,
)
from providers import cache as provider_cache

# The PRD's type-to-provider mapping: for each kind, the providers in shelf
# order, and the query parameter and value each one must be sent.
PRD_MAPPING = {
    "texture": {"ambientcg": ("type", "material"), "polyhaven": ("t", "textures")},
    "hdri": {"ambientcg": ("type", "hdri"), "polyhaven": ("t", "hdris")},
    "model": {"ambientcg": ("type", "3d-model"), "polyhaven": ("t", "models")},
    "sound": {"openverse": None},
}
# An empty answer every provider understands: no assets, no keyword matches.
EMPTY_ANSWER = {"assets": [], "keywordMatches": 0, "results": []}


@pytest.mark.parametrize("kind", PRD_MAPPING)
def test_each_kind_searches_exactly_the_prd_providers_with_their_filter(kind):
    expected = PRD_MAPPING[kind]
    providers = providers_for_kind(kind)
    assert [provider.KEY for provider in providers] == list(expected)

    for provider in providers:
        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            rsps.get(re.compile(r"https://.*"), json=EMPTY_ANSWER)
            provider.search_records("brick", kind)
            assert len(rsps.calls) == 1, provider.KEY
            sent = parse_qs(urlparse(rsps.calls[0].request.url).query)

        if expected[provider.KEY] is None:
            # Openverse has no type split: sounds are its whole catalogue, so
            # no type parameter is sent at all, under any name.
            for param in ("type", "t", "category"):
                assert param not in sent, f"openverse sent {param}: {sent}"
        else:
            param, value = expected[provider.KEY]
            assert sent[param] == [value], provider.KEY


def test_an_unknown_kind_has_no_providers():
    assert providers_for_kind("textures") == []
    assert providers_for_kind("") == []


# ---------------------------------------------------------------- records on a normal response

ACG_ASSET = {
    "id": "Bricks097",
    "title": "Bricks 097",
    "type": "material",
    "url": "https://ambientcg.com/a/Bricks097",
    "tags": ["brick", "wall"],
    "thumbnails": {
        "64-PNG": "https://acg-media.example/64-PNG/Bricks097.png",
        "256-PNG": "https://acg-media.example/256-PNG/Bricks097.png",
    },
}
PH_INFO = {
    "name": "Red Brick 03",
    "type": 1,
    "tags": ["red", "industrial"],
    "authors": {"Rob Tuytel": "All"},
    "thumbnail_url": "https://cdn.polyhaven.com/asset_img/thumbs/red_brick_03.png?width=256",
}
OV_ITEM = {
    "id": "a8783d20-f1af-4c4b-b9ec-a8c212f67fee",
    "title": "Footsteps, Stones, A.wav",
    "creator": "InspectorJ",
    "license": "by",
    "license_version": "4.0",
    "license_url": "https://creativecommons.org/licenses/by/4.0/",
    "attribution": '"Footsteps, Stones, A.wav" by InspectorJ is licensed under CC BY 4.0.',
    "foreign_landing_url": "https://freesound.org/s/345560/",
    "thumbnail": "https://api.openverse.org/v1/audio/a8783d20/thumb/",
    "url": "https://cdn.freesound.org/previews/345/345560_5121236-hq.mp3",
    "tags": [{"name": "footsteps"}, {"name": "stone"}],
}
CC0_URL = "https://creativecommons.org/publicdomain/zero/1.0/"


def assert_every_field_filled(record, with_variants=False):
    """Every field is filled. Only sounds have a preview to play, so only they need one.

    Search results carry no variants (only fetch_record() fetches files), so
    `variants` must be filled only when `with_variants` is set.
    """
    assert isinstance(record, AssetRecord)
    for field in dataclasses.fields(AssetRecord):
        if field.name == "preview_url" and record.kind != "sound":
            assert record.preview_url == "", "only sounds have a preview"
            continue
        if field.name == "variants" and not with_variants:
            assert record.variants == (), "search results carry no variants"
            continue
        assert getattr(record, field.name), f"{field.name} is empty"


def test_ambientcg_search_records_fills_every_field(mocked_responses):
    mocked_responses.get(ambientcg.API_URL, json={"assets": [ACG_ASSET]})
    [record] = ambientcg.search_records("brick", "texture")
    assert_every_field_filled(record)
    assert record == AssetRecord(
        provider="ambientcg",
        external_id="Bricks097",
        kind="texture",
        title="Bricks 097",
        author="ambientCG",
        thumbnail_url="https://acg-media.example/256-PNG/Bricks097.png",
        license="CC0",
        license_url=CC0_URL,
        attribution='"Bricks 097" from ambientCG, CC0 1.0',
        source_url="https://ambientcg.com/a/Bricks097",
        tags=("brick", "wall"),
    )


def test_polyhaven_search_records_fills_every_field(mocked_responses):
    mocked_responses.get(
        f"{polyhaven.API_URL}/search",
        json={"keywordMatches": 1, "results": [{"slug": "red_brick_03", "score": 0.9}]},
    )
    mocked_responses.get(f"{polyhaven.API_URL}/info/red_brick_03", json=PH_INFO)
    [record] = polyhaven.search_records("Brick", "texture")
    assert_every_field_filled(record)
    assert record == AssetRecord(
        provider="polyhaven",
        external_id="red_brick_03",
        kind="texture",
        title="Red Brick 03",
        author="Rob Tuytel",
        thumbnail_url=PH_INFO["thumbnail_url"],
        license="CC0",
        license_url=CC0_URL,
        attribution='"Red Brick 03" by Rob Tuytel, from Poly Haven, CC0 1.0',
        source_url="https://polyhaven.com/a/red_brick_03",
        tags=("red", "industrial"),
    )


def test_openverse_search_records_fills_every_field(mocked_responses):
    mocked_responses.get(openverse.API_URL, json={"results": [OV_ITEM]})
    [record] = openverse.search_records("footsteps", "sound")
    assert_every_field_filled(record)
    assert record == AssetRecord(
        provider="openverse",
        external_id=OV_ITEM["id"],
        kind="sound",
        title="Footsteps, Stones, A.wav",
        author="InspectorJ",
        thumbnail_url=OV_ITEM["thumbnail"],
        license="CC BY 4.0",
        license_url=OV_ITEM["license_url"],
        attribution=OV_ITEM["attribution"],
        source_url=OV_ITEM["foreign_landing_url"],
        tags=("footsteps", "stone"),
        preview_url=OV_ITEM["url"],
    )


def test_search_records_asks_for_12_by_default(mocked_responses):
    mocked_responses.get(ambientcg.API_URL, json={"assets": []})
    mocked_responses.get(openverse.API_URL, json={"results": []})
    ambientcg.search_records("brick", "texture")
    openverse.search_records("rain", "sound")
    sent = [parse_qs(urlparse(call.request.url).query) for call in mocked_responses.calls]
    assert sent[0]["limit"] == ["12"]
    assert sent[1]["page_size"] == ["12"]


def test_search_records_never_returns_more_than_the_limit(mocked_responses):
    many = [{**ACG_ASSET, "id": f"Bricks{n:03}"} for n in range(20)]
    mocked_responses.get(ambientcg.API_URL, json={"assets": many})
    assert len(ambientcg.search_records("brick", "texture")) == 12


# ---------------------------------------------------------------- Poly Haven's /info calls


def test_polyhaven_fetches_info_only_for_hits_within_the_limit():
    """/search may return more hits than asked for; only 12 get an /info request."""
    hits = [{"slug": f"brick_{n:02}", "score": 0.9} for n in range(15)]
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        rsps.get(f"{polyhaven.API_URL}/search", json={"keywordMatches": 15, "results": hits})
        rsps.get(re.compile(rf"{re.escape(polyhaven.API_URL)}/info/.+"), json=PH_INFO)
        records = polyhaven.search_records("brick", "texture")
        info_calls = [call for call in rsps.calls if "/info/" in call.request.url]

    assert len(records) == 12
    assert [call.request.url.rsplit("/", 1)[1] for call in info_calls] == [
        f"brick_{n:02}" for n in range(12)
    ]


def test_polyhaven_zero_keyword_matches_makes_no_info_requests():
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        rsps.get(
            f"{polyhaven.API_URL}/search",
            json={"keywordMatches": 0, "results": [{"slug": "semantic_guess", "score": 0.4}]},
        )
        assert polyhaven.search_records("zzqqxx", "texture") == []
        assert len(rsps.calls) == 1


# ---------------------------------------------------------------- malformed answers


def test_malformed_items_are_skipped_not_fatal(mocked_responses):
    mocked_responses.get(
        ambientcg.API_URL,
        json={"assets": ["not-an-object", {"title": "no id"}, ACG_ASSET, {"id": 7}]},
    )
    records = ambientcg.search_records("brick", "texture")
    assert [record.external_id for record in records] == ["Bricks097"]


@pytest.mark.parametrize("body", [[1, 2], {"results": "nope"}, "a string"])
def test_a_response_of_the_wrong_shape_is_a_safe_provider_error(mocked_responses, body):
    mocked_responses.get(openverse.API_URL, json=body)
    with pytest.raises(ProviderError) as excinfo:
        openverse.search_records("rain", "sound")
    assert str(excinfo.value) == "Openverse Audio sent back results the Toolbox couldn't read."


def test_a_kind_the_provider_does_not_serve_is_refused_before_any_request():
    with responses.RequestsMock() as rsps:  # an unexpected request would fail here
        with pytest.raises(ValueError):
            openverse.search_records("brick", "texture")
        with pytest.raises(ValueError):
            ambientcg.search_records("rain", "sound")
        assert len(rsps.calls) == 0


# ---------------------------------------------------------------- safe messages, logged details

# Stands in for anything internal: a host, a path, a token, a stack detail.
SECRET = "internal-host.example:8443/secret-path"


def test_unexpected_request_failure_hides_exception_text_and_logs_it(mocked_responses, caplog):
    mocked_responses.get(
        ambientcg.API_URL, body=requests.TooManyRedirects(f"Exceeded 30 redirects at {SECRET}")
    )
    with caplog.at_level(logging.WARNING, logger="providers"):
        with pytest.raises(ProviderError) as excinfo:
            ambientcg.search_records("brick", "texture")
    assert str(excinfo.value) == "The request to ambientCG failed. Try again in a moment."
    assert SECRET in caplog.text


@pytest.mark.parametrize(
    "error",
    [requests.Timeout(f"read timeout {SECRET}"), requests.ConnectionError(f"refused {SECRET}")],
)
def test_network_failures_hide_exception_text_and_log_it(mocked_responses, caplog, error):
    mocked_responses.get(openverse.API_URL, body=error)
    with caplog.at_level(logging.WARNING, logger="providers"):
        with pytest.raises(ProviderError) as excinfo:
            openverse.search_records("rain", "sound")
    assert SECRET not in str(excinfo.value)
    assert SECRET in caplog.text


@pytest.mark.parametrize(
    ("status", "body"),
    [
        (500, f"<html><body><h1>Server Error (500)</h1>{SECRET}</body></html>"),
        (200, f"<!doctype html><title>Challenge</title>{SECRET}"),
        (403, f"Forbidden: {SECRET}"),
    ],
)
def test_bad_responses_hide_their_body_and_log_it(mocked_responses, caplog, status, body):
    mocked_responses.get(openverse.API_URL, status=status, body=body)
    with caplog.at_level(logging.WARNING, logger="providers"):
        with pytest.raises(ProviderError) as excinfo:
            openverse.search_records("rain", "sound")
    message = str(excinfo.value)
    assert SECRET not in message and "<" not in message
    assert f"HTTP {status}" in message
    assert SECRET in caplog.text


def test_retry_after_is_echoed_only_when_it_is_a_number(mocked_responses):
    mocked_responses.get(openverse.API_URL, status=429, headers={"Retry-After": SECRET})
    with pytest.raises(ProviderError) as excinfo:
        openverse.search_records("rain", "sound")
    assert SECRET not in str(excinfo.value)
    assert "HTTP 429" in str(excinfo.value)


# ---------------------------------------------------------------- Poly Haven's /info cache

PH_HIT = {"keywordMatches": 1, "results": [{"slug": "red_brick_03", "score": 0.9}]}
PH_INFO_URL = f"{polyhaven.API_URL}/info/red_brick_03"


def info_calls(rsps):
    return [call for call in rsps.calls if "/info/" in call.request.url]


def test_polyhaven_info_is_fetched_once_for_repeated_searches():
    with responses.RequestsMock() as rsps:
        rsps.get(f"{polyhaven.API_URL}/search", json=PH_HIT)
        rsps.get(PH_INFO_URL, json=PH_INFO)
        first = polyhaven.search_records("brick", "texture")
        second = polyhaven.search_records("red brick", "texture")
        assert len(info_calls(rsps)) == 1
    assert first == second


def test_polyhaven_info_is_cached_for_12_hours(monkeypatch):
    stored = {}

    class Recorder:
        def get(self, key, default=None):
            return stored.get(key, (default,))[0]

        def set(self, key, value, timeout=None):
            stored[key] = (value, timeout)

    monkeypatch.setattr(provider_cache, "_backend", Recorder())
    with responses.RequestsMock() as rsps:
        rsps.get(f"{polyhaven.API_URL}/search", json=PH_HIT)
        rsps.get(PH_INFO_URL, json=PH_INFO)
        polyhaven.search_records("brick", "texture")
    assert stored == {"polyhaven:info:red_brick_03": (PH_INFO, 12 * 60 * 60)}


def test_a_failed_polyhaven_info_is_not_cached():
    with responses.RequestsMock() as rsps:
        rsps.get(f"{polyhaven.API_URL}/search", json=PH_HIT)
        rsps.get(PH_INFO_URL, status=503)
        with pytest.raises(ProviderError):
            polyhaven.search_records("brick", "texture")
        rsps.replace(responses.GET, PH_INFO_URL, json=PH_INFO)
        [record] = polyhaven.search_records("brick", "texture")
        assert len(info_calls(rsps)) == 2
    assert record.title == "Red Brick 03"


def test_without_an_installed_cache_nothing_is_cached(monkeypatch):
    """The console script installs no cache, so every lookup goes to the provider."""
    monkeypatch.setattr(provider_cache, "_backend", None)
    with responses.RequestsMock() as rsps:
        rsps.get(f"{polyhaven.API_URL}/search", json=PH_HIT)
        rsps.get(PH_INFO_URL, json=PH_INFO)
        polyhaven.search_records("brick", "texture")
        polyhaven.search_records("brick", "texture")
        assert len(info_calls(rsps)) == 2


def test_the_console_search_never_uses_the_cache():
    """The console's search() is unchanged: it fetches /info every time, cache or not."""
    with responses.RequestsMock() as rsps:
        rsps.get(f"{polyhaven.API_URL}/search", json=PH_HIT)
        rsps.get(PH_INFO_URL, json=PH_INFO)
        polyhaven.search("brick")
        polyhaven.search("brick")
        assert len(info_calls(rsps)) == 2


# ---------------------------------------------------------------- paging (Load more)


def query_of(call):
    return parse_qs(urlparse(call.request.url).query)


def test_ambientcg_pages_with_offset(mocked_responses):
    mocked_responses.get(ambientcg.API_URL, json={"assets": [ACG_ASSET]})
    mocked_responses.get(ambientcg.API_URL, json={"assets": [ACG_ASSET]})
    ambientcg.search_records("brick", "texture")
    ambientcg.search_records("brick", "texture", page=3)
    first, third = (query_of(call) for call in mocked_responses.calls)
    assert "offset" not in first and first["limit"] == ["12"]
    assert third["offset"] == ["24"] and third["limit"] == ["12"]


def test_openverse_pages_with_page(mocked_responses):
    mocked_responses.get(openverse.API_URL, json={"results": [OV_ITEM]})
    mocked_responses.get(openverse.API_URL, json={"results": [OV_ITEM]})
    openverse.search_records("rain", "sound")
    openverse.search_records("rain", "sound", page=2)
    first, second = (query_of(call) for call in mocked_responses.calls)
    assert "page" not in first
    assert second["page"] == ["2"] and second["page_size"] == ["12"]


def test_openverse_stops_at_its_anonymous_depth_without_asking():
    with responses.RequestsMock() as rsps:  # any request would fail here
        assert openverse.search_records("rain", "sound", page=21) == []
        assert len(rsps.calls) == 0


def test_polyhaven_page_two_asks_for_24_hits_and_fetches_info_for_the_last_12():
    hits = [{"slug": f"brick_{n:02}", "score": 0.9} for n in range(24)]
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        rsps.get(f"{polyhaven.API_URL}/search", json={"keywordMatches": 30, "results": hits})
        rsps.get(re.compile(rf"{re.escape(polyhaven.API_URL)}/info/.+"), json=PH_INFO)
        records = polyhaven.search_records("brick", "texture", page=2)
        search, *infos = rsps.calls
    assert query_of(search)["limit"] == ["24"]
    assert [record.external_id for record in records] == [f"brick_{n:02}" for n in range(12, 24)]
    assert [call.request.url.rsplit("/", 1)[1] for call in infos] == [
        f"brick_{n:02}" for n in range(12, 24)
    ]


def test_polyhaven_pages_stop_at_the_keyword_matches():
    """Past the keyword matches, the semantic search only guesses: no more pages."""
    hits = [{"slug": f"guess_{n:02}", "score": 0.3} for n in range(24)]
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        rsps.get(f"{polyhaven.API_URL}/search", json={"keywordMatches": 12, "results": hits})
        assert polyhaven.search_records("brick", "texture", page=2) == []
        assert len(rsps.calls) == 1  # no /info at all
