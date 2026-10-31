"""Poly Haven: CC0 textures, HDRIs and models (https://api.polyhaven.com)."""

import re
from collections import defaultdict

from .http import get_json

NAME = "Poly Haven"
API_URL = "https://api.polyhaven.com"
LICENSE = "CC0"

# The script's type choices mapped to Poly Haven's `t` filter.
TYPE_FILTERS = {"textures": "textures", "hdris": "hdris", "models": "models"}

# /info reports the asset type as a number.
TYPE_NAMES = {0: "hdri", 1: "texture", 2: "model"}

# Resolution keys in /files look like "1k", "8k" or "16k".
_RESOLUTION = re.compile(r"^\d+k$")


def _info(slug):
    return get_json(f"{API_URL}/info/{slug}", provider=NAME)


def _resolution_text(info):
    width, height = info.get("max_resolution") or (None, None)
    return f"{width}x{height}" if width else "unknown"


def _physical_size(info):
    """Format `dimensions` (millimetres) as metres, e.g. "2.5 x 2.5 m"."""
    dims = info.get("dimensions")
    if not dims:
        return None
    return " x ".join(f"{mm / 1000:.2f}".rstrip("0").rstrip(".") for mm in dims) + " m"


def search(query, asset_type=None, limit=5):
    """Return up to `limit` list rows for `query`, or [] when nothing matches."""
    params = {"q": query.strip().lower(), "limit": limit}
    if asset_type:
        params["t"] = TYPE_FILTERS[asset_type]
    data = get_json(f"{API_URL}/search", params, provider=NAME)

    # The semantic search always returns something (even for "zzqqxx"), so
    # only trust it when at least one asset matched the keywords.
    if not data.get("keywordMatches"):
        return []

    # /search returns only slugs and scores, so fetch /info for each row.
    rows = []
    for hit in data.get("results", [])[:limit]:
        info = _info(hit["slug"])
        details = [f"max {_resolution_text(info)}"]
        if size := _physical_size(info):
            details.append(size)
        rows.append(
            {
                "id": hit["slug"],
                "name": info.get("name") or hit["slug"],
                "type": TYPE_NAMES.get(info.get("type"), "unknown"),
                "info": ", ".join(details),
                "license": LICENSE,
            }
        )
    return rows


def _summarize_files(files):
    """Total the /files tree by resolution and format.

    Returns (maps, bundles):
    - maps: {resolution: {format: total bytes}} for the loose map files
    - bundles: {kind: {resolution: total bytes}} for blend/gltf/fbx/usd/mtlx
      packages, counting the bundle file plus every file it includes
    """
    maps = defaultdict(lambda: defaultdict(int))
    bundles = defaultdict(dict)
    for by_resolution in files.values():
        if not isinstance(by_resolution, dict):
            continue
        for resolution, by_format in by_resolution.items():
            if not _RESOLUTION.match(resolution) or not isinstance(by_format, dict):
                continue
            for fmt, entry in by_format.items():
                if not isinstance(entry, dict) or "size" not in entry:
                    continue
                if "include" in entry:
                    included = sum(f.get("size", 0) for f in entry["include"].values())
                    bundles[fmt][resolution] = entry["size"] + included
                else:
                    maps[resolution][fmt] += entry["size"]
    return maps, bundles


def get_details(asset_id):
    """Return info plus a summarized file list for one Poly Haven slug."""
    slug = asset_id.strip()
    info = _info(slug)
    maps, bundles = _summarize_files(get_json(f"{API_URL}/files/{slug}", provider=NAME))
    return {
        "id": slug,
        "name": info.get("name") or slug,
        "type": TYPE_NAMES.get(info.get("type"), "unknown"),
        "url": f"https://polyhaven.com/a/{slug}",
        "max_resolution": _resolution_text(info),
        "physical_size": _physical_size(info),
        "authors": info.get("authors") or {},
        "categories": info.get("categories") or [],
        "tags": info.get("tags") or [],
        "download_count": info.get("download_count"),
        "description": info.get("description"),
        "maps": maps,
        "bundles": bundles,
        "license": LICENSE,
    }
