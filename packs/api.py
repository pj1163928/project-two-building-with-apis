"""The pack API: /api/packs/, /api/packs/<id>/ and /api/packs/<id>/export/.

Read-only. Packs are made and changed on the website only, so POST, PUT,
PATCH and DELETE are a 405. Anyone may read public packs, signed in or not;
a private pack is the owner's alone, a 404 to everyone else (packs are read
through Pack.objects.visible_to()). Sign-in is by token or session, as for
the library API.
"""

from django.core.paginator import Paginator
from django.urls import reverse
from rest_framework import generics
from rest_framework.exceptions import NotAuthenticated
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Pack
from .serializers import PackDetailSerializer, PackSerializer
from .views import manifest_for

PACKS_PER_PAGE = 12
TRUE_VALUES = {"1", "true", "yes"}


def _readable_packs(user):
    return (
        Pack.objects.visible_to(user)
        .select_related("owner")
        .prefetch_related("tags")
        .with_item_count()
    )


class PackListAPI(generics.ListAPIView):
    """Public packs plus your own (private ones included), newest change first.

    ?mine=1 lists only your own, and needs sign-in (a 401 otherwise). Pages
    of 12 (page=N; a bad page is the first, one past the end the last), with
    the library API's shape: count, page, num_pages, next, previous, results.
    """

    permission_classes = [AllowAny]
    serializer_class = PackSerializer

    def list(self, request, *args, **kwargs):
        mine = request.query_params.get("mine", "").lower() in TRUE_VALUES
        if mine and not request.user.is_authenticated:
            raise NotAuthenticated("Sign in to list your own packs.")
        packs = _readable_packs(request.user)
        if mine:
            packs = packs.filter(owner=request.user)
        packs = packs.order_by("-updated_at", "-id")
        page = Paginator(packs, PACKS_PER_PAGE).get_page(request.query_params.get("page"))
        return Response(
            {
                "count": page.paginator.count,
                "page": page.number,
                "num_pages": page.paginator.num_pages,
                "next": self._page_url(mine, page.next_page_number() if page.has_next() else None),
                "previous": self._page_url(
                    mine, page.previous_page_number() if page.has_previous() else None
                ),
                "results": self.get_serializer(page.object_list, many=True).data,
            }
        )

    def _page_url(self, mine: bool, page: int | None) -> str | None:
        if page is None:
            return None
        query = f"mine=1&page={page}" if mine else f"page={page}"
        return self.request.build_absolute_uri(f"{reverse('packs:api_packs')}?{query}")


class PackDetailAPI(generics.RetrieveAPIView):
    """One pack, read-only: its details and its items in position order, each
    with this pack's variant and import path and the stored asset. Never the
    owner's notes, ratings or statuses."""

    permission_classes = [AllowAny]
    serializer_class = PackDetailSerializer

    def get_queryset(self):
        return _readable_packs(self.request.user)


class PackExportAPI(generics.GenericAPIView):
    """The pack's export manifest (format "axcenity-pack", version 1), the same
    document as the pack page's Download manifest."""

    permission_classes = [AllowAny]

    def get_queryset(self):
        return Pack.objects.visible_to(self.request.user).select_related("owner")

    def get(self, request, *args, **kwargs):
        return Response(manifest_for(request, self.get_object()))
