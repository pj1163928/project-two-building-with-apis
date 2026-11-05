from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import TemplateView

from .discover import (
    KIND_TILES,
    TILES_BY_KIND,
    clean_kind,
    clean_page,
    clean_query,
    discover_url,
    featured_query,
    load_shelf,
    pending_shelves,
    shelf_provider,
    shuffle_url,
)


class DiscoverView(TemplateView):
    """Type tiles, the command bar, and one pending shelf per matching provider.

    Open to signed-out visitors. The page never waits for a provider: each
    shelf fetches itself with its own HTMX request once the page is up. With
    no query, the shelves show a random featured search for the kind.
    """

    template_name = "catalog/discover.html"
    extra_context = {"active_nav": "discover"}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        kind = clean_kind(self.request.GET.get("type"))
        query = clean_query(self.request.GET.get("q"))
        featured = "" if query else featured_query(kind, after=self.request.GET.get("shuffle", ""))
        context.update(
            kind=kind,
            query=query,
            featured=featured,
            shuffle_url=shuffle_url(kind, featured) if featured else "",
            tile=TILES_BY_KIND[kind],
            tiles=[(tile, discover_url(tile.key, query)) for tile in KIND_TILES],
            shelves=pending_shelves(kind, query or featured),
        )
        return context


class DiscoverShelfView(View):
    """One page of one provider's shelf, fetched by its own HTMX request.

    Page 1 is the whole shelf. A later page (Load more) is a fragment that
    appends its cards to the shelf and replaces the Load more slot.
    """

    def get(self, request, kind, provider):
        # Validate first, so a bad shelf URL is a 404 or 400 whatever the
        # headers, and never reaches a provider or becomes a redirect.
        source = shelf_provider(kind, provider)
        if source is None:
            raise Http404("No such shelf.")
        query = clean_query(request.GET.get("q"))
        if not query:
            return HttpResponseBadRequest("A shelf needs a search query.")
        page = clean_page(request.GET.get("page"))
        if page is None:
            return HttpResponseBadRequest("That shelf page doesn't exist.")

        # A shelf is a fragment; opened directly, it's shown on its page.
        if not request.htmx or request.htmx.boosted:
            return redirect(discover_url(kind, query))
        shelf = load_shelf(source, kind, query, page)
        template = (
            "catalog/partials/shelf.html" if page == 1 else "catalog/partials/shelf_more.html"
        )
        return render(request, template, {"shelf": shelf})


class LibraryView(LoginRequiredMixin, TemplateView):
    template_name = "catalog/library.html"
    extra_context = {"active_nav": "library"}
