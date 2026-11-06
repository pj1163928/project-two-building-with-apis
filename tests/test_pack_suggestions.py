"""Suggested for this pack and Find more from providers (Phase 10).

TDD: suggest_assets() ranking (shared-tag groups highest first, no shared
tags and the pack's own assets left out; ties by title A–Z then id) and
add_suggestion() (a new To review entry, or the member's entry reused
untouched). Also the builder's section, Add, Find more and the access rules.

App tests, so provider functions are replaced with `monkeypatch`.
"""

import json
import re
from urllib.parse import parse_qs, urlsplit

import pytest
from django.test import Client
from django.urls import reverse

from catalog.models import Asset, SavedAsset, Tag
from packs import services
from packs.models import Pack
from packs.services import add_suggestion, add_to_pack
from packs.suggestions import SUGGESTION_LIMIT, find_more, suggest_assets
from providers import PROVIDERS

pytestmark = pytest.mark.django_db


@pytest.fixture
def pack(member):
    return Pack.objects.create_pack(
        member, "Medieval Village", "A market square.", "stone, wood, medieval"
    )


@pytest.fixture
def other_member(django_user_model, password):
    return django_user_model.objects.create_user(username="other_member", password=password)


@pytest.fixture
def tagged_asset(make_asset):
    """A stored Asset with the given tags (normalized names)."""

    def make(external_id, tags, **fields):
        asset = make_asset(external_id=external_id, **fields)
        asset.tags.set(Tag.objects.from_names(tags))
        return asset

    return make


# ---------------------------------------------------------------- TDD: ranking


def test_suggestions_rank_by_shared_tags_and_leave_out_no_overlap_and_the_packs_own(
    pack, member, tagged_asset
):
    three = tagged_asset("three", ["stone", "wood", "medieval", "moss"])
    two_a = tagged_asset("two_a", ["stone", "wood"])
    two_b = tagged_asset("two_b", ["wood", "medieval", "roof"])
    one = tagged_asset("one", ["stone"])
    tagged_asset("none", ["metal", "sci-fi"])
    in_pack = tagged_asset("in_pack", ["stone", "wood", "medieval"])
    add_to_pack(pack, SavedAsset.objects.create(user=member, asset=in_pack))

    suggestions = suggest_assets(pack)

    counts = [asset.shared_tags for asset in suggestions]
    assert counts == sorted(counts, reverse=True) == [3, 2, 2, 1]
    groups = {}
    for asset in suggestions:
        groups.setdefault(asset.shared_tags, set()).add(asset.pk)
    assert groups == {3: {three.pk}, 2: {two_a.pk, two_b.pk}, 1: {one.pk}}


def test_equal_counts_break_ties_by_title_a_to_z_ignoring_case_then_by_id(pack, tagged_asset):
    # Made in an order that differs from the expected one, so the id alone can't pass.
    cobble = tagged_asset("cobble", ["stone"], title="Cobble Path")
    barn = tagged_asset("barn", ["wood"], title="barn door")
    arch_first = tagged_asset("arch_1", ["medieval"], title="Arch")
    arch_second = tagged_asset("arch_2", ["stone"], title="Arch")
    zinc = tagged_asset("zinc", ["stone", "wood"], title="Zinc Roof")

    order = [asset.pk for asset in suggest_assets(pack)]

    # The bigger group still leads; inside the group of 1: A–Z with case ignored, then id.
    assert order == [zinc.pk, arch_first.pk, arch_second.pk, barn.pk, cobble.pk]


# ---------------------------------------------------------------- TDD: adding a suggestion


@pytest.fixture
def no_providers(monkeypatch):
    """Every provider function fails the test if called: a suggestion is already stored."""

    def refuse(*args, **kwargs):
        raise AssertionError("A provider was called.")

    for provider in PROVIDERS:
        for name in ("search", "get_details", "search_records", "fetch_record"):
            monkeypatch.setattr(provider, name, refuse)


def test_adding_a_suggestion_saves_it_as_to_review_or_reuses_the_entry_untouched(
    pack, member, tagged_asset, no_providers
):
    new = tagged_asset("new_one", ["stone"])
    known = tagged_asset("known_one", ["wood"])
    entry = SavedAsset.objects.create(
        user=member, asset=known, status=SavedAsset.Status.APPROVED, rating=4, notes="Used it."
    )

    add_suggestion(pack, new)
    add_suggestion(pack, known)

    made = SavedAsset.objects.filter(user=member, asset=new).first()
    assert made is not None, "The suggestion wasn't saved to the library."
    assert (made.status, made.rating, made.notes) == (SavedAsset.Status.TO_REVIEW, None, "")
    entry.refresh_from_db()
    assert (entry.status, entry.rating, entry.notes) == (SavedAsset.Status.APPROVED, 4, "Used it.")
    assert SavedAsset.objects.filter(user=member).count() == 2
    assert [item.saved_asset for item in pack.ordered_items()] == [made, entry]


# ---------------------------------------------------------------- the rest of add_suggestion()


def test_a_failed_add_leaves_no_new_library_entry_behind(
    pack, member, tagged_asset, no_providers, monkeypatch
):
    new = tagged_asset("new_one", ["stone"])

    def fail(*args, **kwargs):
        raise RuntimeError("The add failed part-way.")

    monkeypatch.setattr(services, "add_to_pack", fail)
    with pytest.raises(RuntimeError):
        add_suggestion(pack, new)
    assert not SavedAsset.objects.filter(user=member).exists()
    assert not pack.items.exists()


def test_adding_a_suggestion_already_in_the_pack_changes_nothing(pack, member, tagged_asset):
    asset = tagged_asset("in_pack", ["stone"])
    entry = SavedAsset.objects.create(user=member, asset=asset)
    item, _ = add_to_pack(pack, entry)
    assert add_suggestion(pack, asset) == (entry, False, item)
    assert pack.items.count() == 1


def test_adding_a_suggestion_reports_whether_it_made_a_library_entry(pack, tagged_asset):
    asset = tagged_asset("new_one", ["stone"])
    assert add_suggestion(pack, asset)[1] is True


# ---------------------------------------------------------------- suggest_assets(), more


def test_suggestions_stop_at_the_limit(pack, tagged_asset):
    for number in range(SUGGESTION_LIMIT + 3):
        tagged_asset(f"asset_{number}", ["stone"])
    assert len(suggest_assets(pack)) == SUGGESTION_LIMIT


def test_a_pack_with_no_tags_has_no_suggestions(member, tagged_asset):
    bare = Pack.objects.create_pack(member, "Bare")
    tagged_asset("stone", ["stone"])
    assert suggest_assets(bare) == []


def test_another_members_entry_or_pack_never_changes_the_suggestions(
    pack, other_member, tagged_asset
):
    asset = tagged_asset("shared", ["stone", "wood"])
    before = [(a.pk, a.shared_tags) for a in suggest_assets(pack)]
    theirs = SavedAsset.objects.create(user=other_member, asset=asset, notes="SENTINEL", rating=1)
    their_pack = Pack.objects.create_pack(other_member, "Theirs", tags="stone, wood")
    add_to_pack(their_pack, theirs)
    assert [(a.pk, a.shared_tags) for a in suggest_assets(pack)] == before == [(asset.pk, 2)]


# ---------------------------------------------------------------- find_more()


def test_find_more_searches_the_most_used_tags_for_the_packs_main_type(pack, member, tagged_asset):
    # "wood" is on three assets, "stone" on two, "medieval" on one.
    tagged_asset("a", ["wood", "stone"], kind="model")
    tagged_asset("b", ["wood", "stone"], kind="model")
    tagged_asset("c", ["wood", "medieval"], kind="sound")
    for asset in Asset.objects.filter(external_id__in=["a", "b", "c"]):
        add_to_pack(pack, SavedAsset.objects.create(user=member, asset=asset))

    result = find_more(pack)

    assert (result.kind, result.query) == ("model", "wood stone")
    params = parse_qs(urlsplit(result.url).query)
    assert urlsplit(result.url).path == reverse("catalog:discover")
    assert params == {"type": ["model"], "q": ["wood stone"]}


def test_find_more_breaks_ties_a_to_z_and_uses_textures_for_an_empty_pack(member):
    # No asset carries these tags, so they tie at 0 and go A–Z.
    pack = Pack.objects.create_pack(member, "Fresh", tags="wood, alley, stone")
    result = find_more(pack)
    assert (result.kind, result.query) == ("texture", "alley stone")


def test_find_more_ties_on_type_follow_discovers_order(pack, member, tagged_asset):
    for external_id, kind in (("s", "sound"), ("h", "hdri")):
        asset = tagged_asset(external_id, ["stone"], kind=kind)
        add_to_pack(pack, SavedAsset.objects.create(user=member, asset=asset))
    assert find_more(pack).kind == "hdri"


def test_find_more_is_none_for_a_pack_with_no_tags(member):
    assert find_more(Pack.objects.create_pack(member, "Bare")) is None


# ---------------------------------------------------------------- the builder's section


HTMX = {"HX-Request": "true"}


def _section(html):
    return html.split('id="pack-suggestions"', 1)[1].split("</section>", 1)[0]


def _text(html):
    return " ".join(re.sub(r"<[^>]+>", " ", html).split())


def test_the_builder_lists_suggestions_with_shared_tags_and_find_more(
    member_client, member, pack, tagged_asset
):
    best = tagged_asset("best", ["stone", "wood"], title="Mossy Cobble")
    saved = tagged_asset("saved", ["stone"], title="Grey Slate")
    SavedAsset.objects.create(user=member, asset=saved)
    tagged_asset("unrelated", ["metal"], title="Steel Panel")

    html = member_client.get(reverse("packs:builder", args=[pack.pk])).content.decode()

    assert "Suggested for this pack" in html
    section = _section(html)
    text = _text(section)
    assert text.index("Mossy Cobble") < text.index("Grey Slate")
    assert "2 shared tags" in text and "1 shared tag" in text and "Steel Panel" not in text
    assert text.count("In your library") == 1
    assert f'id="suggestion-{best.pk}"' in section and 'name="asset"' in section
    assert reverse("packs:suggestion_add", args=[pack.pk]) in section
    assert "isn't in your library saves it there as To review" in text
    assert 'id="pack-find-more"' in section and "Find more from providers" in text
    assert "hx-post" in section and "Save" not in text


def test_in_your_library_and_private_review_come_only_from_the_owners_own_entries(
    member_client, pack, other_member, tagged_asset
):
    asset = tagged_asset("theirs", ["stone"], title="Their Find")
    SavedAsset.objects.create(
        user=other_member, asset=asset, notes="SENTINEL-NOTE", rating=5, status="approved"
    )
    section = _section(member_client.get(reverse("packs:builder", args=[pack.pk])).content.decode())
    assert "Their Find" in section
    assert "In your library" not in section
    for private in ("SENTINEL-NOTE", other_member.username, "Approved"):
        assert private not in section


def test_a_pack_with_no_tags_shows_hints_instead_of_suggestions_or_an_empty_search(
    member_client, member, tagged_asset
):
    bare = Pack.objects.create_pack(member, "Bare")
    tagged_asset("stone", ["stone"])
    section = _section(member_client.get(reverse("packs:builder", args=[bare.pk])).content.decode())
    text = _text(section)
    assert "Add tags to this pack to see suggestions." in text
    assert "Add tags to this pack to find more from providers." in text
    assert 'id="pack-find-more"' not in section and reverse("catalog:discover") not in section


def test_no_matching_assets_says_so(member_client, pack):
    section = _section(member_client.get(reverse("packs:builder", args=[pack.pk])).content.decode())
    assert "No other assets share this pack's tags yet." in _text(section)


def test_the_find_more_link_opens_discover_with_the_packs_tags(member_client, pack):
    section = _section(member_client.get(reverse("packs:builder", args=[pack.pk])).content.decode())
    link = re.search(r'<a href="([^"]+)" id="pack-find-more"', section).group(1)
    params = parse_qs(urlsplit(link.replace("&amp;", "&")).query)
    assert params["type"] == ["texture"] and params["q"] == [find_more(pack).query]
    assert set(params["q"][0].split()) <= {"stone", "wood", "medieval"}


def test_the_suggestions_reload_on_both_events_independently(member_client, pack):
    section = _section(member_client.get(reverse("packs:builder", args=[pack.pk])).content.decode())
    trigger = re.search(r'hx-trigger="([^"]+)"', section).group(1)
    assert [part.strip() for part in trigger.split(",")] == [
        "packItemsChanged from:body",
        "packTagsChanged from:body",
    ]
    assert f'hx-get="{reverse("packs:suggestions", args=[pack.pk])}"' in section


def test_the_suggestions_fragment_for_htmx_and_the_builder_otherwise(
    member_client, pack, tagged_asset
):
    tagged_asset("cobble", ["stone"], title="Cobble Path")
    url = reverse("packs:suggestions", args=[pack.pk])
    fragment = member_client.get(url, headers=HTMX)
    html = fragment.content.decode()
    assert fragment.status_code == 200
    assert 'id="pack-suggestions"' in html and "Cobble Path" in html and "<html" not in html
    page = member_client.get(url)
    assert page.status_code == 302 and page.url == reverse("packs:builder", args=[pack.pk])


# ---------------------------------------------------------------- Add, through the view


def _add(client, pack, asset_id, **headers):
    return client.post(
        reverse("packs:suggestion_add", args=[pack.pk]), {"asset": asset_id}, headers=headers
    )


def test_adding_a_new_suggestion_saves_it_and_sends_the_count_out_of_band(
    member_client, member, pack, tagged_asset, no_providers
):
    asset = tagged_asset("cobble", ["stone"], title="Cobble Path")
    response = _add(member_client, pack, asset.pk, **HTMX)
    html = response.content.decode()
    assert response.status_code == 200
    assert 'id="pack-items"' in html and "Cobble Path" in html
    assert 'id="saved-count" class="ml-auto" hx-swap-oob="true"' in html
    assert '<b class="text-fg-strong">1</b> saved' in html
    entry = SavedAsset.objects.get(user=member, asset=asset)
    assert entry.status == SavedAsset.Status.TO_REVIEW
    assert entry.status_changes.get().changed_by == member
    assert pack.items.get().saved_asset == entry
    assert set(json.loads(response["HX-Trigger"])) == {"packItemsChanged"}


def test_adding_a_saved_suggestion_keeps_the_count_where_it_is(
    member_client, member, pack, tagged_asset, no_providers
):
    asset = tagged_asset("cobble", ["stone"])
    SavedAsset.objects.create(user=member, asset=asset, status="testing", notes="Keep.")
    html = _add(member_client, pack, asset.pk, **HTMX).content.decode()
    assert "hx-swap-oob" not in html.split('id="saved-count"', 1)[-1][:40]
    assert 'id="saved-count"' not in html
    entry = SavedAsset.objects.get(user=member, asset=asset)
    assert (entry.status, entry.notes) == ("testing", "Keep.")
    assert pack.items.get().saved_asset == entry


def test_an_unknown_or_missing_asset_is_a_404_and_adds_nothing(member_client, member, pack):
    for value in ("999999", "abc", ""):
        assert _add(member_client, pack, value, **HTMX).status_code == 404
    assert not pack.items.exists() and not SavedAsset.objects.filter(user=member).exists()


def test_a_plain_post_adds_and_goes_back_to_the_builder(member_client, pack, tagged_asset):
    asset = tagged_asset("cobble", ["stone"])
    response = _add(member_client, pack, asset.pk)
    assert response.status_code == 302 and response.url == reverse("packs:builder", args=[pack.pk])
    assert pack.items.count() == 1


def test_get_on_the_add_url_is_refused(member_client, pack):
    assert member_client.get(reverse("packs:suggestion_add", args=[pack.pk])).status_code == 405


# ---------------------------------------------------------------- the two events stay apart


def test_saving_tags_sends_only_packtagschanged(member_client, pack):
    url = reverse("packs:details", args=[pack.pk])
    tags = member_client.post(url, {"tags": "stone, roof"}, headers=HTMX)
    assert set(json.loads(tags["HX-Trigger"])) == {"packTagsChanged"}
    title = member_client.post(url, {"title": "Renamed"}, headers=HTMX)
    assert "HX-Trigger" not in title


def test_changing_the_items_sends_only_packitemschanged(member_client, member, pack, make_asset):
    entry = SavedAsset.objects.create(user=member, asset=make_asset(external_id="brick"))
    response = member_client.post(
        reverse("packs:add_item", args=[pack.pk]), {"entry": entry.pk}, headers=HTMX
    )
    assert set(json.loads(response["HX-Trigger"])) == {"packItemsChanged"}


# ---------------------------------------------------------------- access (also in test_access_control.py)


def test_a_visitor_is_sent_to_sign_in_and_back_to_the_builder_and_nothing_is_saved(
    pack, tagged_asset
):
    visitor = Client()
    asset = tagged_asset("cobble", ["stone"])
    builder = reverse("packs:builder", args=[pack.pk])
    login = f"{reverse('accounts:login')}?next={builder}"
    assert (
        visitor.get(reverse("packs:suggestions", args=[pack.pk]), headers=HTMX)["HX-Redirect"]
        == login
    )
    assert _add(visitor, pack, asset.pk).url == login
    assert not SavedAsset.objects.exists() and not pack.items.exists()


def test_another_members_pack_is_a_404_for_both_urls_and_saves_nothing(
    pack, other_member, password, tagged_asset
):
    asset = tagged_asset("cobble", ["stone"])
    intruder = Client()
    intruder.force_login(other_member)
    assert (
        intruder.get(reverse("packs:suggestions", args=[pack.pk]), headers=HTMX).status_code == 404
    )
    assert _add(intruder, pack, asset.pk, **HTMX).status_code == 404
    assert not SavedAsset.objects.exists() and not pack.items.exists()


def test_adding_a_suggestion_needs_csrf_and_works_with_the_pages_header(member, pack, tagged_asset):
    asset = tagged_asset("cobble", ["stone"])
    client = Client(enforce_csrf_checks=True)
    client.force_login(member)
    assert _add(client, pack, asset.pk, **HTMX).status_code == 403
    assert not SavedAsset.objects.exists()
    page = client.get(reverse("packs:builder", args=[pack.pk])).content.decode()
    token = re.search(r"hx-headers='\{\"X-CSRFToken\": \"([^\"]+)\"\}'", page).group(1)
    assert _add(client, pack, asset.pk, **HTMX, **{"X-CSRFToken": token}).status_code == 200
    assert pack.items.count() == 1
