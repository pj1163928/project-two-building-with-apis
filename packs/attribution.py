"""The Attribution center's pages: the license guide, and the attribution for
each pack and each asset.

- The guide (/attribution/) is for everyone.
- Pack attribution (/attribution/packs/) lists the member's own packs; each
  pack's attribution (/attribution/packs/<slug>/) follows the pack page's
  reader rule (Pack.objects.visible_to()), and an unlisted pack's readers use
  its share link (/packs/link/<token>/attribution/).
- Asset attribution (/attribution/assets/) is a member's own library,
  filtered by search, license type and credit rule; each asset's attribution
  (/attribution/assets/<id>/) is their own entry only, a 404 otherwise.

Only Packs, PackItems and Assets are read for anything a reader sees; an
entry's page reads the member's own entry. The license wording comes from
catalog.licenses, the credits and notice from packs.credits.
"""

from urllib.parse import urlencode

from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import TemplateView

from catalog.library import clean_license_params, filter_library, license_choices, license_filter
from catalog.licenses import LICENSE_ORDER, LICENSES, SYMBOLS, USES
from catalog.models import SavedAsset

from .credits import pack_credits, pack_notice
from .manifest import credit_line
from .models import Pack, PackItem
from .views import PacksPageMixin, _shared_pack, _unindexed, _visible_pack, _wants_fragment


def _ordered_items():
    return PackItem.objects.select_related("saved_asset__asset").order_by("position", "id")


class AttributionPageMixin:
    """The Attribution center's sidebar entry and its own panel (`attribution_page`
    marks the current row: guide, packs or assets)."""

    attribution_page = "guide"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(active_nav="attribution", attribution_page=self.attribution_page)
        return context


class AttributionGuideView(AttributionPageMixin, TemplateView):
    """The guide, /attribution/: every license in plain words, for everyone."""

    template_name = "packs/attribution.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            licenses=[LICENSES[key] for key in LICENSE_ORDER],
            symbols=list(SYMBOLS.values()),
            uses=USES,
        )
        return context


class AttributionPacksView(AttributionPageMixin, PacksPageMixin, TemplateView):
    """Pack attribution, /attribution/packs/: the member's own packs, each with the
    licenses in it, what they ask and a link to its attribution page."""

    template_name = "packs/attribution_packs.html"
    attribution_page = "packs"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        packs = Pack.objects.owned_by(self.request.user).prefetch_related(
            Prefetch("items", _ordered_items())
        )
        context["pack_credits"] = [(pack, pack_credits(list(pack.items.all()))) for pack in packs]
        return context


class PackAttributionView(AttributionPageMixin, TemplateView):
    """One pack's attribution, /attribution/packs/<slug>/: its licenses with their
    terms, the credits each item needs, and the formal notice to copy.

    The pack page's reader rule: anyone reads a public pack; a private or
    unlisted one is a 404 here to everyone but its owner.
    """

    template_name = "packs/attribution_pack.html"
    attribution_page = "packs"

    def get_pack(self) -> Pack:
        return _visible_pack(self.request, self.kwargs["slug"])

    def urls(self, pack: Pack) -> dict:
        return {
            "page_url": pack.get_public_url(),
            "attribution_url": reverse("packs:attribution_pack", args=[pack.slug]),
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pack = self.get_pack()
        items = list(pack.ordered_items())
        for item in items:
            item.credit = credit_line(item.asset)
        credits = pack_credits(items)
        urls = self.urls(pack)
        user = self.request.user
        context.update(
            pack=pack,
            items=items,
            credits=credits,
            notice=pack_notice(pack, credits, self.request.build_absolute_uri(urls["page_url"])),
            credit_lines=credits.credit_lines(),
            is_owner=user.is_authenticated and pack.owner_id == user.pk,
            **urls,
        )
        return context


class SharedPackAttributionView(PackAttributionView):
    """An unlisted pack's attribution by its share link, for anyone holding it.
    A public pack's link goes to its slug page; a private pack's is a 404."""

    def get(self, request, *args, **kwargs):
        self.shared = _shared_pack(kwargs["token"])
        if self.shared.is_public:
            return redirect("packs:attribution_pack", self.shared.slug)
        return _unindexed(super().get(request, *args, **kwargs))

    def get_pack(self) -> Pack:
        return self.shared

    def urls(self, pack: Pack) -> dict:
        return {
            "page_url": pack.get_share_url(),
            "attribution_url": reverse("packs:shared_attribution", args=[pack.share_token]),
        }


class AttributionAssetsView(AttributionPageMixin, PacksPageMixin, TemplateView):
    """Asset attribution, /attribution/assets/: the member's own library, 12 to a
    page, filtered by search (`q`), license type (`license`, repeatable) and credit
    rule (`credit`, repeatable). The filters' HTMX requests get the results
    fragment, and the address keeps every choice."""

    template_name = "packs/attribution_assets.html"
    attribution_page = "assets"

    def get_template_names(self):
        if _wants_fragment(self.request):
            return ["packs/partials/attribution_assets_results.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user, params = self.request.user, self.request.GET
        keys, credits = clean_license_params(params)
        query = params.get("q") or ""
        results = filter_library(
            user,
            {"q": query, "page": params.get("page") or "1"},
            licenses=license_filter(user, keys, credits),
        )
        entries = list(results.page.object_list)
        for entry in entries:
            entry.credit = credit_line(entry.asset)
        types, rules = license_choices(user, keys, credits)
        state = {"q": results.params.q, "license": keys, "credit": credits}
        context.update(
            results=results,
            entries=entries,
            query=results.params.q,
            filtered=bool(keys or credits),
            license_types=types,
            credit_rules=rules,
            state_query=urlencode({k: v for k, v in state.items() if v}, doseq=True),
            library_empty=not SavedAsset.objects.for_user(user).exists(),
        )
        return context


class AssetAttributionView(AttributionPageMixin, PacksPageMixin, TemplateView):
    """One asset's attribution, /attribution/assets/<id>/: the member's own entry
    (a 404 for anyone else's), with its license's terms, the credit it needs,
    the formal notice to copy and the member's packs it's in."""

    template_name = "packs/attribution_asset.html"
    attribution_page = "assets"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        entries = SavedAsset.objects.for_user(self.request.user).select_related("asset")
        entry = get_object_or_404(entries, pk=self.kwargs["pk"])
        entry.credit = credit_line(entry.asset)
        credits = pack_credits([entry])
        context.update(
            entry=entry,
            asset=entry.asset,
            group=credits.groups[0],
            credits=credits,
            notice=credits.notice(f'"{entry.asset.title}"', source_url=entry.asset.source_url),
            credit_lines=credits.credit_lines(),
            packs=Pack.objects.filter(items__saved_asset=entry).order_by("title").distinct(),
        )
        return context
