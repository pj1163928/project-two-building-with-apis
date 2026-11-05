"""The library API: /api/library/ and /api/library/<id>/.

Sign-in by token (`Authorization: Token <key>`, no CSRF) or by the browser
session (CSRF checked on writes); see REST_FRAMEWORK in config/settings.py.
The views are thin: browsing is filter_library() and saving is
save_to_library(), the same functions the library page uses.
"""

from django.urls import reverse
from rest_framework import generics, status
from rest_framework.response import Response

from providers import ProviderError

from .library import LibraryParams, filter_library, save_to_library
from .models import SavedAsset
from .serializers import LibraryEntrySerializer, NewLibraryEntrySerializer

ALREADY_SAVED_MESSAGE = "Already in your library."


class LibraryAPI(generics.ListCreateAPIView):
    """Your library.

    GET lists your entries with the library page's parameters: q, type,
    provider, status and tag (each may repeat), min_rating, sort (newest,
    oldest, title, rating, community) and page, 12 to a page. Bad values
    fall back to the defaults, as on the page.

    POST saves an asset: provider and external_id, plus optional notes,
    rating and status. An asset already in your library is a 400 ("Already
    in your library."); a provider failure is a 502 with its message.
    """

    serializer_class = LibraryEntrySerializer

    def get_serializer_class(self):
        return (
            NewLibraryEntrySerializer
            if self.request.method == "POST"
            else super().get_serializer_class()
        )

    def list(self, request, *args, **kwargs):
        results = filter_library(request.user, request.query_params)
        page = results.page
        next_page = page.next_page_number() if page.has_next() else None
        previous_page = page.previous_page_number() if page.has_previous() else None
        return Response(
            {
                "count": page.paginator.count,
                "page": page.number,
                "num_pages": page.paginator.num_pages,
                "next": self._page_url(results.params, next_page),
                "previous": self._page_url(results.params, previous_page),
                "results": self.get_serializer(page.object_list, many=True).data,
            }
        )

    def _page_url(self, params: LibraryParams, page: int | None) -> str | None:
        """The API URL for another page of the same parameters, or None."""
        if page is None:
            return None
        path = reverse("catalog:api_library")
        return self.request.build_absolute_uri(f"{path}?{params.query_string(page)}")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review = dict(serializer.validated_data)
        provider = review.pop("provider")
        external_id = review.pop("external_id")
        try:
            entry, created = save_to_library(request.user, provider, external_id, **review)
        except ProviderError as error:
            # The provider is at fault, not the request: a bad gateway, with
            # the message that's safe to show.
            return Response({"detail": str(error)}, status=status.HTTP_502_BAD_GATEWAY)
        if not created:
            return Response({"detail": ALREADY_SAVED_MESSAGE}, status=status.HTTP_400_BAD_REQUEST)
        # Read it again with its community rating, which may include the new rating.
        entry = SavedAsset.objects.with_community_rating().select_related("asset").get(pk=entry.pk)
        return Response(LibraryEntrySerializer(entry).data, status=status.HTTP_201_CREATED)


class LibraryEntryAPI(generics.RetrieveUpdateDestroyAPIView):
    """One of your library entries.

    GET reads it. PATCH or PUT changes its notes, rating and status; the
    asset's fields are read-only and ignored. DELETE removes the entry from
    your library and from every one of your packs it's in. The shared asset
    stays for everyone else.
    """

    serializer_class = LibraryEntrySerializer

    def get_queryset(self):
        # Only the caller's own entries, so anything else is a 404.
        return (
            SavedAsset.objects.for_user(self.request.user)
            .with_community_rating()
            .select_related("asset")
            .prefetch_related("asset__tags")
        )

    def perform_update(self, serializer):
        serializer.save()
        # Read it again, so the community rating includes a new rating.
        serializer.instance = self.get_object()
