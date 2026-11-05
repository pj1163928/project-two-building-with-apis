"""Template filters for the catalog's pages."""

from collections.abc import Mapping
from typing import Any

from django import template

register = template.Library()


@register.filter
def lookup(mapping: Mapping[str, Any] | None, key: str) -> Any:
    """`mapping[key]`, or None: e.g. a Discover result's community rating by its ID."""
    return (mapping or {}).get(key)
