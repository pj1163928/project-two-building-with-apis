"""Regression tests for the Project 1 console script and its provider calls.

These lock the behaviour of each provider's existing `search()` and
`get_details()`, and of `asset_search.py` end to end, using canned
`responses` mocks. They must keep passing unchanged as the provider
modules gain the Toolbox's new functions.
"""

import pytest
import requests
from responses import matchers

import asset_search
from providers import ProviderError, ambientcg, openverse, polyhaven
from providers.http import USER_AGENT

ACG_URL = ambientcg.API_URL
PH_URL = polyhaven.API_URL
OV_URL = openverse.API_URL

ACG_ASSET = {
    "id": "Bricks097",
    "title": "Bricks 097",
    "type": "material",
    "url": "https://ambientcg.com/a/Bricks097",
    "tags": ["brick", "bricks", "brown"],
    "maps": ["Color", "Displacement", "NormalGL", "Roughness"],
    "dimensions": {"width": 2.5, "height": 2.5, "depth": 0.1},
    "downloads": [
        {
            "attributes": "1K-JPG",
            "extension": "zip",
            "size": 5172084,
            "url": "https://ambientcg.com/get?file=Bricks097_1K-JPG.zip",
        },
        {
            "attributes": "2K-JPG",
            "extension": "zip",
            "size": 17000000,
            "url": "https://ambientcg.com/get?file=Bricks097_2K-JPG.zip",
        },
    ],
}

PH_INFO = {
    "name": "Red Bricks 02",
    "type": 1,
    "max_resolution": [8192, 8192],
    "dimensions": [2500, 2500],
    "authors": {"Rob Tuytel": "All"},
    "categories": ["brick", "wall"],
    "tags": ["rough", "red", "bricks"],
    "download_count": 12345,
    "description": "Old red bricks.",
}

PH_FILES = {
    "Diffuse": {
        "1k": {"jpg": {"size": 100, "url": "https://dl.polyhaven.org/d_1k.jpg"}},
        "2k": {
            "jpg": {"size": 400, "url": "https://dl.polyhaven.org/d_2k.jpg"},
            "png": {"size": 900, "url": "https://dl.polyhaven.org/d_2k.png"},
        },
    },
    "nor_gl": {"2k": {"jpg": {"size": 300, "url": "https://dl.polyhaven.org/n_2k.jpg"}}},
    "blend": {
        "2k": {
            "blend": {
                "size": 1000,
                "url": "https://dl.polyhaven.org/x_2k.blend",
                "include": {"textures/d.jpg": {"size": 400}, "textures/n.jpg": {"size": 300}},
            }
        }
    },
    "thumbnail": "not-a-dict-entry",
}

OV_ITEM = {
    "id": "a8783d20-f1af-4c4b-b9ec-a8c212f67fee",
    "title": "Footsteps, Stones, A.wav",
    "category": "sound_effect",
    "duration": 18944,
    "filetype": "mp3",
    "creator": "InspectorJ",
    "license": "by",
    "license_version": "4.0",
    "foreign_landing_url": "https://freesound.org/s/123/",
    "url": "https://cdn.freesound.org/123.mp3",
    "creator_url": "https://freesound.org/people/InspectorJ/",
    "source": "freesound",
    "bit_rate": 128000,
    "sample_rate": 44100,
    "filesize": 300000,
    "alt_files": [],
    "license_url": "https://creativecommons.org/licenses/by/4.0/",
    "attribution": '"Footsteps, Stones, A.wav" by InspectorJ is licensed under CC BY 4.0.',
}


# ---------------------------------------------------------------- ambientCG


def test_ambientcg_search_sends_filter_and_returns_rows(mocked_responses):
    mocked_responses.get(
        ACG_URL,
        match=[
            matchers.query_param_matcher(
                {
                    "q": "brick",
                    "limit": "5",
                    "include": "title,url,tags,type,maps,dimensions,downloads",
                    "type": "material",
                }
            ),
            matchers.header_matcher({"User-Agent": USER_AGENT}),
        ],
        json={"assets": [ACG_ASSET]},
    )
    rows = ambientcg.search("  brick ", "textures")
    assert rows == [
        {
            "id": "Bricks097",
            "name": "Bricks 097",
            "type": "material",
            "info": "4 maps, 2 downloads",
            "license": "CC0",
        }
    ]


def test_ambientcg_search_with_no_results(mocked_responses):
    mocked_responses.get(ACG_URL, json={"assets": []})
    assert ambientcg.search("zzqqxx") == []


def test_ambientcg_get_details(mocked_responses):
    mocked_responses.get(
        ACG_URL,
        match=[matchers.query_param_matcher({"id": "Bricks097"}, strict_match=False)],
        json={"assets": [ACG_ASSET]},
    )
    details = ambientcg.get_details(" Bricks097 ")
    assert details == {
        "id": "Bricks097",
        "name": "Bricks 097",
        "type": "material",
        "url": "https://ambientcg.com/a/Bricks097",
        "tags": ["brick", "bricks", "brown"],
        "maps": ["Color", "Displacement", "NormalGL", "Roughness"],
        "dimensions": {"width": 2.5, "height": 2.5, "depth": 0.1},
        "downloads": ACG_ASSET["downloads"],
        "license": "CC0",
    }


def test_ambientcg_unknown_id_is_a_provider_error(mocked_responses):
    mocked_responses.get(ACG_URL, json={"assets": []})
    with pytest.raises(ProviderError, match="ambientCG has no asset with ID 'Nope001'"):
        ambientcg.get_details("Nope001")


# ---------------------------------------------------------------- Poly Haven


def test_polyhaven_search_fetches_info_for_each_hit(mocked_responses):
    mocked_responses.get(
        f"{PH_URL}/search",
        match=[matchers.query_param_matcher({"q": "brick", "limit": "5", "t": "textures"})],
        json={"keywordMatches": 1, "results": [{"slug": "red_bricks_02", "score": 0.9}]},
    )
    mocked_responses.get(f"{PH_URL}/info/red_bricks_02", json=PH_INFO)
    rows = polyhaven.search("Brick", "textures")
    assert rows == [
        {
            "id": "red_bricks_02",
            "name": "Red Bricks 02",
            "type": "texture",
            "info": "max 8192x8192, 2.5 x 2.5 m",
            "license": "CC0",
        }
    ]


def test_polyhaven_zero_keyword_matches_means_no_results(mocked_responses):
    mocked_responses.get(
        f"{PH_URL}/search",
        json={"keywordMatches": 0, "results": [{"slug": "something_semantic", "score": 0.1}]},
    )
    assert polyhaven.search("zzqqxx") == []


def test_polyhaven_get_details_summarizes_files(mocked_responses):
    mocked_responses.get(f"{PH_URL}/info/red_bricks_02", json=PH_INFO)
    mocked_responses.get(f"{PH_URL}/files/red_bricks_02", json=PH_FILES)
    details = polyhaven.get_details("red_bricks_02")
    assert details["id"] == "red_bricks_02"
    assert details["name"] == "Red Bricks 02"
    assert details["type"] == "texture"
    assert details["url"] == "https://polyhaven.com/a/red_bricks_02"
    assert details["max_resolution"] == "8192x8192"
    assert details["physical_size"] == "2.5 x 2.5 m"
    assert details["authors"] == {"Rob Tuytel": "All"}
    assert details["download_count"] == 12345
    assert details["license"] == "CC0"
    assert {res: dict(fmts) for res, fmts in details["maps"].items()} == {
        "1k": {"jpg": 100},
        "2k": {"jpg": 700, "png": 900},
    }
    assert dict(details["bundles"]) == {"blend": {"2k": 1700}}


def test_polyhaven_404_is_a_friendly_provider_error(mocked_responses):
    mocked_responses.get(f"{PH_URL}/info/missing_asset", status=404, body="Not found")
    with pytest.raises(ProviderError, match=r"Poly Haven has nothing at that address \(HTTP 404\)"):
        polyhaven.get_details("missing_asset")


# ---------------------------------------------------------------- Openverse


def test_openverse_search_returns_rows(mocked_responses):
    mocked_responses.get(
        OV_URL,
        match=[matchers.query_param_matcher({"q": "footsteps", "page_size": "5"})],
        json={"results": [OV_ITEM]},
    )
    assert openverse.search("footsteps") == [
        {
            "id": OV_ITEM["id"],
            "name": "Footsteps, Stones, A.wav",
            "type": "sound_effect",
            "info": "0:19, mp3, by InspectorJ",
            "license": "CC BY 4.0",
        }
    ]


def test_openverse_get_details(mocked_responses):
    mocked_responses.get(f"{OV_URL}{OV_ITEM['id']}/", json=OV_ITEM)
    details = openverse.get_details(OV_ITEM["id"])
    assert details["name"] == "Footsteps, Stones, A.wav"
    assert details["audio_url"] == "https://cdn.freesound.org/123.mp3"
    assert details["license"] == "CC BY 4.0"
    assert details["attribution"] == OV_ITEM["attribution"]
    assert details["duration_ms"] == 18944


@pytest.mark.parametrize(
    ("code", "version", "label"),
    [
        ("cc0", "1.0", "CC0 1.0"),
        ("pdm", "1.0", "Public Domain Mark"),
        ("by-sa", "4.0", "CC BY-SA 4.0"),
        (None, None, "unknown"),
    ],
)
def test_openverse_license_label(code, version, label):
    assert openverse.license_label(code, version) == label


def test_openverse_server_error_html_body_is_not_leaked(mocked_responses):
    mocked_responses.get(OV_URL, status=500, body="<html><body>Traceback ...</body></html>")
    with pytest.raises(ProviderError) as excinfo:
        openverse.search("footsteps")
    assert str(excinfo.value) == ("Openverse Audio had a server error (HTTP 500). Try again later.")


# ---------------------------------------------------------------- shared HTTP errors


def test_timeout_is_a_friendly_provider_error(mocked_responses):
    mocked_responses.get(ACG_URL, body=requests.Timeout())
    with pytest.raises(ProviderError, match="ambientCG did not respond within 10 seconds"):
        ambientcg.search("brick")


def test_connection_error_is_a_friendly_provider_error(mocked_responses):
    mocked_responses.get(ACG_URL, body=requests.ConnectionError())
    with pytest.raises(ProviderError, match="Could not connect to ambientCG"):
        ambientcg.search("brick")


def test_rate_limit_mentions_retry_after(mocked_responses):
    mocked_responses.get(OV_URL, status=429, headers={"Retry-After": "30"})
    with pytest.raises(ProviderError, match="asked to wait 30 seconds"):
        openverse.search("footsteps")


# ---------------------------------------------------------------- console script


def test_console_search_and_details_end_to_end(mocked_responses, monkeypatch, capsys):
    mocked_responses.get(ACG_URL, json={"assets": [ACG_ASSET]})  # search, then details
    answers = iter(["1", "", "brick", "2", "1", "n"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))

    asset_search.main()

    out = capsys.readouterr().out
    assert "Searching ambientCG for 'brick'..." in out
    assert "Bricks 097" in out
    assert "4 maps, 2 downloads" in out
    assert "Fetching details for 'Bricks097' from ambientCG..." in out
    assert "Bricks 097  [Bricks097]" in out
    assert "Downloads (2):" in out
    assert "Goodbye." in out


def test_console_shows_provider_error_and_keeps_running(mocked_responses, monkeypatch, capsys):
    mocked_responses.get(OV_URL, status=500, body="<html>oops</html>")
    answers = iter(["3", "s", "footsteps", "n"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))

    asset_search.main()

    out = capsys.readouterr().out
    assert "Error: Openverse Audio had a server error (HTTP 500). Try again later." in out
    assert "<html>" not in out
    assert "Goodbye." in out


def test_console_quit_immediately(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda prompt="": "q")
    asset_search.main()
    assert "Goodbye." in capsys.readouterr().out
