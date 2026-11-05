"""Poly Haven: CC0 textures, HDRIs and models (https://api.polyhaven.com)."""

import re
from collections import defaultdict

from .cache import remember
from .http import get_json
from .records import CC0_LICENSE, CC0_URL, AssetRecord, items_in, tag_names, text

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


# ---------------------------------------------------------------- Toolbox records
# New code for the Toolbox. The console's search() and get_details() above stay as they are.

KEY = "polyhaven"
# The credit line on its Discover shelf, and where it links.
CREDIT = "Powered by Poly Haven"
HOME_URL = "https://polyhaven.com"

# The Toolbox's kinds mapped to Poly Haven's `t` filter (the PRD's mapping).
KIND_FILTERS = {"texture": "textures", "hdri": "hdris", "model": "models"}

# How long an asset's /info answer is reused (the PRD: 12 hours).
INFO_CACHE_SECONDS = 12 * 60 * 60


def _cached_info(slug):
    """/info for one slug, reused for INFO_CACHE_SECONDS. Every Toolbox lookup uses this."""
    return remember(f"polyhaven:info:{slug}", INFO_CACHE_SECONDS, lambda: _info(slug))


def _authors(info):
    authors = info.get("authors")
    if not isinstance(authors, dict):
        return ""
    return ", ".join(name for name in map(text, authors) if name)


def _record(slug, info, kind):
    title = text(info.get("name")) or slug
    author = _authors(info) or NAME
    return AssetRecord(
        provider=KEY,
        external_id=slug,
        kind=kind,
        title=title,
        author=author,
        thumbnail_url=text(info.get("thumbnail_url")),
        license=CC0_LICENSE,
        license_url=CC0_URL,
        attribution=f'"{title}" by {author}, from {NAME}, CC0 1.0',
        source_url=f"https://polyhaven.com/a/{slug}",
        tags=tag_names(info.get("tags")),
    )


def search_records(query: str, kind: str, limit: int = 12, page: int = 1) -> list[AssetRecord]:
    """Return up to `limit` AssetRecords of `kind` matching `query`, from page `page`.

    /search has no offset, so page N asks for N * `limit` hits and keeps the
    last `limit`. Each kept hit needs its /info, which is cached for
    INFO_CACHE_SECONDS; no /info is fetched for a hit that won't be shown.
    Zero keyword matches means no results (the semantic search never comes
    back empty), and pages after the first stop at the keyword matches, so
    Load more never wanders into unrelated guesses. Any failure raises
    ProviderError.
    """
    if kind not in KIND_FILTERS:
        raise ValueError(f"{NAME} has no {kind!r} assets.")
    start = (page - 1) * limit
    params = {"q": query.strip().lower(), "t": KIND_FILTERS[kind], "limit": start + limit}
    data = get_json(f"{API_URL}/search", params, provider=NAME)
    hits = items_in(data, "results", NAME)
    matches = data.get("keywordMatches")
    if not matches or (page > 1 and not (isinstance(matches, int) and matches > start)):
        return []

    slugs = [slug for slug in (text(hit.get("slug")) for hit in hits) if slug]
    slugs = slugs[start : start + limit]
    records = []
    for slug in slugs:
        info = _cached_info(slug)
        if isinstance(info, dict):
            records.append(_record(slug, info, kind))
    return records
