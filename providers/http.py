"""Shared HTTP helper. Every provider request goes through get_json()."""

import logging

import requests

logger = logging.getLogger(__name__)

# Poly Haven's API terms require a User-Agent that identifies the app.
USER_AGENT = "AssetLibrary-CIDM3312/0.1"
TIMEOUT_SECONDS = 10

# How much of an unexpected response body goes into the server log.
_LOGGED_BODY_CHARS = 300


class ProviderError(Exception):
    """A failed provider request, with a message that is safe to show the user.

    The message never carries exception text or response content. Those
    details go to the server log (the `providers` logger) instead.
    """


def _snippet(response):
    return response.text[:_LOGGED_BODY_CHARS].replace("\n", " ")


def get_json(url, params=None, provider="The provider"):
    """GET a URL and return the decoded JSON body.

    Any failure (network, HTTP status, or a body that isn't JSON) is raised
    as a single ProviderError with a friendly message, and its details are
    logged as a warning.
    """
    try:
        response = requests.get(
            url,
            params=params,
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT_SECONDS,
        )
    except requests.Timeout as exc:
        logger.warning("%s timed out: GET %s params=%s (%r)", provider, url, params, exc)
        raise ProviderError(
            f"{provider} did not respond within {TIMEOUT_SECONDS} seconds. Try again in a moment."
        ) from None
    except requests.ConnectionError as exc:
        logger.warning("%s connection failed: GET %s params=%s (%r)", provider, url, params, exc)
        raise ProviderError(
            f"Could not connect to {provider}. Check your internet connection."
        ) from None
    except requests.RequestException as exc:
        logger.warning("%s request failed: GET %s params=%s (%r)", provider, url, params, exc)
        raise ProviderError(f"The request to {provider} failed. Try again in a moment.") from None

    status = response.status_code
    if status >= 400:
        logger.warning(
            "%s answered HTTP %s: GET %s body=%r",
            provider,
            status,
            response.url,
            _snippet(response),
        )
    if status == 429:
        wait = response.headers.get("Retry-After")
        hint = f" The server asked to wait {wait} seconds." if wait and wait.isdigit() else ""
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
        logger.warning(
            "%s sent a non-JSON body (HTTP %s): GET %s body=%r",
            provider,
            status,
            response.url,
            _snippet(response),
        )
        raise ProviderError(
            f"{provider} sent back a response that isn't JSON (HTTP {status})."
        ) from None
