"""ambientCG: CC0 PBR materials, HDRIs and 3D models (https://docs.ambientcg.com/api/v3/)."""

from .http import ProviderError, get_json

NAME = "ambientCG"
API_URL = "https://ambientcg.com/api/v3/assets"
LICENSE = "CC0"

# The script's type choices mapped to ambientCG's `type` filter.
TYPE_FILTERS = {"textures": "material", "hdris": "hdri", "models": "3d-model"}

_INCLUDE = "title,url,tags,type,maps,dimensions,downloads"


def _row(asset):
    maps = asset.get("maps") or []
    downloads = asset.get("downloads") or []
    info = f"{len(downloads)} downloads"
    if maps:
        info = f"{len(maps)} maps, {info}"
    return {
        "id": asset["id"],
        "name": asset.get("title") or asset["id"],
        "type": asset.get("type") or "unknown",
        "info": info,
        "license": LICENSE,
    }


def search(query, asset_type=None, limit=5):
    """Return up to `limit` list rows for `query`, or [] when nothing matches."""
    params = {"q": query.strip(), "limit": limit, "include": _INCLUDE}
    if asset_type:
        params["type"] = TYPE_FILTERS[asset_type]
    data = get_json(API_URL, params, provider=NAME)
    return [_row(asset) for asset in data.get("assets", [])]


def get_details(asset_id):
    """Return the full asset record for one ambientCG asset ID."""
    data = get_json(API_URL, {"id": asset_id.strip(), "include": _INCLUDE}, provider=NAME)
    assets = data.get("assets") or []
    if not assets:
        # ambientCG answers an unknown ID with 200 and an empty list, not 404.
        raise ProviderError(f"ambientCG has no asset with ID '{asset_id}'.")
    asset = assets[0]
    return {
        "id": asset["id"],
        "name": asset.get("title") or asset["id"],
        "type": asset.get("type") or "unknown",
        "url": asset.get("url"),
        "tags": asset.get("tags") or [],
        "maps": asset.get("maps") or [],
        "dimensions": asset.get("dimensions") or {},
        "downloads": asset.get("downloads") or [],
        "license": LICENSE,
    }
