"""Template filters for the catalog's pages."""

from collections.abc import Mapping
from typing import Any

from django import template

from catalog import licenses
from catalog.licenses import LicenseInfo

register = template.Library()


@register.filter
def lookup(mapping: Mapping[str, Any] | None, key: str) -> Any:
    """`mapping[key]`, or None: e.g. a Discover result's community rating by its ID."""
    return (mapping or {}).get(key)


@register.filter
def license_info(name: str) -> LicenseInfo:
    """What a license, as a provider wrote it, means (catalog.licenses): e.g. a
    Discover result's symbols and whether it allows commercial use."""
    return licenses.license_info(name or "")
