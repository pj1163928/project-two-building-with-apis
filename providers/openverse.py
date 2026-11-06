"""Openverse Audio: Creative Commons sound and music (https://api.openverse.org/v1/).

Used anonymously, which Openverse caps at 20 requests/minute and 200/day.
"""

import re
from collections.abc import Sequence
from dataclasses import replace

from .formatting import duration
from .http import ProviderError, get_json
from .records import (
    AssetRecord,
    Variant,
    VariantFile,
    byte_size,
    file_name,
    items_in,
    tag_names,
    text,
)

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
        rows.append(
            {
                "id": item["id"],
                "name": item.get("title") or item["id"],
                "type": item.get("category") or "audio",
                "info": f"{duration(item.get('duration'))}, {item.get('filetype') or '?'}, "
                f"by {item.get('creator') or 'unknown'}",
                "license": license_label(item.get("license"), item.get("license_version")),
            }
        )
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


# ---------------------------------------------------------------- Toolbox records
# New code for the Toolbox. The console's search() and get_details() above stay as they are.

KEY = "openverse"
# The credit line on its Discover shelf, and where it links.
CREDIT = "Made with Openverse"
HOME_URL = "https://openverse.org"

# Openverse serves sounds only, with no type filter (the PRD's mapping).
KIND_FILTERS = {"sound": None}
# Openverse's licenses are mixed, so None: search_records() filters by license itself.
LICENSES = None

# Anonymous clients may page no deeper than this many results.
MAX_DEPTH = 240


def _record(item):
    external_id = text(item.get("id"))
    if not external_id:
        return None
    title = text(item.get("title")) or external_id
    return AssetRecord(
        provider=KEY,
        external_id=external_id,
        kind="sound",
        title=title,
        author=text(item.get("creator")) or "unknown",
        thumbnail_url=text(item.get("thumbnail")),
        license=license_label(item.get("license"), item.get("license_version")),
        license_url=text(item.get("license_url")),
        attribution=text(item.get("attribution")),
        source_url=text(item.get("foreign_landing_url")),
        tags=tag_names(item.get("tags")),
        preview_url=text(item.get("url")),
    )


def search_records(
    query: str, kind: str, limit: int = 12, page: int = 1, licenses: Sequence[str] = ()
) -> list[AssetRecord]:
    """Return up to `limit` sound AssetRecords matching `query`, from page `page`.

    Pages are 1-based. A page past MAX_DEPTH is empty, with no request, since
    Openverse refuses it. `kind` must be "sound". `licenses` (the Toolbox's
    license keys, which are Openverse's own codes: "cc0", "by", "by-nc-sa",
    "sampling+"...) limits the results to those licenses; empty means any.
    Any failure raises ProviderError.
    """
    if kind not in KIND_FILTERS:
        raise ValueError(f"{NAME} has no {kind!r} assets.")
    if (page - 1) * limit >= MAX_DEPTH:
        return []
    params = {"q": query.strip(), "page_size": limit}
    if page > 1:
        params["page"] = page
    if licenses:
        params["license"] = ",".join(licenses)
    data = get_json(API_URL, params, provider=NAME)
    records = (_record(item) for item in items_in(data, "results", NAME))
    return [record for record in records if record][:limit]


# An Openverse ID (a UUID): letters, digits and hyphens, so it's safe in a URL path.
_ID = re.compile(r"^[\w-]+$")


def _variant(entry, external_id):
    """One audio file as a variant labelled by its type. A URL with no file name
    (Freesound's download links) gets "<id>.<type>"."""
    url = text(entry.get("url"))
    if not url:
        return None
    filetype = text(entry.get("filetype")).lower()
    fallback = f"{external_id}.{filetype or 'audio'}"
    return Variant(
        filetype.upper() or "Audio",
        (VariantFile(url, file_name(url, fallback), byte_size(entry.get("filesize"))),),
    )


def _variants(item, external_id):
    """The main audio file, then each alternative file, one variant per file type."""
    alternatives = item.get("alt_files")
    entries = [item, *(alternatives if isinstance(alternatives, list) else [])]
    variants = {}
    for entry in entries:
        if isinstance(entry, dict) and (variant := _variant(entry, external_id)):
            variants.setdefault(variant.label, variant)
    return tuple(variants.values())


def fetch_record(external_id: str) -> AssetRecord:
    """Return the full AssetRecord for one Openverse audio ID, with its variants.

    Any failure raises ProviderError, including an unknown ID (HTTP 404).
    """
    audio_id = external_id.strip()
    if not _ID.match(audio_id):
        raise ProviderError(f"{NAME} has no sound with that ID.")
    item = get_json(f"{API_URL}{audio_id}/", provider=NAME)
    record = _record(item) if isinstance(item, dict) else None
    if record is None:
        raise ProviderError(f"{NAME} sent back results the Toolbox couldn't read.")
    return replace(record, variants=_variants(item, record.external_id))
