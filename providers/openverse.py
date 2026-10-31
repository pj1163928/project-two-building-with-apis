"""Openverse Audio: Creative Commons sound and music (https://api.openverse.org/v1/).

Used anonymously, which Openverse caps at 20 requests/minute and 200/day.
"""

from .formatting import duration
from .http import get_json

NAME = "Openverse Audio"
API_URL = "https://api.openverse.org/v1/audio/"

# Openverse has no texture/HDRI/model split, so the type question is skipped.
TYPE_FILTERS = None


def license_label(code, version):
    """Turn Openverse's license code and version into e.g. "CC BY 4.0"."""
    if not code:
        return "unknown"
    if code == "cc0":
        return f"CC0 {version or ''}".strip()
    if code == "pdm":
        return "Public Domain Mark"
    return f"CC {code.upper()} {version or ''}".strip()


def search(query, asset_type=None, limit=5):
    """Return up to `limit` list rows for `query`, or [] when nothing matches."""
    data = get_json(API_URL, {"q": query.strip(), "page_size": limit}, provider=NAME)
    rows = []
    for item in data.get("results", []):
        rows.append({
            "id": item["id"],
            "name": item.get("title") or item["id"],
            "type": item.get("category") or "audio",
            "info": f"{duration(item.get('duration'))}, {item.get('filetype') or '?'}, "
                    f"by {item.get('creator') or 'unknown'}",
            "license": license_label(item.get("license"), item.get("license_version")),
        })
    return rows


def get_details(asset_id):
    """Return the full record for one Openverse audio ID (a UUID)."""
    item = get_json(f"{API_URL}{asset_id.strip()}/", provider=NAME)
    return {
        "id": item["id"],
        "name": item.get("title") or item["id"],
        "url": item.get("foreign_landing_url"),
        "audio_url": item.get("url"),
        "creator": item.get("creator"),
        "creator_url": item.get("creator_url"),
        "source": item.get("source") or item.get("provider"),
        "duration_ms": item.get("duration"),
        "bit_rate": item.get("bit_rate"),
        "sample_rate": item.get("sample_rate"),
        "filetype": item.get("filetype"),
        "filesize": item.get("filesize"),
        "alt_files": item.get("alt_files") or [],
        "license": license_label(item.get("license"), item.get("license_version")),
        "license_url": item.get("license_url"),
        "attribution": item.get("attribution"),
    }
