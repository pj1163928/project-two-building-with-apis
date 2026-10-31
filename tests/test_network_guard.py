"""The autouse network guard fails any unmocked outbound request."""

import socket
import urllib.request

import pytest
import requests

from providers import ProviderError
from providers.http import get_json
from tests.conftest import NetworkBlockedError


def test_requests_call_is_blocked():
    with pytest.raises(NetworkBlockedError):
        requests.get("https://api.polyhaven.com/search", timeout=5)


def test_get_json_does_not_hide_the_block_as_a_provider_error():
    # If the guard's error were a requests exception, get_json() would turn
    # it into a friendly ProviderError and a test expecting that error could
    # pass while really hitting the network.
    with pytest.raises(NetworkBlockedError):
        get_json("https://ambientcg.com/api/v3/assets", {"q": "brick"}, provider="ambientCG")
    assert not issubclass(NetworkBlockedError, (ProviderError, requests.RequestException, OSError))


def test_urllib_call_is_blocked():
    with pytest.raises(NetworkBlockedError):
        urllib.request.urlopen("https://api.openverse.org/v1/audio/", timeout=5)


def test_raw_socket_connect_is_blocked():
    with socket.socket() as sock, pytest.raises(NetworkBlockedError):
        sock.connect(("93.184.215.14", 443))


def test_mocked_request_still_works(mocked_responses):
    mocked_responses.get("https://ambientcg.com/api/v3/assets", json={"assets": []})
    assert get_json("https://ambientcg.com/api/v3/assets", provider="ambientCG") == {"assets": []}


def test_guard_cannot_be_switched_off_by_a_marker(request):
    # The guard is autouse and has no opt-out marker; it is active here too.
    assert "_network_guard" in request.fixturenames
    assert socket.getaddrinfo.__name__ == "_blocked"
