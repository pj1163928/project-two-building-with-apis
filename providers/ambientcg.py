"""ambientCG: CC0 PBR materials, HDRIs and 3D models (https://docs.ambientcg.com/api/v3/)."""

from dataclasses import replace

from .http import ProviderError, get_json
from .records import (
    CC0_LICENSE,
    CC0_URL,
    AssetRecord,
    Variant,
    VariantFile,
    byte_size,
    file_name,
    items_in,
    tag_names,
    text,
)

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


# ---------------------------------------------------------------- Toolbox records
# New code for the Toolbox. The console's search() and get_details() above stay as they are.

KEY = "ambientcg"
# The credit line on its Discover shelf, and where it links.
CREDIT = "Assets from ambientCG · CC0"
HOME_URL = "https://ambientcg.com"

# The Toolbox's kinds mapped to ambientCG's `type` filter (the PRD's mapping).
KIND_FILTERS = {"texture": "material", "hdri": "hdri", "model": "3d-model"}
# Every ambientCG asset is CC0, so Discover's license filters need no request to rule it in or out.
LICENSES = ("cc0",)

_RECORD_INCLUDE = "title,url,tags,type,thumbnails"
# Thumbnail sizes in order of preference: big enough for a card, small to load.
_THUMBNAIL_SIZES = ("256-PNG", "256-JPG", "512-PNG", "512-JPG", "128-PNG", "128-JPG")


def _thumbnail(thumbnails):
    if not isinstance(thumbnails, dict):
        return ""
    for size in _THUMBNAIL_SIZES:
        if url := text(thumbnails.get(size)):
            return url
    return next((url for url in map(text, thumbnails.values()) if url), "")


def _record(asset, kind):
    external_id = text(asset.get("id"))
    if not external_id:
        return None
    title = text(asset.get("title")) or external_id
    return AssetRecord(
        provider=KEY,
        external_id=external_id,
        kind=kind,
        title=title,
        # ambientCG publishes its own work and names no per-asset author.
        author=NAME,
        thumbnail_url=_thumbnail(asset.get("thumbnails")),
        license=CC0_LICENSE,
        license_url=CC0_URL,
        attribution=f'"{title}" from {NAME}, CC0 1.0',
        source_url=text(asset.get("url")) or f"https://ambientcg.com/a/{external_id}",
        tags=tag_names(asset.get("tags")),
    )


def search_records(query: str, kind: str, limit: int = 12, page: int = 1) -> list[AssetRecord]:
    """Return up to `limit` AssetRecords of `kind` matching `query`, from page `page`.

    Pages are 1-based and `limit` long (ambientCG's `offset`). `kind` must be
    one of KIND_FILTERS. Any failure raises ProviderError.
    """
    if kind not in KIND_FILTERS:
        raise ValueError(f"{NAME} has no {kind!r} assets.")
    params = {
        "q": query.strip(),
        "type": KIND_FILTERS[kind],
        "limit": limit,
        "include": _RECORD_INCLUDE,
    }
    if page > 1:
        params["offset"] = (page - 1) * limit
    data = get_json(API_URL, params, provider=NAME)
    records = (_record(asset, kind) for asset in items_in(data, "assets", NAME))
    return [record for record in records if record][:limit]


# What fetch_record() asks for: the search fields plus every download.
_DETAIL_INCLUDE = "title,url,tags,type,thumbnails,downloads"
# ambientCG's `type` back to the Toolbox's kinds.
_KINDS_BY_TYPE = {value: kind for kind, value in KIND_FILTERS.items()}


def _variants(asset):
    """One variant per download (each is a single zip), labelled e.g. "2K JPG"."""
    downloads = asset.get("downloads")
    variants = []
    for download in downloads if isinstance(downloads, list) else []:
        if not isinstance(download, dict) or not (url := text(download.get("url"))):
            continue
        attributes = text(download.get("attributes"))
        extension = text(download.get("extension")) or "zip"
        fallback = f"{text(asset.get('id'))}_{attributes or 'download'}.{extension}"
        variants.append(
            Variant(
                label=attributes.replace("-", " ") or "Download",
                files=(
                    VariantFile(url, file_name(url, fallback), byte_size(download.get("size"))),
                ),
            )
        )
    return tuple(variants)


def fetch_record(external_id: str) -> AssetRecord:
    """Return the full AssetRecord for one ambientCG asset ID, with its variants.

    Any failure raises ProviderError, including an unknown ID (ambientCG
    answers that with an empty list) and an asset of a type the Toolbox
    doesn't hold.
    """
    asset_id = external_id.strip()
    data = get_json(API_URL, {"id": asset_id, "include": _DETAIL_INCLUDE}, provider=NAME)
    assets = items_in(data, "assets", NAME)
    if not assets:
        raise ProviderError(f"{NAME} has no asset with that ID.")
    asset = assets[0]
    kind = _KINDS_BY_TYPE.get(text(asset.get("type")))
    record = _record(asset, kind) if kind else None
    if record is None:
        raise ProviderError(f"{NAME} sent back an asset the Toolbox can't save.")
    return replace(record, variants=_variants(asset))
