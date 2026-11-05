from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import TemplateView

from .discover import (
    KIND_TILES,
    TILES_BY_KIND,
    clean_kind,
    clean_query,
    discover_url,
    load_shelf,
    pending_shelves,
    shelf_provider,
)


class DiscoverView(TemplateView):
    """Type tiles, the command bar, and one pending shelf per matching provider.

    Open to signed-out visitors. The page never waits for a provider: each
    shelf fetches itself with its own HTMX request once the page is up.
    """

    template_name = "catalog/discover.html"
    extra_context = {"active_nav": "discover"}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        kind = clean_kind(self.request.GET.get("type"))
        query = clean_query(self.request.GET.get("q"))
        context.update(
            kind=kind,
            query=query,
            tile=TILES_BY_KIND[kind],
            tiles=[(tile, discover_url(tile.key, query)) for tile in KIND_TILES],
            shelves=pending_shelves(kind, query) if query else [],
        )
        return context


class DiscoverShelfView(View):
    """One provider's shelf of results, fetched by its own HTMX request."""

    def get(self, request, kind, provider):
        # Validate first, so a bad shelf URL is a 404 or 400 whatever the
        # headers, and never reaches a provider or becomes a redirect.
        source = shelf_provider(kind, provider)
        if source is None:
            raise Http404("No such shelf.")
        query = clean_query(request.GET.get("q"))
        if not query:
            return HttpResponseBadRequest("A shelf needs a search query.")

        # A shelf is a fragment; opened directly, it's shown on its page.
        if not request.htmx or request.htmx.boosted:
            return redirect(discover_url(kind, query))
        shelf = load_shelf(source, kind, query)
        return render(request, "catalog/partials/shelf.html", {"shelf": shelf})


class LibraryView(LoginRequiredMixin, TemplateView):
    template_name = "catalog/library.html"
    extra_context = {"active_nav": "library"}
