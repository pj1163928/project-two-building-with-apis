"""The library's cross-model workflows: saving a provider asset for a member.

Saving touches both models: the shared Asset (created from the provider on
the first save by anyone, reused after that) and the member's own
SavedAsset.
"""

from django.db import transaction

from providers import PROVIDERS_BY_KEY

from .models import Asset, SavedAsset


class UnknownProviderError(LookupError):
    """A save named a provider the Toolbox doesn't have."""


def get_or_fetch_asset(provider_key: str, external_id: str) -> Asset:
    """The shared Asset for one provider asset, fetching and storing it the first time.

    A stored Asset is reused without contacting the provider. Otherwise the
    provider's fetch_record() is called once. Raises UnknownProviderError for
    an unknown provider, and lets ProviderError through, in which case
    nothing is stored.
    """
    provider = PROVIDERS_BY_KEY.get(provider_key)
    if provider is None:
        raise UnknownProviderError(provider_key)
    external_id = external_id.strip()
    asset = Asset.objects.filter(provider=provider.KEY, external_id=external_id).first()
    if asset is None:
        asset = Asset.objects.from_record(provider.fetch_record(external_id))
    return asset


def save_to_library(user, provider_key: str, external_id: str) -> tuple[SavedAsset, bool]:
    """Save one provider asset to `user`'s library; return (entry, created).

    The shared Asset comes from get_or_fetch_asset(). A member who already
    has the asset gets their existing entry back with created=False, never a
    second one. A new entry starts as To review with no rating. Raises
    UnknownProviderError or ProviderError, and then saves nothing.
    """
    asset = get_or_fetch_asset(provider_key, external_id)
    with transaction.atomic():
        return SavedAsset.objects.get_or_create(user=user, asset=asset)
