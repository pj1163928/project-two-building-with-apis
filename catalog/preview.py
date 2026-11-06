"""A Discover result in full, for Discover's drawer (user request, 2026-11-06).

Opening a result shows it in a drawer, as the library does, before anything is
saved. The drawer reads the Toolbox's stored Asset when any member has saved
it (no provider request), and otherwise the provider's fetch_record(), cached
for an hour like a search. Nothing is stored: saving is still Save to library.
"""

import hashlib
from dataclasses import dataclass

from django.core.cache import cache

from providers import PROVIDERS_BY_KEY, AssetRecord

from .discover import TILES_BY_KIND, KindTile
from .files import VariantInfo, describe_variants
from .licenses import LicenseInfo, license_info
from .models import KIND_LABELS, Asset

# How long a fetched record is reused, the same hour as a search.
PREVIEW_CACHE_SECONDS = 60 * 60
# The longest ID Save to library accepts; the drawer refuses the same.
MAX_EXTERNAL_ID_LENGTH = 200


@dataclass(frozen=True)
class AssetPreview:
    """One provider asset as the drawer shows it, from a stored Asset or a record."""

    provider: str
    external_id: str
    kind: str
    title: str
    author: str
    thumbnail_url: str
    license: str
    license_url: str
    attribution: str
    source_url: str
    tags: tuple[str, ...]
    preview_url: str
    variants: tuple[VariantInfo, ...]

    @property
    def provider_name(self) -> str:
        return PROVIDERS_BY_KEY[self.provider].NAME

    @property
    def kind_label(self) -> str:
        """The type in the singular: "Texture", "HDRI", "Model" or "Sound"."""
        return KIND_LABELS[self.kind]

    @property
    def tile(self) -> KindTile:
        return TILES_BY_KIND[self.kind]

    @property
    def license_info(self) -> LicenseInfo:
        return license_info(self.license)

    @property
    def file_count(self) -> int:
        """How many files its largest variant holds (a bundle's maps, or one)."""
        return max((len(variant.files) for variant in self.variants), default=0)


def _from_asset(asset: Asset) -> AssetPreview:
    return AssetPreview(
        provider=asset.provider,
        external_id=asset.external_id,
        kind=asset.kind,
        title=asset.title,
        author=asset.author,
        thumbnail_url=asset.thumbnail_url,
        license=asset.license,
        license_url=asset.license_url,
        attribution=asset.attribution,
        source_url=asset.source_url,
        tags=tuple(tag.name for tag in asset.tags.all()),
        preview_url=asset.preview_url,
        variants=tuple(asset.file_variants),
    )


def _from_record(record: AssetRecord) -> AssetPreview:
    stored = [variant.as_dict() for variant in record.variants]
    return AssetPreview(
        provider=record.provider,
        external_id=record.external_id,
        kind=record.kind,
        title=record.title,
        author=record.author,
        thumbnail_url=record.thumbnail_url,
        license=record.license,
        license_url=record.license_url,
        attribution=record.attribution,
        source_url=record.source_url,
        tags=record.tags,
        preview_url=record.preview_url,
        variants=tuple(describe_variants(stored, record.external_id)),
    )


def preview_cache_key(provider_key: str, external_id: str) -> str:
    """The cache key for one fetched record; the ID is hashed, so no user text is in it."""
    digest = hashlib.sha256(external_id.encode()).hexdigest()
    return f"discover:record:{provider_key}:{digest}"


def valid_asset_ref(provider_key: str, external_id: str) -> bool:
    """Whether a provider and ID could name an asset: Save to library's rule."""
    return (
        provider_key in PROVIDERS_BY_KEY
        and bool(external_id)
        and len(external_id) <= MAX_EXTERNAL_ID_LENGTH
    )


def asset_preview(provider_key: str, external_id: str) -> AssetPreview:
    """One provider asset in full, for Discover's drawer.

    The stored Asset when anyone has saved it, so no provider is asked;
    otherwise the provider's fetch_record(), cached for PREVIEW_CACHE_SECONDS.
    Check valid_asset_ref() first. Lets ProviderError through (its message is
    safe to show), and stores nothing either way.
    """
    asset = (
        Asset.objects.filter(provider=provider_key, external_id=external_id)
        .prefetch_related("tags")
        .first()
    )
    if asset is not None:
        return _from_asset(asset)
    key = preview_cache_key(provider_key, external_id)
    record = cache.get(key)
    if record is None:
        record = PROVIDERS_BY_KEY[provider_key].fetch_record(external_id)
        cache.set(key, record, PREVIEW_CACHE_SECONDS)
    return _from_record(record)
