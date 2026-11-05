from urllib.parse import urlsplit

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.http import Http404, HttpResponseBadRequest, QueryDict
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView
from django_htmx.http import HttpResponseClientRedirect, push_url, replace_url

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
from .forms import NOTES_MAX_LENGTH, ReviewForm
from .library import SORT_LABELS, filter_groups, filter_library, save_to_library
from .models import SavedAsset, Tag

# The drawer's stars, lowest first.
RATING_VALUES = (1, 2, 3, 4, 5)


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
        external_ids = [record.external_id for record in shelf.records]
        saved_ids = SavedAsset.objects.saved_external_ids(request.user, shelf.key, external_ids)
        # Each result's community rating (every member's average), fresh like saved_ids.
        community = SavedAsset.objects.community_ratings(shelf.key, external_ids)
        context = {"shelf": shelf, "saved_ids": saved_ids, "community_ratings": community}
        return render(request, template, context)


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


def _wants_fragment(request) -> bool:
    """True for the library's own HTMX requests, which swap in a fragment: the
    controls' results, or a card's drawer.

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
        if _wants_fragment(self.request):
            return HttpResponseClientRedirect(redirect_to_login(self.request.get_full_path()).url)
        return super().handle_no_permission()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_library_context(self.request.user, self.request.GET))
        context.update(
            filter_groups=filter_groups(
                context["params"], Tag.objects.in_library(self.request.user)
            ),
            sort_labels=SORT_LABELS,
        )
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        if _wants_fragment(request):
            response = render(request, self.results_template_name, context)
            return push_url(response, context["results"].url)
        return self.render_to_response(context)


def _library_context(user, params) -> dict:
    """What the library's results fragment needs, for `params` from a query string."""
    results = filter_library(user, params)
    return {
        "results": results,
        "params": results.params,
        "entries": results.page.object_list,
        "library_empty": not (
            results.page.paginator.count or SavedAsset.objects.for_user(user).exists()
        ),
    }


class RemoveFromLibraryView(LoginRequiredMixin, View):
    """Remove one of the member's own entries: the POST behind a library card's Remove.

    Members only, with CSRF. Another member's entry, or one that doesn't
    exist, is a 404. The shared Asset stays. The library's HTMX request gets
    the results fragment again, for the view the member was on (read from
    HX-Current-URL), with the status bar's saved count out of band. That
    includes the drawer's Remove, which posts from the library page. Any
    other request, the full entry page's boosted form included, is sent back
    to the library.
    """

    http_method_names = ["post"]

    def handle_no_permission(self):
        login = redirect_to_login(reverse("catalog:library"))
        return HttpResponseClientRedirect(login.url) if self.request.htmx else login

    def post(self, request, pk):
        entry = get_object_or_404(SavedAsset.objects.for_user(request.user), pk=pk)
        entry.delete()
        if not _wants_fragment(request):
            return redirect("catalog:library")
        context = _library_context(request.user, _current_library_params(request))
        response = render(
            request, "catalog/partials/library_results.html", {**context, "count_oob": True}
        )
        # A page that no longer exists falls back to the last one; keep the address bar in step.
        return replace_url(response, context["results"].url)


class EntryView(LoginRequiredMixin, TemplateView):
    """One of the member's entries: the drawer's fragment, or the same as a full page.

    The library's HTMX request (a card's title) gets the drawer. A direct
    visit, a boosted link or a history restore gets the full page, so the
    URL can be bookmarked and shared with yourself. Another member's entry,
    or one that doesn't exist, is a 404. Everything renders from the stored
    Asset, so it works with every provider down.
    """

    template_name = "catalog/entry.html"
    drawer_template_name = "catalog/partials/entry_drawer.html"
    extra_context = {"active_nav": "library"}

    def handle_no_permission(self):
        # The drawer would fill with the sign-in page, so a signed-out HTMX
        # request redirects the whole window to sign-in instead.
        if _wants_fragment(self.request):
            return HttpResponseClientRedirect(redirect_to_login(self.request.get_full_path()).url)
        return super().handle_no_permission()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            entry=_own_entry(self.request.user, self.kwargs["pk"]),
            status_choices=SavedAsset.Status.choices,
            star_values=RATING_VALUES,
            notes_max_length=NOTES_MAX_LENGTH,
        )
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        if _wants_fragment(request):
            return render(request, self.drawer_template_name, context)
        return self.render_to_response(context)


class UpdateEntryView(LoginRequiredMixin, View):
    """Save a change to one of the member's entries: whichever of its status,
    rating and notes is posted (ReviewForm), and nothing else.

    Members only, with CSRF; another member's entry is a 404. The drawer's
    HTMX request gets the status line (#entry-save-status): "Saved", or a
    400 with the first problem and nothing saved. A status or rating change
    from the library also sends the card behind the drawer, out of band, and
    a rating change the drawer's community rating. A plain POST is sent back
    to the entry's page.

    A signed-out HTMX save (a session that ended mid-edit) gets a 401 status
    line with a sign-in link that opens in a new tab, rather than a redirect
    that would throw away the notes being typed.
    """

    http_method_names = ["post"]
    template_name = "catalog/partials/entry_save_status.html"

    def handle_no_permission(self):
        entry_url = reverse("catalog:entry", args=[self.kwargs["pk"]])
        login = redirect_to_login(entry_url)
        if not _wants_fragment(self.request):
            return login
        context = {
            "state": "error",
            "message": "You're signed out, so this didn't save. Your text is still here.",
            "sign_in_url": login.url,
        }
        return render(self.request, self.template_name, context, status=401)

    def post(self, request, pk):
        entry = _own_entry(request.user, pk)
        form = ReviewForm(request.POST, instance=entry)
        if not form.changed_fields:
            return self.reply(entry, status=400, message="There was nothing to save.")
        if not form.is_valid():
            return self.reply(entry, status=400, message=form.first_error)
        form.save()
        if not _wants_fragment(request):
            return redirect("catalog:entry", pk=entry.pk)
        changed = set(form.changed_fields)
        # Read it again, so the community rating includes the new rating.
        entry = _own_entry(request.user, pk)
        # The card behind the drawer shows the status and the ratings, not the notes.
        card_oob = bool({"status", "rating"} & changed) and _from_library(request)
        return self.reply(entry, card_oob=card_oob, community_oob="rating" in changed)

    def reply(self, entry, status=200, message="", card_oob=False, community_oob=False):
        context = {
            "entry": entry,
            "state": "error" if message else "saved",
            "message": message,
            "card_oob": card_oob,
            "community_oob": community_oob,
        }
        return render(self.request, self.template_name, context, status=status)


def _own_entry(user, pk) -> SavedAsset:
    """The member's own entry `pk` with its Asset, or a 404."""
    entries = SavedAsset.objects.for_user(user).with_community_rating().select_related("asset")
    return get_object_or_404(entries.prefetch_related("asset__tags"), pk=pk)


def _current_library_params(request) -> QueryDict:
    """The library parameters of the page the request came from, or none.

    Only a library URL counts: a request from any other page gets the whole
    library.
    """
    if not _from_library(request):
        return QueryDict()
    return QueryDict(urlsplit(request.htmx.current_url).query)


def _from_library(request) -> bool:
    """Whether an HTMX request came from the library page (HX-Current-URL)."""
    current = urlsplit(request.htmx.current_url or "")
    return current.path == reverse("catalog:library")
