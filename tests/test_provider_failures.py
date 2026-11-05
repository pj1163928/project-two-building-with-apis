"""Story 83 at the provider level: each failure gives its own friendly ProviderError.

HTTP is faked with `responses`. Every fake carries SECRET in its exception
text or body, standing in for anything internal; no message may contain it,
or any HTML. test_discover.py proves the same messages reach the shelves.
"""

import pytest
import requests

from providers import ProviderError, ambientcg, openverse, polyhaven

SECRET = "internal-host.example:8443/secret-path"
HTML_BODY = f"<!doctype html><html><body><h1>Server Error (500)</h1><p>{SECRET}</p></body></html>"

# One search per provider, with the URL its first request goes to.
SEARCHES = {
    "ambientcg": (ambientcg, ambientcg.API_URL, "texture"),
    "polyhaven": (polyhaven, f"{polyhaven.API_URL}/search", "texture"),
    "openverse": (openverse, openverse.API_URL, "sound"),
}


def search_fails_with(provider_key):
    provider, _, kind = SEARCHES[provider_key]
    with pytest.raises(ProviderError) as excinfo:
        provider.search_records("brick", kind)
    message = str(excinfo.value)
    assert SECRET not in message
    assert "<" not in message and ">" not in message
    return message


@pytest.mark.parametrize("provider_key", SEARCHES)
def test_a_timeout(mocked_responses, provider_key):
    provider, url, _ = SEARCHES[provider_key]
    mocked_responses.get(url, body=requests.Timeout(f"read timed out at {SECRET}"))
    assert search_fails_with(provider_key) == (
        f"{provider.NAME} did not respond within 10 seconds. Try again in a moment."
    )


@pytest.mark.parametrize("provider_key", SEARCHES)
def test_a_connection_error(mocked_responses, provider_key):
    provider, url, _ = SEARCHES[provider_key]
    mocked_responses.get(url, body=requests.ConnectionError(f"refused by {SECRET}"))
    assert search_fails_with(provider_key) == (
        f"Could not connect to {provider.NAME}. Check your internet connection."
    )


@pytest.mark.parametrize("provider_key", SEARCHES)
def test_a_429(mocked_responses, provider_key):
    provider, url, _ = SEARCHES[provider_key]
    mocked_responses.get(url, status=429, headers={"Retry-After": "30"}, body=SECRET)
    assert search_fails_with(provider_key) == (
        f"{provider.NAME} is rate-limiting requests (HTTP 429). The server asked to wait "
        "30 seconds. Openverse allows anonymous clients 20 requests per minute and 200 "
        "per day, so wait a minute and try again."
    )


def test_openverse_500_with_an_html_body(mocked_responses):
    mocked_responses.get(openverse.API_URL, status=500, body=HTML_BODY, content_type="text/html")
    assert search_fails_with("openverse") == (
        "Openverse Audio had a server error (HTTP 500). Try again later."
    )


NOT_FOUND = (
    "Poly Haven has nothing at that address (HTTP 404). "
    "If you entered an asset ID, check it and try again."
)


def test_polyhaven_404_on_search(mocked_responses):
    mocked_responses.get(f"{polyhaven.API_URL}/search", status=404, body=SECRET)
    assert search_fails_with("polyhaven") == NOT_FOUND


def test_polyhaven_404_on_an_assets_info(mocked_responses):
    mocked_responses.get(
        f"{polyhaven.API_URL}/search",
        json={"keywordMatches": 1, "results": [{"slug": "gone_asset", "score": 0.9}]},
    )
    mocked_responses.get(f"{polyhaven.API_URL}/info/gone_asset", status=404, body=SECRET)
    assert search_fails_with("polyhaven") == NOT_FOUND


def test_polyhaven_zero_keyword_matches_is_no_results_not_an_error(mocked_responses):
    mocked_responses.get(
        f"{polyhaven.API_URL}/search",
        json={"keywordMatches": 0, "results": [{"slug": "semantic_guess", "score": 0.3}]},
    )
    assert polyhaven.search_records("zzqqxx", "texture") == []


def test_each_failure_has_its_own_message(mocked_responses):
    """For one provider, no two failures read the same, so the user can tell them apart."""
    url = f"{polyhaven.API_URL}/search"
    fakes = [
        {"body": requests.Timeout()},
        {"body": requests.ConnectionError()},
        {"status": 429},
        {"status": 500, "body": HTML_BODY},
        {"status": 404},
    ]
    messages = set()
    for fake in fakes:
        mocked_responses.get(url, **fake)
        messages.add(search_fails_with("polyhaven"))
        mocked_responses.reset()
    assert len(messages) == len(fakes)
