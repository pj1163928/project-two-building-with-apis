"""Shared fixtures for the whole test suite (see docs/TESTING.md).

Two fixtures run for every test:
- the cache is cleared before and after, so cached provider results never
  leak between tests
- the network guard makes any unmocked outbound connection fail the test
"""

import socket

import pytest
import responses
from django.core.cache import cache


class NetworkBlockedError(RuntimeError):
    """Raised when a test tries to reach the real network.

    It is deliberately not an OSError or a requests exception, so neither
    requests nor get_json() can turn it into a friendly ProviderError: it
    always escapes and fails the test.
    """


def _blocked(*args, **kwargs):
    raise NetworkBlockedError(
        "A test tried to reach the network. Mock provider HTTP with `responses`, "
        "or replace provider functions with `monkeypatch`."
    )


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def _network_guard(monkeypatch):
    # DNS lookup and socket connect are where every HTTP client (requests,
    # urllib, http.client) first touches the network. `responses` answers
    # before either is reached, so mocked requests are unaffected.
    monkeypatch.setattr(socket, "getaddrinfo", _blocked)
    monkeypatch.setattr(socket.socket, "connect", _blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", _blocked)


@pytest.fixture(autouse=True)
def _fast_password_hashing(settings):
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


@pytest.fixture
def mocked_responses():
    """A `responses` mock that also fails the test if a registered URL goes unused."""
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        yield rsps


@pytest.fixture
def password():
    return "demo-Passw0rd-not-secret"


@pytest.fixture
def member(django_user_model, password):
    return django_user_model.objects.create_user(username="demo_member", password=password)


@pytest.fixture
def member_client(client, member):
    client.force_login(member)
    return client
