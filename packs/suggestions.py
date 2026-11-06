"""Suggested for this pack, and Find more from providers (Phase 10).

Suggestions are stored Assets (the shared cache of provider data) ranked by
how many tags they share with the pack. They read only Asset and Tag rows,
never anyone's library entry, so no member's notes, rating or status (or
who saved what) can reach them.
"""

from collections import Counter
from dataclasses import dataclass

from django.db.models import Count, Q
from django.db.models.functions import Lower

from catalog.discover import discover_url
from catalog.library import FIND_MORE_TAGS
from catalog.models import Asset, Tag
from providers import KINDS

from .models import Pack

# How many suggestions the builder shows.
SUGGESTION_LIMIT = 8


def suggest_assets(pack: Pack, limit: int = SUGGESTION_LIMIT) -> list[Asset]:
    """Up to `limit` stored Assets sharing tags with `pack`, each with `shared_tags`.

    Most shared tags first; equal counts go by title A–Z (case ignored),
    then by id, so the order is stable. Assets sharing no tag, and assets
    already in the pack, are left out. Only Asset and Tag rows are read:
    the suggestions are the same whoever saved the assets.
    """
    tag_ids = pack.tags.values("pk")
    in_pack = pack.items.values("saved_asset__asset")
    suggestions = (
        Asset.objects.exclude(pk__in=in_pack)
        .annotate(shared_tags=Count("tags", filter=Q(tags__in=tag_ids), distinct=True))
        .filter(shared_tags__gt=0)
        .order_by("-shared_tags", Lower("title"), "pk")
    )
    return list(suggestions[:limit])


@dataclass(frozen=True)
class FindMore:
    """Find more from providers: a Discover search built from the pack's tags."""

    kind: str
    query: str
    url: str


def find_more(pack: Pack) -> FindMore | None:
    """Discover for the pack's main type, searching up to FIND_MORE_TAGS of its tags.

    The tags most stored assets carry come first (then A–Z), so the search
    leans on words the providers use, as the entry page's Find more does.
    The type is the one most of the pack's items have (ties in Discover's
    order), or textures for an empty pack. None when the pack has no tags,
    so the builder shows a hint instead of an empty search.
    """
    # Counted over every asset, not through pack.tags (whose join would skew the count).
    tags = list(
        Tag.objects.filter(pk__in=pack.tags.values("pk"))
        .annotate(assets_using=Count("assets"))
        .order_by("-assets_using", "name")
        .values_list("name", flat=True)[:FIND_MORE_TAGS]
    )
    if not tags:
        return None
    kinds = Counter(pack.items.values_list("saved_asset__asset__kind", flat=True))
    kind = sorted(KINDS, key=lambda key: -kinds[key])[0]  # a stable sort keeps Discover's order
    query = " ".join(tags)
    return FindMore(kind=kind, query=query, url=discover_url(kind, query))
