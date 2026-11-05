"""API clients for the game-asset providers.

Each provider module exposes, for the console script:
- NAME: display name
- TYPE_FILTERS: {"textures" | "hdris" | "models": provider value}, or None
- search(query, asset_type=None) -> list of rows (id, name, type, info, license)
- get_details(asset_id) -> dict of provider-specific details

and, for the Toolbox:
- KEY: a short stable identifier used in URLs and stored records
- KIND_FILTERS: {kind: the provider's filter value, or None}, one entry per
  kind the provider serves (the PRD's type-to-provider mapping)
- CREDIT, HOME_URL: the credit line on its Discover shelf, and its link
- search_records(query, kind, limit=12, page=1) -> list of AssetRecord
- fetch_record(external_id) -> one AssetRecord with its download variants

providers.cache lets the Toolbox install Django's cache for lookups such as
Poly Haven's /info. The console script installs none, so nothing is cached.
"""

import logging

from . import ambientcg, openverse, polyhaven
from .http import ProviderError
from .records import KINDS, AssetRecord

# Failure details are logged under "providers". The Toolbox's settings send
# them to the server console; the console script, which configures no
# logging, stays quiet rather than printing Python's last-resort warnings.
logging.getLogger(__name__).addHandler(logging.NullHandler())

PROVIDERS = [ambientcg, polyhaven, openverse]
PROVIDERS_BY_KEY = {provider.KEY: provider for provider in PROVIDERS}


def providers_for_kind(kind: str) -> list:
    """Return the provider modules that serve `kind`, in shelf order.

    The order is PROVIDERS' order; an unknown kind gets an empty list.
    """
    return [provider for provider in PROVIDERS if kind in provider.KIND_FILTERS]


__all__ = [
    "KINDS",
    "PROVIDERS",
    "PROVIDERS_BY_KEY",
    "AssetRecord",
    "ProviderError",
    "ambientcg",
    "openverse",
    "polyhaven",
    "providers_for_kind",
]
