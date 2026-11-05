"""The provider-neutral asset record the Toolbox works with.

Each provider's `search_records()` turns its own API's JSON into these, so
Discover (and later the library) never needs to know a response shape.
"""

from dataclasses import dataclass

from .http import ProviderError

# The four asset kinds, in the order Discover shows them.
KINDS = ("texture", "hdri", "model", "sound")

CC0_LICENSE = "CC0"
CC0_URL = "https://creativecommons.org/publicdomain/zero/1.0/"


@dataclass(frozen=True)
class AssetRecord:
    """One asset as a provider describes it, ready to show or save."""

    provider: str  # the provider module's KEY, e.g. "polyhaven"
    external_id: str  # the provider's own ID or slug
    kind: str  # one of KINDS
    title: str
    author: str
    thumbnail_url: str  # the provider's URL; never downloaded or copied
    license: str  # e.g. "CC0" or "CC BY 4.0"
    license_url: str
    attribution: str
    source_url: str  # the asset's page on the provider's site
    tags: tuple[str, ...] = ()


def items_in(data: object, key: str, provider: str) -> list[dict]:
    """Return the list of result objects under `key` in a decoded response.

    A body that isn't the expected shape becomes a ProviderError with a safe
    message, and any entry that isn't an object is dropped, so a provider's
    malformed answer can never crash a page.
    """
    items = data.get(key, []) if isinstance(data, dict) else None
    if not isinstance(items, list):
        raise ProviderError(f"{provider} sent back results the Toolbox couldn't read.")
    return [item for item in items if isinstance(item, dict)]


def text(value: object) -> str:
    """A provider value as display text: strings are trimmed, anything else is ''."""
    return value.strip() if isinstance(value, str) else ""


def tag_names(values: object) -> tuple[str, ...]:
    """Provider tags as a tuple of non-blank strings (normalising comes in Phase 3)."""
    if not isinstance(values, list):
        return ()
    names = (value.get("name") if isinstance(value, dict) else value for value in values)
    return tuple(name for name in map(text, names) if name)
