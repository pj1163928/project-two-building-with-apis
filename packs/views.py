"""The pack pages: the member's packs, New pack, the builder and its autosaving
controls, and the Add to pack picker on Discover and the library.

Every pack and item is looked up through the member's own packs, so another
member's pack, item or entry is a 404. Every write is a POST with CSRF.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import FormView, TemplateView
from django_htmx.http import HttpResponseClientRedirect, trigger_client_event

from catalog.library import UnknownProviderError, filter_library
from catalog.models import SavedAsset
from providers import PROVIDERS_BY_KEY, ProviderError

from .forms import NewPackForm, PackDetailsForm, PackItemForm
from .models import Pack, PackItem
from .services import add_from_provider, add_to_pack, move_item


class HomeView(TemplateView):
    template_name = "packs/home.html"
    extra_context = {"active_nav": "home"}


def _wants_fragment(request) -> bool:
    """An HTMX request that swaps in a fragment (not boosted navigation or Back)."""
    htmx = request.htmx
    return bool(htmx) and not htmx.boosted and not htmx.history_restore_request


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


class PackListView(PacksPageMixin, TemplateView):
    """The member's packs, newest change first, with New pack."""

    template_name = "packs/pack_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["packs"] = (
            Pack.objects.owned_by(self.request.user).with_item_count().prefetch_related("tags")
        )
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
        context.update(_items_context(pack), pack=pack)
        return context


def _items_context(pack: Pack) -> dict:
    return {"pack": pack, "items": list(pack.ordered_items())}


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
        return render(request, "packs/partials/save_status.html", context)


def _status(request, message: str, status: int):
    context = {"state": "error", "message": message}
    return render(request, "packs/partials/save_status.html", context, status=status)


class PackVisibilityView(OwnPackMixin, View):
    """The public/private switch: saves at once and replies with the switch."""

    http_method_names = ["post"]

    def post(self, request, pk):
        pack = self.get_pack()
        choice = request.POST.get("visibility")
        if choice not in ("public", "private"):
            return HttpResponseBadRequest("Choose public or private.")
        pack.is_public = choice == "public"
        pack.save(update_fields=["is_public", "updated_at"])
        if not _wants_fragment(request):
            return redirect(pack)
        return render(request, "packs/partials/visibility.html", {"pack": pack, "saved": True})


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
    """Add from my library: the member's entries matching `q`, up to 12, each
    with Add, or "In pack" when it's already there. A fragment for the
    builder's search; any other request goes to the builder."""

    template_name = "packs/partials/library_search.html"

    def get(self, request, *args, **kwargs):
        pack = self.get_pack()
        if not _wants_fragment(request):
            return redirect(pack)
        return self.render_to_response(_search_context(request.user, pack, request.GET.get("q")))


def _search_context(user, pack: Pack, query) -> dict:
    results = filter_library(user, {"q": query or ""})
    in_pack = set(pack.items.values_list("saved_asset_id", flat=True))
    return {
        "pack": pack,
        "query": results.params.q,
        "results": results,
        "in_pack": in_pack,
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


class PackItemRemoveView(OwnPackMixin, View):
    """Take an item out of the pack. The library entry and the Asset stay."""

    http_method_names = ["post"]

    def post(self, request, pk, item_pk):
        self.get_item().delete()
        return _items_reply(request, self.get_pack())


def _items_reply(request, pack: Pack):
    """The builder's item list after an add, move or remove, for HTMX; the
    builder for anything else. Add from my library refreshes itself on the
    packItemsChanged event, so its "In pack" marks stay right."""
    if not _wants_fragment(request):
        return redirect(pack)
    response = render(request, "packs/partials/items.html", _items_context(pack))
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
