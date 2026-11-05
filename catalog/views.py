from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView
from django_htmx.http import HttpResponseClientRedirect, push_url

from providers import PROVIDERS_BY_KEY, ProviderError

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
from .library import SORT_LABELS, filter_groups, filter_library, save_to_library
from .models import SavedAsset


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
        # Results the member already has render as "In library". Shelves are
        # cached for everyone, so this is looked up fresh on every request.
        saved_ids = SavedAsset.objects.saved_external_ids(
            request.user, shelf.key, (record.external_id for record in shelf.records)
        )
        return render(request, template, {"shelf": shelf, "saved_ids": saved_ids})


class SaveAssetView(LoginRequiredMixin, View):
    """Save to library: the POST behind a Discover result's Save button.

    Members only, with CSRF (base.html sends the token on every HTMX
    request). The reply is a fragment that replaces the button: the "In
    library" badge (with the status bar's saved count out of band), or the
    ProviderError message with Try again. A bad provider or ID is a 400
    before any provider is called.
    """

    http_method_names = ["post"]

    def handle_no_permission(self):
        # Back to the Discover page the button was on, not to this POST-only URL.
        htmx = self.request.htmx
        back = (htmx and htmx.current_url_abs_path) or reverse("catalog:discover")
        login = redirect_to_login(back)
        return HttpResponseClientRedirect(login.url) if htmx else login

    def post(self, request):
        provider = request.POST.get("provider", "")
        external_id = request.POST.get("external_id", "").strip()
        if provider not in PROVIDERS_BY_KEY or not external_id or len(external_id) > 200:
            return HttpResponseBadRequest("Saving needs a known provider and an asset ID.")
        slot = {"provider": provider, "external_id": external_id}
        try:
            save_to_library(request.user, provider, external_id)
        except ProviderError as error:
            return render(
                request, "catalog/partials/save_error.html", {**slot, "error": str(error)}
            )
        return render(request, "catalog/partials/in_library.html", {**slot, "count_oob": True})


def _wants_results_only(request) -> bool:
    """True for the library controls' own HTMX requests, which swap only the results.

    A boosted link and a history restore (Back after a swap) are HTMX
    requests too, but each needs the whole page.
    """
    htmx = request.htmx
    return bool(htmx) and not htmx.boosted and not htmx.history_restore_request


class LibraryView(LoginRequiredMixin, TemplateView):
    """The member's private library: a card grid of their own entries.

    Search, filters, sort and page come from the query string, through
    filter_library(). The controls' HTMX requests get only the results
    fragment, with the tidy URL pushed to the address bar. Any other request
    for the same URL gets the whole page in the same state. Every card
    renders from the Toolbox's stored Asset, so the library works with every
    provider down.
    """

    template_name = "catalog/library.html"
    results_template_name = "catalog/partials/library_results.html"
    extra_context = {"active_nav": "library"}

    def handle_no_permission(self):
        # The results fragment would land inside the old page, so a signed-out
        # HTMX request redirects the whole window to sign-in instead.
        if _wants_results_only(self.request):
            return HttpResponseClientRedirect(redirect_to_login(self.request.get_full_path()).url)
        return super().handle_no_permission()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        results = filter_library(self.request.user, self.request.GET)
        context.update(
            results=results,
            params=results.params,
            entries=results.page.object_list,
            library_empty=not (
                results.page.paginator.count
                or SavedAsset.objects.for_user(self.request.user).exists()
            ),
            filter_groups=filter_groups(results.params),
            sort_labels=SORT_LABELS,
        )
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        if _wants_results_only(request):
            response = render(request, self.results_template_name, context)
            return push_url(response, context["results"].url)
        return self.render_to_response(context)
