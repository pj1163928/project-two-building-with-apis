"""The pack pages: the member's packs, New pack, the builder and its autosaving
controls, Add from my library, the Add to pack picker on the library and
Discover, the Remove dialog that lists packs, and the drawer's pack list.

App tests, so provider functions are replaced with `monkeypatch`.
"""

import re

import pytest
from django.urls import reverse

from catalog.models import Asset, SavedAsset
from packs.models import Pack, PackItem
from packs.services import add_to_pack
from providers import ProviderError, polyhaven
from tests.test_library_save import full_record

pytestmark = pytest.mark.django_db

HTMX = {"HX-Request": "true"}
VARIANTS = [
    {"label": "1K JPG", "files": [], "total_size": None},
    {"label": "2K JPG", "files": [], "total_size": None},
    {"label": "4K PNG", "files": [], "total_size": None},
]


@pytest.fixture
def pack(member):
    return Pack.objects.create_pack(member, "Medieval Village", "A market square.", "stone, wood")


@pytest.fixture
def entry(member, make_asset):
    return SavedAsset.objects.create(
        user=member, asset=make_asset(external_id="red_brick_03", variants=VARIANTS)
    )


@pytest.fixture
def item(pack, entry):
    return add_to_pack(pack, entry)[0]


@pytest.fixture
def other(django_user_model, password):
    return django_user_model.objects.create_user(username="other_member", password=password)


def _text(html):
    return " ".join(re.sub(r"<[^>]+>", " ", html).split())


# ---------------------------------------------------------------- the member's packs


def test_the_packs_page_lists_only_the_members_own_packs(member_client, pack, other):
    Pack.objects.create_pack(other, "Their Secret Pack")
    html = member_client.get(reverse("packs:list")).content.decode()
    assert "Medieval Village" in html and "Their Secret Pack" not in html
    assert f'href="{reverse("packs:builder", args=[pack.pk])}"' in html
    card = html.split('id="pack-list"', 1)[1]
    assert "Private" in card and "0 items" in card and "stone" in card
    # The side panel lists them too, with New pack.
    nav = html.split('id="pack-nav"', 1)[1].split("</section>", 1)[0]
    assert "Medieval Village" in nav and reverse("packs:create") in nav


def test_with_no_packs_the_page_says_what_to_do(member_client):
    text = _text(member_client.get(reverse("packs:list")).content.decode())
    assert "You have no packs yet." in text and "The packs you create are listed here." in text


def test_new_pack_creates_a_private_pack_with_tidy_tags_and_opens_its_builder(
    member_client, member
):
    response = member_client.post(
        reverse("packs:create"),
        {"title": "Quarry", "description": "Cliffs.", "tags": "Rocks, rock, 2048,  Mossy  Stones"},
    )
    pack = Pack.objects.get(owner=member)
    assert response.status_code == 302 and response.url == reverse("packs:builder", args=[pack.pk])
    assert (pack.title, pack.description, pack.is_public) == ("Quarry", "Cliffs.", False)
    assert sorted(pack.tags.values_list("name", flat=True)) == ["mossy stone", "rock"]


def test_new_pack_needs_a_title(member_client):
    response = member_client.post(reverse("packs:create"), {"title": "  ", "tags": "stone"})
    assert response.status_code == 200 and "Give the pack a title." in response.content.decode()
    assert not Pack.objects.exists()


# ---------------------------------------------------------------- the builder


def test_the_builder_shows_details_items_and_add_from_my_library(member_client, pack, item):
    html = member_client.get(reverse("packs:builder", args=[pack.pk])).content.decode()
    assert '<h1 id="pack-title"' in html and 'value="Medieval Village"' in html
    assert "A market square." in html and 'value="stone, wood"' in html
    assert 'id="pack-visibility"' in html and 'value="private" checked' in html
    row = html.split(f'id="item-{item.pk}"', 1)[1].split("</li>", 1)[0]
    assert '<option value="2K JPG" selected>' in row
    # A blank import path shows the default as its placeholder.
    assert 'placeholder="textures/red_brick_03/"' in row
    assert "Move up" in row and "Move down" in row and "Remove" in row
    assert 'id="pack-library-search"' in html
    # Every control saves on its own: no Save button anywhere in the builder.
    assert ">Save<" not in html and 'type="submit">Save' not in html
    # Nothing private from the library entry shows in the builder.
    assert "To review" not in _text(row)


def test_details_save_one_field_at_a_time(member_client, pack):
    url = reverse("packs:details", args=[pack.pk])
    response = member_client.post(url, {"title": "Old Town"}, headers=HTMX)
    assert response.status_code == 200
    html = response.content.decode()
    assert 'data-save-status="saved"' in html
    # The heading and the side panel's row follow the rename, out of band.
    assert '<h1 id="pack-title"' in html and 'hx-swap-oob="true">Old Town</h1>' in html
    assert f'id="pack-nav-{pack.pk}"' in html
    response = member_client.post(url, {"tags": "Bricks, Walls"}, headers=HTMX)
    pack.refresh_from_db()
    assert (pack.title, pack.description) == ("Old Town", "A market square.")
    assert pack.tags_text == "brick, wall"
    assert "pack-title" not in response.content.decode()


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ({"title": ""}, "Give the pack a title."),
        ({"title": "x" * 121}, "A title can be up to 120 characters."),
        ({}, "There was nothing to save."),
    ],
)
def test_a_bad_detail_is_a_400_that_saves_nothing(member_client, pack, data, message):
    response = member_client.post(reverse("packs:details", args=[pack.pk]), data, headers=HTMX)
    assert response.status_code == 400 and message in response.content.decode()
    pack.refresh_from_db()
    assert pack.title == "Medieval Village"


def test_the_public_switch_saves_at_once_and_back(member_client, pack):
    url = reverse("packs:visibility", args=[pack.pk])
    response = member_client.post(url, {"visibility": "public"}, headers=HTMX)
    pack.refresh_from_db()
    assert pack.is_public and "Anyone can view and export it." in response.content.decode()
    member_client.post(url, {"visibility": "private"}, headers=HTMX)
    pack.refresh_from_db()
    assert not pack.is_public
    assert member_client.post(url, {"visibility": "yes"}, headers=HTMX).status_code == 400


def test_deleting_a_pack_returns_to_the_packs_and_keeps_the_library(member_client, pack, item):
    response = member_client.post(reverse("packs:delete", args=[pack.pk]))
    assert response.status_code == 302 and response.url == reverse("packs:list")
    assert not Pack.objects.exists() and not PackItem.objects.exists()
    assert SavedAsset.objects.filter(pk=item.saved_asset_id).exists()


def test_the_builder_offers_a_confirm_before_deleting(member_client, pack):
    html = member_client.get(reverse("packs:builder", args=[pack.pk])).content.decode()
    dialog = html.split('<dialog id="pack-delete-dialog"', 1)[1].split("</dialog>", 1)[0]
    assert f'action="{reverse("packs:delete", args=[pack.pk])}"' in dialog
    assert "Everything stays in your library" in dialog
    assert 'data-dialog-open="pack-delete-dialog"' in html


# ---------------------------------------------------------------- items through HTMX


def test_changing_the_variant_saves_through_htmx(member_client, pack, item):
    url = reverse("packs:item_update", args=[pack.pk, item.pk])
    response = member_client.post(url, {"preferred_variant": "4K PNG"}, headers=HTMX)
    assert response.status_code == 200
    assert f'id="item-{item.pk}-status"' in response.content.decode()
    item.refresh_from_db()
    assert (item.preferred_variant, item.import_path) == ("4K PNG", "")


def test_changing_the_import_path_saves_through_htmx(member_client, pack, item):
    url = reverse("packs:item_update", args=[pack.pk, item.pk])
    member_client.post(url, {"import_path": "  village\\walls/ "}, headers=HTMX)
    item.refresh_from_db()
    assert (item.preferred_variant, item.import_path) == ("2K JPG", "village/walls/")
    # Blank again: the default applies.
    member_client.post(url, {"import_path": ""}, headers=HTMX)
    item.refresh_from_db()
    assert item.import_path == ""


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ({"preferred_variant": "8K EXR"}, "Choose one of this asset&#x27;s variants."),
        ({"import_path": "/etc/"}, "Use a path inside your project"),
        ({"import_path": "C:/games/"}, "Use a path inside your project"),
        ({"import_path": "textures/../../secrets/"}, "can&#x27;t climb out"),
        ({"import_path": "a" * 301}, "up to 300 characters"),
    ],
)
def test_a_bad_item_value_is_a_400_that_saves_nothing(member_client, pack, item, data, message):
    url = reverse("packs:item_update", args=[pack.pk, item.pk])
    response = member_client.post(url, data, headers=HTMX)
    assert response.status_code == 400 and message in response.content.decode()
    item.refresh_from_db()
    assert (item.preferred_variant, item.import_path) == ("2K JPG", "")


def test_moving_an_item_saves_the_order_through_htmx(member_client, pack, item, member, make_asset):
    second, _ = add_to_pack(
        pack, SavedAsset.objects.create(user=member, asset=make_asset(external_id="moss"))
    )
    url = reverse("packs:item_move", args=[pack.pk, second.pk])
    response = member_client.post(url, {"direction": "up"}, headers=HTMX)
    assert response.status_code == 200
    assert "packItemsChanged" in response["HX-Trigger"]
    html = response.content.decode()
    assert html.index(f'id="item-{second.pk}"') < html.index(f'id="item-{item.pk}"')
    assert [i.pk for i in pack.ordered_items()] == [second.pk, item.pk]
    assert member_client.post(url, {"direction": "sideways"}, headers=HTMX).status_code == 400


def test_removing_an_item_keeps_the_library_entry(member_client, pack, item):
    url = reverse("packs:item_remove", args=[pack.pk, item.pk])
    response = member_client.post(url, headers=HTMX)
    assert response.status_code == 200 and "This pack is empty." in response.content.decode()
    assert not PackItem.objects.exists()
    assert SavedAsset.objects.filter(pk=item.saved_asset_id).exists() and Asset.objects.exists()


def test_add_from_my_library_filters_as_you_type_and_marks_whats_in(
    member_client, pack, item, member, make_asset
):
    SavedAsset.objects.create(
        user=member, asset=make_asset(external_id="moss", title="Mossy Ground")
    )
    url = reverse("packs:library_search", args=[pack.pk])
    html = member_client.get(url, headers=HTMX).content.decode()
    assert "Mossy Ground" in html and "Red Brick 03" in html
    assert f'id="pick-{item.saved_asset_id}"' in html and "In pack" in html
    html = member_client.get(url, {"q": "moss"}, headers=HTMX).content.decode()
    assert "Mossy Ground" in html and "Red Brick 03" not in html
    html = member_client.get(url, {"q": "nothing"}, headers=HTMX).content.decode()
    assert "Nothing in your library matches “nothing”." in html
    # Opened directly, it's the builder.
    assert member_client.get(url).url == reverse("packs:builder", args=[pack.pk])


def test_adding_from_the_library_swaps_the_item_list(member_client, pack, entry):
    url = reverse("packs:add_item", args=[pack.pk])
    response = member_client.post(url, {"entry": entry.pk}, headers=HTMX)
    assert response.status_code == 200 and "packItemsChanged" in response["HX-Trigger"]
    assert response.content.decode().strip().startswith('<section id="pack-items"')
    assert pack.items.get().saved_asset == entry
    # Again: still one item.
    member_client.post(url, {"entry": entry.pk}, headers=HTMX)
    assert pack.items.count() == 1


def test_add_from_my_library_never_lists_another_members_entries(
    member_client, pack, other, make_asset
):
    SavedAsset.objects.create(user=other, asset=make_asset(external_id="x", title="Their Find"))
    html = member_client.get(reverse("packs:library_search", args=[pack.pk]), headers=HTMX)
    assert "Their Find" not in html.content.decode()


# ---------------------------------------------------------------- the Add to pack picker


def test_the_library_picker_lists_only_the_members_own_packs(member_client, pack, entry, other):
    Pack.objects.create_pack(other, "Their Secret Pack")
    held = Pack.objects.create_pack(entry.user, "Castle")
    add_to_pack(held, entry)
    html = member_client.get(reverse("packs:picker"), {"entry": entry.pk}, headers=HTMX)
    html = html.content.decode()
    assert "Medieval Village" in html and "Castle" in html
    assert "Their Secret Pack" not in html
    # The pack it's already in shows as such, with no button to add it again.
    assert f'action="{reverse("packs:picker_add", args=[held.pk])}"' not in html
    assert f'action="{reverse("packs:picker_add", args=[pack.pk])}"' in html
    assert "In pack" in html


def test_the_picker_with_no_packs_offers_a_new_one(member_client, entry):
    html = member_client.get(reverse("packs:picker"), {"entry": entry.pk}, headers=HTMX)
    html = html.content.decode()
    assert "You don't have any packs yet." in html and reverse("packs:create") in html


def test_choosing_a_pack_in_the_library_picker_adds_the_entry(member_client, pack, entry):
    url = reverse("packs:picker_add", args=[pack.pk])
    response = member_client.post(url, {"entry": entry.pk}, headers=HTMX)
    html = response.content.decode()
    assert response.status_code == 200 and "Added to “Medieval Village”." in html
    assert pack.items.get().saved_asset == entry
    assert "In pack" in html


def test_a_discover_picker_saves_the_result_first_as_to_review(
    member_client, member, pack, monkeypatch
):
    monkeypatch.setattr(polyhaven, "fetch_record", lambda external_id: full_record())
    url = reverse("packs:picker_add", args=[pack.pk])
    data = {"provider": "polyhaven", "external_id": "red_brick_03"}
    response = member_client.post(url, data, headers=HTMX)
    html = response.content.decode()
    entry = SavedAsset.objects.get(user=member)
    assert entry.status == "to_review" and pack.items.get().saved_asset == entry
    assert "Added to “Medieval Village”." in html
    # The status bar's saved count follows, out of band.
    assert 'id="saved-count" class="ml-auto" hx-swap-oob="true"' in html


def test_a_discover_picker_reuses_an_entry_untouched(member_client, pack, entry, monkeypatch):
    SavedAsset.objects.filter(pk=entry.pk).update(status="approved", rating=5, notes="Keep.")

    def must_not_fetch(external_id):
        raise AssertionError("fetch_record() was called for an asset already stored")

    monkeypatch.setattr(polyhaven, "fetch_record", must_not_fetch)
    data = {"provider": "polyhaven", "external_id": "red_brick_03"}
    member_client.post(reverse("packs:picker_add", args=[pack.pk]), data, headers=HTMX)
    entry.refresh_from_db()
    assert (entry.status, entry.rating, entry.notes) == ("approved", 5, "Keep.")
    assert pack.items.get().saved_asset == entry


def test_a_discover_pickers_provider_error_shows_and_saves_nothing(
    member_client, pack, monkeypatch
):
    def failing(external_id):
        raise ProviderError("Poly Haven is busy right now. Try again in a minute.")

    monkeypatch.setattr(polyhaven, "fetch_record", failing)
    data = {"provider": "polyhaven", "external_id": "red_brick_03"}
    response = member_client.post(reverse("packs:picker_add", args=[pack.pk]), data, headers=HTMX)
    assert response.status_code == 200
    assert "Poly Haven is busy right now. Try again in a minute." in response.content.decode()
    assert not SavedAsset.objects.exists() and not PackItem.objects.exists()
    assert not Asset.objects.exists()


@pytest.mark.parametrize(
    "data",
    [{}, {"provider": "sketchfab", "external_id": "x"}, {"provider": "polyhaven"}, {"entry": "x"}],
)
def test_the_picker_needs_an_asset_before_any_provider_call(member_client, pack, data):
    assert member_client.get(reverse("packs:picker"), data, headers=HTMX).status_code == 400
    response = member_client.post(reverse("packs:picker_add", args=[pack.pk]), data, headers=HTMX)
    assert response.status_code == 400
    assert not SavedAsset.objects.exists()


def test_discover_cards_point_the_picker_at_their_provider_and_id(member_client, monkeypatch):
    from providers import ambientcg

    record = full_record(variants=())
    monkeypatch.setattr(polyhaven, "search_records", lambda *a, **k: [record])
    monkeypatch.setattr(ambientcg, "search_records", lambda *a, **k: [])
    url = reverse("catalog:discover_shelf", args=["texture", "polyhaven"])
    html = member_client.get(url, {"q": "brick"}, headers=HTMX).content.decode()
    picker = reverse("packs:picker")
    assert f'data-picker-url="{picker}?provider=polyhaven&amp;external_id=red_brick_03"' in html


# ---------------------------------------------------------------- Remove and the drawer


def test_remove_first_shows_the_packs_the_entry_will_leave(member_client, member, pack, item):
    castle = Pack.objects.create_pack(member, "Castle")
    add_to_pack(castle, item.saved_asset)
    url = reverse("catalog:remove", args=[item.saved_asset_id])
    html = member_client.get(url, headers=HTMX).content.decode()
    packs = html.split('id="remove-packs"', 1)[1].split("</ul>", 1)[0]
    assert re.findall(r"<span>([^<]+)</span>", packs) == ["Castle", "Medieval Village"]
    assert "these 2 packs" in html
    assert f'hx-post="{url}" hx-target="#library-results"' in html
    # Nothing is removed by looking.
    assert SavedAsset.objects.filter(pk=item.saved_asset_id).exists()


def test_remove_of_an_entry_in_no_pack_says_so(member_client, entry):
    html = member_client.get(reverse("catalog:remove", args=[entry.pk]), headers=HTMX)
    assert "It isn't in any of your packs." in html.content.decode()


def test_confirming_remove_takes_it_out_of_its_packs_only(
    member_client, member, pack, item, make_asset
):
    kept = add_to_pack(
        pack, SavedAsset.objects.create(user=member, asset=make_asset(external_id="moss"))
    )[0]
    url = reverse("catalog:remove", args=[item.saved_asset_id])
    response = member_client.post(
        url, headers={**HTMX, "HX-Current-URL": "http://testserver/library/"}
    )
    assert response.status_code == 200
    assert list(pack.items.all()) == [kept]
    assert Asset.objects.filter(external_id="red_brick_03").exists()


def test_the_drawer_lists_the_packs_its_entry_is_in(member_client, item):
    html = member_client.get(reverse("catalog:entry", args=[item.saved_asset_id]), headers=HTMX)
    packs = html.content.decode().split('id="entry-packs"', 1)[1].split("</ul>", 1)[0]
    assert "Medieval Village" in packs and "2K JPG" in packs
    assert reverse("packs:builder", args=[item.pack_id]) in packs
