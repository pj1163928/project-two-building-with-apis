"""Shared HTTP helper. Every provider request goes through get_json()."""

import requests

# Poly Haven's API terms require a User-Agent that identifies the app.
USER_AGENT = "AssetLibrary-CIDM3312/0.1"
TIMEOUT_SECONDS = 10


class ProviderError(Exception):
    """A failed provider request, with a message that is safe to show the user."""


def get_json(url, params=None, provider="The provider"):
    """GET a URL and return the decoded JSON body.

    Any failure (network, HTTP status, or a body that isn't JSON) is raised
    as a single ProviderError with a friendly message.
    """
    try:
        response = requests.get(
            url,
            params=params,
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT_SECONDS,
        )
    except requests.Timeout:
        raise ProviderError(
            f"{provider} did not respond within {TIMEOUT_SECONDS} seconds. Try again in a moment."
        ) from None
    except requests.ConnectionError:
        raise ProviderError(
            f"Could not connect to {provider}. Check your internet connection."
        ) from None
    except requests.RequestException as exc:
        raise ProviderError(f"The request to {provider} failed: {exc}") from None

    status = response.status_code
    if status == 429:
        wait = response.headers.get("Retry-After")
        hint = f" The server asked to wait {wait} seconds." if wait else ""
        raise ProviderError(
            f"{provider} is rate-limiting requests (HTTP 429).{hint} "
            "Openverse allows anonymous clients 20 requests per minute and "
            "200 per day, so wait a minute and try again."
        )
    if status == 404:
        raise ProviderError(
            f"{provider} has nothing at that address (HTTP 404). "
            "If you entered an asset ID, check it and try again."
        )
    if status >= 500:
        raise ProviderError(f"{provider} had a server error (HTTP {status}). Try again later.")
    if status >= 400:
        raise ProviderError(f"{provider} rejected the request (HTTP {status}).")

    try:
        return response.json()
    except ValueError:
        raise ProviderError(
            f"{provider} sent back a response that isn't JSON (HTTP {status})."
        ) from None
