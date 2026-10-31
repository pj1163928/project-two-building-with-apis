"""API clients for the game-asset providers.

Each provider module exposes:
- NAME: display name
- TYPE_FILTERS: {"textures" | "hdris" | "models": provider value}, or None
- search(query, asset_type=None) -> list of rows (id, name, type, info, license)
- get_details(asset_id) -> dict of provider-specific details
"""

from . import ambientcg, openverse, polyhaven
from .http import ProviderError

PROVIDERS = [ambientcg, polyhaven, openverse]

__all__ = ["PROVIDERS", "ProviderError", "ambientcg", "openverse", "polyhaven"]
