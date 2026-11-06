"""The pack pages: the member's packs, New pack, the builder and its autosaving
controls, the Add to pack picker on Discover and the library, and the pack's
own page with its manifest download.

Every pack the builder, the picker or a write touches is looked up through
the member's own packs, so another member's pack, item or entry is a 404.
The pack page and its download read packs through Pack.objects.visible_to(),
so a private or unlisted pack is a 404 there to everyone but its owner. An
unlisted pack's readers use its share link (/packs/link/<token>/,
Pack.objects.shared_by_link()). Every write is a POST with CSRF.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.http import Http404, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import FormView, TemplateView
from django_htmx.http import HttpResponseClientRedirect, push_url, trigger_client_event

from catalog.library import UnknownProviderError, filter_library, save_asset
from catalog.models import Asset, SavedAsset
from providers import PROVIDERS_BY_KEY, ProviderError

from .credits import pack_credits, pack_notice
from .downloads import item_download, pack_download
from .forms import NewPackForm, PackDetailsForm, PackItemForm
from .gallery import GALLERY_SORTS, filter_public_packs, gallery_type_choices
from .hero import hero_orbit
from .manifest import build_manifest, credit_line, is_cc0, manifest_item
from .models import Pack, PackItem
from .services import (
    ITEM_SORTS,
    ReorderError,
    add_from_provider,
    add_suggestion,
    add_to_pack,
    copy_pack,
    move_item,
    reorder_items,
    sort_items,
)
from .suggestions import find_more, suggest_assets


def _wants_fragment(request) -> bool:
    """An HTMX request that swaps in a fragment (not boosted navigation or Back)."""
    htmx = request.htmx
    return bool(htmx) and not htmx.boosted and not htmx.history_restore_request


class HomeView(TemplateView):
    """The main page, open to everyone: what the Toolbox does (the four steps,
    with Sign up and Sign in, for visitors only) and the public gallery.

    The gallery's search, type, sort and page come from the query string,
    through filter_public_packs(), which lists public packs only. The
    gallery's HTMX requests get only the results, with the tidy URL pushed,
    as the library does; any other request gets the whole page in the same state,
    with the orbit hero (hero_orbit(), public packs only).
    """

    template_name = "packs/home.html"
    results_template_name = "packs/partials/gallery_results.html"
    # The side panel starts collapsed here (PRD); base.html and shell.js read it,
    # and every other page keeps the member's own choice.
    extra_context = {"active_nav": "home", "panel_start": "collapsed"}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        gallery = filter_public_packs(self.request.GET)
        context.update(
            gallery=gallery,
            gallery_params=gallery.params,
            gallery_sorts=list(GALLERY_SORTS.items()),  # a "items" key hides dict.items()
            gallery_types=gallery_type_choices(),
            gallery_empty=not (gallery.page.paginator.count or Pack.objects.public().exists()),
        )
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        if _wants_fragment(request):
            response = render(request, self.results_template_name, context)
            return push_url(response, context["gallery"].url)
        # The whole page also gets the orbit hero (public packs only); a gallery
        # swap doesn't need it.
        context["hero"] = hero_orbit()
        return self.render_to_response(context)


class PacksPageMixin(LoginRequiredMixin):
    """Members only. Gives the side panel the member's packs. A signed-out
    visitor goes to sign in and back to login_return_url() (an HTMX request
    redirects the whole window)."""

    extra_context = {"active_nav": "packs"}

    def login_return_url(self) -> str:
        return self.request.get_full_path()

    def handle_no_permission(self):
        # Back to a page, never to a POST-only or fragment URL.
        login = redirect_to_login(self.login_return_url())
        return HttpResponseClientRedirect(login.url) if self.request.htmx else login

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["my_packs"] = Pack.objects.owned_by(self.request.user)
        return context


class OwnPackMixin(PacksPageMixin):
    """A view of one of the member's own packs (`pk` in the URL), or a 404."""

    def login_return_url(self) -> str:
        return reverse("packs:builder", args=[self.kwargs["pk"]])

    def get_pack(self) -> Pack:
        if not hasattr(self, "_pack"):
            self._pack = get_object_or_404(
                Pack.objects.owned_by(self.request.user), pk=self.kwargs["pk"]
            )
        return self._pack

    def get_item(self) -> PackItem:
        return get_object_or_404(
            self.get_pack().items.select_related("saved_asset__asset"), pk=self.kwargs["item_pk"]
        )


# How Your packs lays the packs out (user request, 2026-11-06): cards in a grid,
# or one row each in a list. The member's choice is kept in their session.
PACK_LAYOUTS = ("grid", "list")
PACK_LAYOUT_SESSION_KEY = "pack_layout"


def pack_layout(request) -> str:
    """The member's Your packs layout: `?layout=` when it's "grid" or "list"
    (remembered in the session from then on), else the remembered one, else "grid"."""
    chosen = request.GET.get("layout")
    if chosen in PACK_LAYOUTS:
        request.session[PACK_LAYOUT_SESSION_KEY] = chosen
        return chosen
    remembered = request.session.get(PACK_LAYOUT_SESSION_KEY)
    return remembered if remembered in PACK_LAYOUTS else PACK_LAYOUTS[0]


class PackListView(PacksPageMixin, TemplateView):
    """The member's packs, newest change first, with New pack, as a grid of
    cards or a list of rows (pack_layout())."""

    template_name = "packs/pack_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["packs"] = (
            Pack.objects.owned_by(self.request.user).with_item_count().prefetch_related("tags")
        )
        context["layout"] = pack_layout(self.request)
        return context


class PackCreateView(PacksPageMixin, FormView):
    """New pack: a title, its intended use and tags. The pack starts private,
    and the member lands in its builder."""

    template_name = "packs/pack_new.html"
    form_class = NewPackForm

    def form_valid(self, form):
        return redirect(form.create(self.request.user))


class PackBuilderView(OwnPackMixin, TemplateView):
    """The builder: the pack's details, its items, and Add from my library."""

    template_name = "packs/builder.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pack = self.get_pack()
        context.update(_items_context(pack), **_share_context(self.request, pack))
        context.update(_suggestions_context(self.request.user, pack))
        context["copied_from"] = _copied_from(self.request.user, pack)
        return context


def _copied_from(user, pack: Pack) -> dict | None:
    """The pack this one was copied from (Copy pack), for the builder's note: its
    title and owner, and its page when `user` may still read it by slug (public,
    or their own). None for a pack that wasn't copied, or whose original is gone."""
    original = pack.copied_from
    if original is None:
        return None
    readable = Pack.objects.visible_to(user).filter(pk=original.pk).exists()
    return {
        "title": original.title,
        "owner": original.owner.get_username(),
        "url": original.get_public_url() if readable else "",
    }


def _items_context(pack: Pack, **extra) -> dict:
    """The builder's item list, with the pack's credits for its license compatibility."""
    items = list(pack.ordered_items())
    return {
        "pack": pack,
        "items": items,
        "item_sorts": ITEM_SORTS,
        "credits": pack_credits(items),
        "is_owner": True,
        **extra,
    }


class PackDetailsView(OwnPackMixin, View):
    """Autosave one of the pack's details (title, intended use or tags).

    The reply is the builder's status line, plus the title out of band when
    it changed; a bad value is a 400 with one sentence, and nothing saves.
    """

    http_method_names = ["post"]

    def post(self, request, pk):
        pack = self.get_pack()
        form = PackDetailsForm(request.POST, pack=pack)
        if not form.changed_fields:
            return _status(request, "There was nothing to save.", status=400)
        if not form.is_valid():
            return _status(request, form.first_error, status=400)
        form.save()
        if not _wants_fragment(request):
            return redirect(pack)
        context = {"state": "saved", "pack": pack, "title_oob": "title" in form.changed_fields}
        response = render(request, "packs/partials/save_status.html", context)
        if "tags" in form.changed_fields:
            # Its own event: only the suggestions (and Find more) depend on the tags.
            response = trigger_client_event(response, "packTagsChanged")
        return response


def _status(request, message: str, status: int):
    context = {"state": "error", "message": message}
    return render(request, "packs/partials/save_status.html", context, status=status)


def _share_context(request, pack: Pack, **extra) -> dict:
    """The pack and its absolute share link ("" before it's first unlisted)."""
    link = request.build_absolute_uri(pack.get_share_url()) if pack.share_token else ""
    return {"pack": pack, "share_link": link, **extra}


class PackVisibilityView(OwnPackMixin, View):
    """The private/unlisted/public switch: saves at once and replies with the
    switch, plus the share link while the pack is unlisted (the first unlisting
    makes it)."""

    http_method_names = ["post"]

    def post(self, request, pk):
        pack = self.get_pack()
        choice = request.POST.get("visibility")
        if choice not in Pack.Visibility.values:
            return HttpResponseBadRequest("Choose private, unlisted or public.")
        pack.set_visibility(choice)
        if not _wants_fragment(request):
            return redirect(pack)
        context = _share_context(request, pack, saved=True)
        return render(request, "packs/partials/visibility.html", context)


class PackRotateLinkView(OwnPackMixin, View):
    """New link: replace the pack's share link, so every older link is a 404.

    The owner confirms first (the builder's dialog). Replies with the share
    link box holding the new link.
    """

    http_method_names = ["post"]

    def post(self, request, pk):
        pack = self.get_pack()
        pack.rotate_share_token()
        if not _wants_fragment(request):
            return redirect(pack)
        context = _share_context(request, pack, rotated=True)
        return render(request, "packs/partials/share_link.html", context)


class PackDeleteView(OwnPackMixin, View):
    """Delete the pack after the builder's confirm dialog. Its items go with it;
    the member's library entries and the shared Assets stay."""

    http_method_names = ["post"]

    def login_return_url(self) -> str:
        return reverse("packs:list")

    def post(self, request, pk):
        self.get_pack().delete()
        return redirect("packs:list")


class PackLibrarySearchView(OwnPackMixin, TemplateView):
    """Add from my library: one page of 12 of the member's entries matching `q`
    (`page`), each with its thumbnail and Add. Entries already in the pack are
    hidden unless `show_in=1`, and then marked "In pack". A fragment for the
    builder's search; any other request goes to the builder."""

    template_name = "packs/partials/library_search.html"

    def get(self, request, *args, **kwargs):
        pack = self.get_pack()
        if not _wants_fragment(request):
            return redirect(pack)
        return self.render_to_response(_search_context(request.user, pack, request.GET))


def _search_context(user, pack: Pack, params) -> dict:
    query = params.get("q") or ""
    show_in = params.get("show_in") == "1"
    in_pack = set(pack.items.values_list("saved_asset_id", flat=True))
    search = {"q": query, "page": params.get("page") or "1"}
    results = filter_library(user, search, exclude_entries=() if show_in else in_pack)
    hidden = 0
    if not show_in and in_pack:
        everything = filter_library(user, {"q": query})
        hidden = everything.page.paginator.count - results.page.paginator.count
    return {
        "pack": pack,
        "query": results.params.q,
        "results": results,
        "in_pack": in_pack,
        "show_in": show_in,
        "hidden": hidden,
        "library_empty": not SavedAsset.objects.for_user(user).exists(),
    }


class PackAddItemView(OwnPackMixin, View):
    """Add one of the member's entries (`entry`) to the pack from the builder.

    Replies with the item list (see _items_reply). Another member's entry,
    or one that doesn't exist, is a 404.
    """

    http_method_names = ["post"]

    def post(self, request, pk):
        pack = self.get_pack()
        entry = _own_entry(request)
        add_to_pack(pack, entry)
        return _items_reply(request, pack)


def _own_entry(request) -> SavedAsset:
    entry_id = request.POST.get("entry") or request.GET.get("entry") or ""
    if not entry_id.isdigit():
        raise Http404("No such library entry.")
    return get_object_or_404(
        SavedAsset.objects.for_user(request.user).select_related("asset"), pk=entry_id
    )


class PackSuggestionsView(OwnPackMixin, TemplateView):
    """Suggested for this pack: stored Assets sharing the pack's tags, with Find
    more from providers. A fragment the builder reloads on packItemsChanged and
    packTagsChanged; any other request goes to the builder."""

    template_name = "packs/partials/suggestions.html"

    def get(self, request, *args, **kwargs):
        pack = self.get_pack()
        if not _wants_fragment(request):
            return redirect(pack)
        return self.render_to_response(_suggestions_context(request.user, pack))


def _suggestions_context(user, pack: Pack) -> dict:
    """The suggestions, which of them the owner has saved, and Find more.

    "In your library" checks only `user`'s own entries.
    """
    suggestions = suggest_assets(pack)
    in_library = set(
        SavedAsset.objects.for_user(user)
        .filter(asset__in=[asset.pk for asset in suggestions])
        .values_list("asset_id", flat=True)
    )
    return {
        "pack": pack,
        "suggestions": suggestions,
        "suggestions_in_library": in_library,
        "has_tags": pack.tags.exists(),
        "find_more": find_more(pack),
    }


class PackSuggestionAddView(OwnPackMixin, View):
    """Add a suggestion (`asset`, a stored Asset's id) to the pack.

    add_suggestion() saves it to the owner's library as To review when they
    don't have it, then adds it, in one transaction, never calling a
    provider. Replies with the item list (packItemsChanged refreshes the
    suggestions and Add from my library), plus the saved count out of band
    only when a new library entry was made. An unknown asset is a 404.
    """

    http_method_names = ["post"]

    def post(self, request, pk):
        pack = self.get_pack()
        asset_id = request.POST.get("asset") or ""
        if not asset_id.isdigit():
            raise Http404("No such asset.")
        asset = get_object_or_404(Asset, pk=asset_id)
        _entry, entry_created, _item = add_suggestion(pack, asset)
        return _items_reply(request, pack, count_oob=entry_created)


class PackItemUpdateView(OwnPackMixin, View):
    """Autosave one item's variant or import path. Replies with that item's
    status line; a bad value is a 400 with one sentence, and nothing saves."""

    http_method_names = ["post"]

    def post(self, request, pk, item_pk):
        item = self.get_item()
        form = PackItemForm(request.POST, item=item)
        context = {"item": item}
        if not form.changed_fields:
            context.update(state="error", message="There was nothing to save.")
            return render(request, "packs/partials/item_status.html", context, status=400)
        if not form.is_valid():
            context.update(state="error", message=form.first_error)
            return render(request, "packs/partials/item_status.html", context, status=400)
        form.save()
        if not _wants_fragment(request):
            return redirect(self.get_pack())
        return render(request, "packs/partials/item_status.html", {**context, "state": "saved"})


class PackItemMoveView(OwnPackMixin, View):
    """Move an item one place up or down; replies with the item list."""

    http_method_names = ["post"]

    def post(self, request, pk, item_pk):
        steps = {"up": -1, "down": 1}
        direction = request.POST.get("direction")
        if direction not in steps:
            return HttpResponseBadRequest("Move an item up or down.")
        move_item(self.get_item(), steps[direction])
        return _items_reply(request, self.get_pack())


class PackItemsReorderView(OwnPackMixin, View):
    """Drag and drop: save the order posted as `order`, every item's id once,
    comma-separated. Replies with the item list; an order that doesn't match
    the pack's items (a stale page) is a 400 and changes nothing."""

    http_method_names = ["post"]

    def post(self, request, pk):
        pack = self.get_pack()
        parts = [part.strip() for part in request.POST.get("order", "").split(",")]
        if not all(part.isdigit() for part in parts):
            return HttpResponseBadRequest("Send every item's id, in the new order.")
        try:
            reorder_items(pack, [int(part) for part in parts])
        except ReorderError as error:
            return HttpResponseBadRequest(str(error))
        return _items_reply(request, pack)


class PackItemsSortView(OwnPackMixin, View):
    """Auto sort the items by `sort` (one of ITEM_SORTS); replies with the list."""

    http_method_names = ["post"]

    def post(self, request, pk):
        pack = self.get_pack()
        sort = request.POST.get("sort")
        if sort not in ITEM_SORTS:
            return HttpResponseBadRequest("Choose how to sort the items.")
        sort_items(pack, sort)
        return _items_reply(request, pack, sorted_by=ITEM_SORTS[sort])


class PackItemRemoveView(OwnPackMixin, View):
    """Take an item out of the pack. The library entry and the Asset stay."""

    http_method_names = ["post"]

    def post(self, request, pk, item_pk):
        self.get_item().delete()
        return _items_reply(request, self.get_pack())


def _items_reply(request, pack: Pack, **extra):
    """The builder's item list after an add, move, reorder, sort or remove, for
    HTMX; the builder for anything else. Add from my library refreshes itself
    on the packItemsChanged event, so what it hides stays right."""
    if not _wants_fragment(request):
        return redirect(pack)
    response = render(request, "packs/partials/items.html", _items_context(pack, **extra))
    return trigger_client_event(response, "packItemsChanged")


# ---------------------------------------------------------------- the Add to pack picker


class PickerView(PacksPageMixin, TemplateView):
    """The picker's list of the member's own packs, for one asset, loaded each
    time the picker opens. The asset is a library entry (`entry`) or a
    Discover result (`provider` and `external_id`)."""

    template_name = "packs/partials/picker_list.html"

    def login_return_url(self) -> str:
        return (self.request.htmx and self.request.htmx.current_url_abs_path) or reverse(
            "catalog:discover"
        )

    def get(self, request, *args, **kwargs):
        target = _picker_target(request, request.GET)
        if target is None:
            return HttpResponseBadRequest("Choose an asset to add.")
        return self.render_to_response(_picker_context(request.user, target))


class PickerAddView(PickerView):
    """Add the picker's asset to one of the member's packs (`pk`).

    A Discover result goes through the member's library first
    (add_from_provider). A ProviderError shows its message in the picker,
    and nothing is saved or added. Another member's pack or entry is a 404.
    """

    http_method_names = ["post"]

    def post(self, request, pk):
        pack = get_object_or_404(Pack.objects.owned_by(request.user), pk=pk)
        target = _picker_target(request, request.POST)
        if target is None:
            return HttpResponseBadRequest("Choose an asset to add.")
        context = {}
        try:
            if "entry" in target:
                add_to_pack(pack, target["entry"])
            else:
                add_from_provider(pack, target["provider"], target["external_id"])
                context["count_oob"] = True
        except ProviderError as error:
            context["error"] = str(error)
        except UnknownProviderError:
            return HttpResponseBadRequest("Choose an asset to add.")
        else:
            context["added_to"] = pack
        return self.render_to_response({**_picker_context(request.user, target), **context})


def _picker_target(request, params) -> dict | None:
    """The picker's asset: the member's own entry (404 for anyone else's), or a
    provider and ID, or None when neither is given properly."""
    if params.get("entry"):
        entry_id = params["entry"]
        if not entry_id.isdigit():
            return None
        entries = SavedAsset.objects.for_user(request.user).select_related("asset")
        return {"entry": get_object_or_404(entries, pk=entry_id)}
    provider = params.get("provider", "")
    external_id = params.get("external_id", "").strip()
    if provider not in PROVIDERS_BY_KEY or not external_id or len(external_id) > 200:
        return None
    return {"provider": provider, "external_id": external_id}


def _picker_context(user, target: dict) -> dict:
    entry = target.get("entry")
    if entry is None:
        entry = (
            SavedAsset.objects.for_user(user)
            .filter(asset__provider=target["provider"], asset__external_id=target["external_id"])
            .first()
        )
    packs = Pack.objects.owned_by(user).with_item_count()
    holding = set(entry.pack_items.values_list("pack_id", flat=True)) if entry else set()
    return {"packs": packs, "holding": holding, "target": target}


# ---------------------------------------------------------------- the pack's own page


def _visible_pack(request, slug: str) -> Pack:
    """The pack at `slug` when the caller may read it (public, or theirs), else a 404."""
    packs = Pack.objects.visible_to(request.user).select_related("owner")
    return get_object_or_404(packs, slug=slug)


def _shared_pack(token: str) -> Pack:
    """The pack whose share link carries `token` (unlisted or public), else a 404."""
    return get_object_or_404(Pack.objects.shared_by_link(token).select_related("owner"))


def manifest_for(request, pack: Pack) -> dict:
    """The pack's manifest, its source_url the absolute address readers use
    (the share link while unlisted, otherwise the pack's page).

    The page's download and the API's export both call this, so they match.
    """
    return build_manifest(pack, source_url=request.build_absolute_uri(pack.reader_url))


def _download(request, pack: Pack) -> JsonResponse:
    response = JsonResponse(manifest_for(request, pack), json_dumps_params={"indent": 2})
    response["Content-Disposition"] = f'attachment; filename="{pack.slug}.axcenity-pack.json"'
    return response


def _unindexed(response):
    """A share link's reply: kept out of search engines, like the link itself."""
    response["X-Robots-Tag"] = "noindex, nofollow"
    return response


class PackPageView(TemplateView):
    """A pack's page, /packs/<slug>/: its items with their licenses and credit.

    Anyone can read a public pack, signed out or not; a private or unlisted
    one is a 404 here to everyone but its owner. It shows only the pack, its
    items and their stored Assets, never anything from a member's library
    entry, and only the owner gets a way into the builder.
    """

    template_name = "packs/pack_page.html"
    extra_context = {"active_nav": "packs"}

    def get_pack(self) -> Pack:
        return _visible_pack(self.request, self.kwargs["slug"])

    def page_urls(self, pack: Pack) -> dict:
        """The page's own address (the crumb), its downloads' and Copy pack's."""
        return {
            "page_url": pack.get_public_url(),
            "export_url": reverse("packs:export", args=[pack.slug]),
            "files_url": reverse("packs:files", args=[pack.slug]),
            "attribution_url": reverse("packs:attribution_pack", args=[pack.slug]),
            "copy_url": reverse("packs:copy", args=[pack.slug]),
        }

    def item_save_url(self, pack: Pack, item: PackItem) -> str:
        return reverse("packs:save_item", args=[pack.slug, item.pk])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pack = self.pack = self.get_pack()
        items = list(pack.ordered_items())
        user = self.request.user
        # The reader's own entries for these assets (Save's "In your library"):
        # only theirs, never anything about the pack owner's.
        mine = dict(
            SavedAsset.objects.for_user(user)
            .filter(asset__in=[item.saved_asset.asset_id for item in items])
            .values_list("asset_id", "pk")
        )
        for item in items:
            item.export = manifest_item(item)
            item.needs_credit = not is_cc0(item.asset.license)
            item.credit = credit_line(item.asset)
            item.save_url = self.item_save_url(pack, item)
            item.my_entry_id = mine.get(item.saved_asset.asset_id)
        credits = pack_credits(items)
        urls = self.page_urls(pack)
        context.update(
            pack=pack,
            items=items,
            tags=pack.tags.order_by("name"),
            is_owner=user.is_authenticated and pack.owner_id == user.pk,
            my_packs=Pack.objects.owned_by(user),
            credits=credits,
            credits_needed=credits.needing_credit,
            has_files=any(item.export["files"] for item in items),
            # Copy pack's confirm: how many assets would join the reader's library.
            copy_missing=sum(1 for item in items if item.my_entry_id is None),
            **urls,
        )
        return context


class PackExportView(View):
    """Download the pack's manifest as <slug>.axcenity-pack.json.

    The same reader rule as the page: a private pack is a 404 to everyone
    but its owner. The document is the API export's, indented for reading.
    """

    http_method_names = ["get", "head"]

    def get(self, request, slug):
        return _download(request, _visible_pack(request, slug))


class PackSharedView(PackPageView):
    """An unlisted pack's page by its share link, /packs/link/<token>/: for
    anyone holding the link, signed in or not.

    The same read-only page. A token the owner has replaced, or a private
    pack's, is a 404. Once the pack is public, the link goes to its page.
    """

    def get(self, request, *args, **kwargs):
        self.shared = _shared_pack(kwargs["token"])
        if self.shared.is_public:
            return redirect(self.shared.get_public_url())
        return _unindexed(super().get(request, *args, **kwargs))

    def get_pack(self) -> Pack:
        return self.shared

    def page_urls(self, pack: Pack) -> dict:
        return {
            "page_url": pack.get_share_url(),
            "export_url": reverse("packs:shared_export", args=[pack.share_token]),
            "files_url": reverse("packs:shared_files", args=[pack.share_token]),
            "attribution_url": reverse("packs:shared_attribution", args=[pack.share_token]),
            "copy_url": reverse("packs:shared_copy", args=[pack.share_token]),
        }

    def item_save_url(self, pack: Pack, item: PackItem) -> str:
        return reverse("packs:shared_save_item", args=[pack.share_token, item.pk])


class PackSharedExportView(View):
    """Download an unlisted (or public) pack's manifest by its share link."""

    http_method_names = ["get", "head"]

    def get(self, request, token):
        return _unindexed(_download(request, _shared_pack(token)))


def _files_reply(request, pack: Pack) -> JsonResponse:
    """What Download files fetches: the whole pack, or one item (`item`, an id in
    this pack, else a 404). Only the providers' URLs and the credits; the
    browser fetches and zips the files (packs.downloads)."""
    items = list(pack.ordered_items())
    source_url = request.build_absolute_uri(pack.reader_url)
    item_id = request.GET.get("item")
    if item_id is None:
        credits = pack_credits(items)
        data = pack_download(
            pack,
            items,
            manifest=manifest_for(request, pack),
            credits_text=pack_notice(pack, credits, source_url),
        )
    else:
        item = next((item for item in items if str(item.pk) == item_id), None)
        if item is None:
            raise Http404("No such item in this pack.")
        notice = pack_credits([item]).notice(
            f'"{item.asset.title}", from the pack "{pack.title}"',
            compiled_by=pack.owner.get_username(),
            source_url=source_url,
        )
        data = item_download(item, credits_text=notice)
    return JsonResponse(data)


class PackFilesView(View):
    """Download files: the pack's (or one item's) file list for the browser's zip.

    The same reader rule as the page and the manifest: a private or unlisted
    pack is a 404 here to everyone but its owner.
    """

    http_method_names = ["get", "head"]

    def get(self, request, slug):
        return _files_reply(request, _visible_pack(request, slug))


class PackSharedFilesView(View):
    """Download files for an unlisted (or public) pack, by its share link."""

    http_method_names = ["get", "head"]

    def get(self, request, token):
        return _unindexed(_files_reply(request, _shared_pack(token)))


# ---------------------------------------------------------------- Save and Copy (Phase 11)


class PackReaderWriteMixin(LoginRequiredMixin):
    """Save an item from, or copy, a pack the member can read: members only, POST
    with CSRF. The pack comes by slug or, with by_link, by its share link.

    A signed-out visitor goes to sign in and back to the pack's page (an HTMX
    request redirects the whole window), never to this POST-only URL.
    """

    http_method_names = ["post"]
    by_link = False

    def page_url(self) -> str:
        if self.by_link:
            return reverse("packs:shared", args=[self.kwargs["token"]])
        return reverse("packs:public", args=[self.kwargs["slug"]])

    def handle_no_permission(self):
        login = redirect_to_login(self.page_url())
        return HttpResponseClientRedirect(login.url) if self.request.htmx else login

    def get_pack(self) -> Pack:
        """The pack page's reader rule: a 404 for any pack the member can't read."""
        if self.by_link:
            return _shared_pack(self.kwargs["token"])
        return _visible_pack(self.request, self.kwargs["slug"])


class PackItemSaveView(PackReaderWriteMixin, View):
    """Save one item of the pack to the member's library (Save to library).

    The stored Asset is saved through save_asset(): an entry the member has
    comes back untouched, otherwise a new To review one is made, and no
    provider is called. HTMX gets the item's "In your library" slot (with the
    saved count out of band for a new entry); anything else goes back to the
    pack's page. An item of another pack is a 404.
    """

    def post(self, request, item_pk, **kwargs):
        pack = self.get_pack()
        item = get_object_or_404(pack.items.select_related("saved_asset__asset"), pk=item_pk)
        entry, created = save_asset(request.user, item.asset)
        if not _wants_fragment(request):
            return redirect(self.page_url())
        item.my_entry_id = entry.pk
        context = {"item": item, "saved": True, "count_oob": created}
        return render(request, "packs/partials/item_save.html", context)


class PackCopyView(PackReaderWriteMixin, View):
    """Copy pack: a private copy for the member (copy_pack()), then its builder."""

    def post(self, request, **kwargs):
        copy = copy_pack(self.get_pack(), request.user)
        return redirect(copy)
