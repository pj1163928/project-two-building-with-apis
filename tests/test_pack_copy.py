"""Save single items and Copy pack (Phase 11).

TDD: copy_pack() saving missing assets as To review while the copier's own
entries stay untouched; a copy that fails part-way leaving nothing behind;
and Save and Copy following the pack page's reader rule. Also the copy's
details, the single-item save, the pack page's buttons and the access rules.

App tests, so provider functions are replaced with `monkeypatch`.
"""

import re
from urllib.parse import quote

import pytest
from django.test import Client
from django.urls import reverse

from catalog.models import SavedAsset, StatusChange
from packs import services
from packs.models import Pack, PackItem
from packs.services import add_to_pack, copy_pack
from providers import PROVIDERS

pytestmark = pytest.mark.django_db


@pytest.fixture
def copier(django_user_model, password):
    return django_user_model.objects.create_user(username="copier", password=password)


@pytest.fixture
def no_providers(monkeypatch):
    """Every provider function fails the test if called: a pack's assets are stored."""

    def refuse(*args, **kwargs):
        raise AssertionError("A provider was called.")

    for provider in PROVIDERS:
        for name in ("search", "get_details", "search_records", "fetch_record"):
            monkeypatch.setattr(provider, name, refuse)


@pytest.fixture
def source_pack(member, make_asset):
    """A public pack of three of the owner's entries, each with the owner's review."""
    pack = Pack.objects.create_pack(member, "Medieval Village", "A market square.", "stone, wood")
    for external_id in ("brick", "roof", "well"):
        asset = make_asset(external_id=external_id, title=external_id.title())
        entry = SavedAsset.objects.create(
            user=member,
            asset=asset,
            notes="The owner's private note.",
            rating=5,
            status=SavedAsset.Status.APPROVED,
        )
        add_to_pack(pack, entry)
    pack.set_visibility("public")
    return pack


# ---------------------------------------------------------------- TDD: the copier's library


def test_copying_saves_missing_assets_as_to_review_and_leaves_existing_entries_untouched(
    source_pack, copier, no_providers
):
    roof = source_pack.items.get(saved_asset__asset__external_id="roof").asset
    mine = SavedAsset.objects.create(
        user=copier, asset=roof, notes="My own note.", rating=2, status=SavedAsset.Status.REJECTED
    )
    before = (mine.notes, mine.rating, mine.status, mine.saved_at)

    copy = copy_pack(source_pack, copier)

    entries = {entry.asset.external_id: entry for entry in SavedAsset.objects.for_user(copier)}
    assert set(entries) == {"brick", "roof", "well"}
    # Missing ones are new, To review, unrated and without the owner's notes.
    for external_id in ("brick", "well"):
        entry = entries[external_id]
        assert (entry.status, entry.rating, entry.notes) == (SavedAsset.Status.TO_REVIEW, None, "")
        assert entry.status_changes.get().changed_by == copier
    # The copier's own entry is the same row, unchanged, and still the only one.
    mine.refresh_from_db()
    assert entries["roof"].pk == mine.pk
    assert (mine.notes, mine.rating, mine.status, mine.saved_at) == before
    assert SavedAsset.objects.filter(user=copier, asset=roof).count() == 1
    # The copy's items point at the copier's entries; the owner's are untouched.
    assert {item.saved_asset.user_id for item in copy.items.all()} == {copier.pk}
    assert copy.items.count() == 3
    owners = SavedAsset.objects.for_user(source_pack.owner)
    assert {(e.status, e.rating) for e in owners} == {(SavedAsset.Status.APPROVED, 5)}
    assert not StatusChange.objects.filter(entry__user=source_pack.owner).exists()


# ---------------------------------------------------------------- TDD: one transaction


def test_a_copy_that_fails_part_way_leaves_nothing_behind(
    source_pack, copier, monkeypatch, no_providers
):
    real_save_asset = services.save_asset
    calls = []

    def fail_on_the_second_item(user, asset, **kwargs):
        calls.append(asset)
        if len(calls) == 2:
            raise RuntimeError("The copy failed part-way.")
        return real_save_asset(user, asset, **kwargs)

    monkeypatch.setattr(services, "save_asset", fail_on_the_second_item)
    packs_before, items_before = Pack.objects.count(), PackItem.objects.count()

    with pytest.raises(RuntimeError):
        copy_pack(source_pack, copier)

    assert len(calls) == 2  # it really failed part-way, after one item was copied
    assert Pack.objects.count() == packs_before
    assert not Pack.objects.filter(owner=copier).exists()
    assert PackItem.objects.count() == items_before
    assert not SavedAsset.objects.filter(user=copier).exists()
    assert not StatusChange.objects.filter(entry__user=copier).exists()


# ---------------------------------------------------------------- TDD: the reader rule


def _action_url(action, pack, *, by_link=False):
    """Copy pack, or Save on the pack's first item, by slug or by share link."""
    key = pack.share_token if by_link else pack.slug
    prefix = "shared_" if by_link else ""
    if action == "copy":
        return reverse(f"packs:{prefix}copy", args=[key])
    return reverse(f"packs:{prefix}save_item", args=[key, pack.ordered_items()[0].pk])


@pytest.mark.parametrize("action", ["copy", "save"])
def test_save_and_copy_follow_the_pack_pages_reader_rule(action, source_pack, copier, no_providers):
    def writes():
        return (
            Pack.objects.filter(owner=copier).count(),
            SavedAsset.objects.filter(user=copier).count(),
        )

    member = Client()
    member.force_login(copier)
    visitor = Client()

    # Another member's private pack, and an unlisted one by its slug: a 404, nothing written.
    source_pack.set_visibility("private")
    assert member.post(_action_url(action, source_pack)).status_code == 404
    source_pack.set_visibility("unlisted")
    assert member.post(_action_url(action, source_pack)).status_code == 404
    # A private pack's share link opens nothing either.
    source_pack.set_visibility("private")
    assert member.post(_action_url(action, source_pack, by_link=True)).status_code == 404
    assert writes() == (0, 0)

    # A visitor is sent to sign in and back to the pack's page, and nothing is written.
    for visibility, by_link in (("public", False), ("unlisted", True)):
        source_pack.set_visibility(visibility)
        page = source_pack.get_share_url() if by_link else source_pack.get_public_url()
        response = visitor.post(_action_url(action, source_pack, by_link=by_link))
        assert response.status_code == 302
        assert response["Location"] == f"{reverse('accounts:login')}?next={quote(page)}"
    assert Pack.objects.count() == 1 and SavedAsset.objects.count() == 3

    # The member can when they can read it: an unlisted pack by its link, a public one.
    source_pack.set_visibility("unlisted")
    member.post(_action_url(action, source_pack, by_link=True))
    assert writes() == ((1, 3) if action == "copy" else (0, 1))
    source_pack.set_visibility("public")
    member.post(_action_url(action, source_pack))
    assert writes() == ((2, 3) if action == "copy" else (0, 1))


# ---------------------------------------------------------------- the copy itself


def test_the_copy_is_private_titled_linked_and_matches_the_items_in_order(source_pack, copier):
    items = list(source_pack.ordered_items())
    items[0].preferred_variant, items[0].import_path = "4K PNG", "textures/brick/"
    items[0].save()
    # Positions with a gap and out of creation order, copied as they are.
    for item, position in zip(items, (5, 0, 2), strict=True):
        item.position = position
        item.save()
    source_pack.set_visibility("unlisted")  # it has a share token, which the copy must not

    copy = copy_pack(source_pack, copier)

    assert copy.owner == copier
    assert copy.title == "Medieval Village (copy)"
    assert copy.slug == "medieval-village-copy"
    assert copy.copied_from == source_pack
    assert copy.visibility == Pack.Visibility.PRIVATE and copy.share_token is None
    assert copy.description == source_pack.description
    assert set(copy.tags.values_list("name", flat=True)) == {"stone", "wood"}

    def shape(pack):
        return [
            (i.asset.external_id, i.preferred_variant, i.import_path, i.position)
            for i in pack.ordered_items()
        ]

    assert shape(copy) == shape(source_pack)
    assert shape(copy)[-1] == ("brick", "4K PNG", "textures/brick/", 5)


def test_a_long_title_is_shortened_so_the_copy_still_fits():
    from packs.models import TITLE_MAX_LENGTH
    from packs.services import copy_title

    title = copy_title("x" * TITLE_MAX_LENGTH)
    assert len(title) == TITLE_MAX_LENGTH and title.endswith("x (copy)")
    assert copy_title("Short") == "Short (copy)"


def test_the_owner_can_copy_their_own_pack_and_their_entries_stay(source_pack, member):
    entries_before = list(SavedAsset.objects.for_user(member).values_list("pk", "notes", "status"))

    copy = copy_pack(source_pack, member)

    assert copy.title == "Medieval Village (copy)" and copy.owner == member
    assert (
        list(SavedAsset.objects.for_user(member).values_list("pk", "notes", "status"))
        == entries_before
    )
    assert {i.saved_asset_id for i in copy.items.all()} == {
        i.saved_asset_id for i in source_pack.items.all()
    }


def test_copying_an_empty_pack_copies_its_details(member, copier):
    pack = Pack.objects.create_pack(member, "Empty Kit", "Nothing yet.", "metal")
    pack.set_visibility("public")

    copy = copy_pack(pack, copier)

    assert copy.items.count() == 0 and copy.title == "Empty Kit (copy)"
    assert list(copy.tags.values_list("name", flat=True)) == ["metal"]
    assert not SavedAsset.objects.filter(user=copier).exists()


def test_deleting_the_original_keeps_the_copy(source_pack, copier):
    copy = copy_pack(source_pack, copier)
    source_pack.delete()
    copy.refresh_from_db()
    assert copy.copied_from is None and copy.items.count() == 3


# ---------------------------------------------------------------- Copy pack on the website


@pytest.fixture
def copier_client(copier):
    client = Client()
    client.force_login(copier)
    return client


def test_copy_pack_opens_the_copys_builder_which_says_where_it_came_from(
    source_pack, copier, copier_client, no_providers
):
    response = copier_client.post(reverse("packs:copy", args=[source_pack.slug]))

    copy = Pack.objects.get(owner=copier)
    assert response.status_code == 302 and response.url == reverse("packs:builder", args=[copy.pk])
    html = copier_client.get(response.url).content.decode()
    note = html.split('id="pack-copied-from"', 1)[1].split("</p>", 1)[0]
    assert f'href="{source_pack.get_public_url()}"' in note
    assert "Medieval Village" in note and "by demo_member" in note


def test_a_copy_of_an_unlisted_pack_names_it_without_a_link(source_pack, copier, copier_client):
    source_pack.set_visibility("unlisted")
    copier_client.post(reverse("packs:shared_copy", args=[source_pack.share_token]))

    copy = Pack.objects.get(owner=copier)
    html = copier_client.get(reverse("packs:builder", args=[copy.pk])).content.decode()
    note = html.split('id="pack-copied-from"', 1)[1].split("</p>", 1)[0]
    assert "Medieval Village" in note and "<a " not in note
    assert source_pack.share_token not in html


def test_a_pack_that_was_not_copied_has_no_note(member_client, source_pack):
    html = member_client.get(reverse("packs:builder", args=[source_pack.pk])).content.decode()
    assert 'id="pack-copied-from"' not in html


def test_copy_and_save_are_post_only(source_pack, copier_client):
    item = source_pack.ordered_items()[0]
    for url in (
        reverse("packs:copy", args=[source_pack.slug]),
        reverse("packs:save_item", args=[source_pack.slug, item.pk]),
    ):
        assert copier_client.get(url).status_code == 405
    assert not Pack.objects.exclude(pk=source_pack.pk).exists()


def test_the_api_has_no_copy_url(source_pack, copier):
    from rest_framework.authtoken.models import Token

    api = Client(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=copier).key}")
    assert api.post(f"/api/packs/{source_pack.pk}/copy/").status_code == 404
    assert api.post(reverse("packs:api_pack", args=[source_pack.pk])).status_code == 405
    assert api.post(reverse("packs:api_packs"), {"copy": source_pack.pk}).status_code == 405
    assert Pack.objects.count() == 1


# ---------------------------------------------------------------- Save to library, one item


def _save_url(pack, external_id):
    item = pack.items.get(saved_asset__asset__external_id=external_id)
    return reverse("packs:save_item", args=[pack.slug, item.pk])


def test_saving_an_item_makes_a_to_review_entry_and_shows_in_library(
    source_pack, copier, copier_client, no_providers
):
    response = copier_client.post(_save_url(source_pack, "brick"), headers={"HX-Request": "true"})

    entry = SavedAsset.objects.get(user=copier)
    assert entry.asset.external_id == "brick"
    assert (entry.status, entry.rating, entry.notes) == (SavedAsset.Status.TO_REVIEW, None, "")
    html = response.content.decode()
    assert "In your library" in html
    assert f'href="{reverse("catalog:entry", args=[entry.pk])}"' in html
    assert 'id="saved-count"' in html and "hx-swap-oob" in html


def test_saving_an_item_the_member_has_reuses_it_untouched(
    source_pack, copier, copier_client, no_providers
):
    roof = source_pack.items.get(saved_asset__asset__external_id="roof").asset
    mine = SavedAsset.objects.create(user=copier, asset=roof, notes="Mine.", rating=1)

    response = copier_client.post(_save_url(source_pack, "roof"), headers={"HX-Request": "true"})

    assert SavedAsset.objects.filter(user=copier).count() == 1
    mine.refresh_from_db()
    assert (mine.notes, mine.rating) == ("Mine.", 1)
    html = response.content.decode()
    assert "In your library" in html and "hx-swap-oob" not in html


def test_saving_without_htmx_goes_back_to_the_pack_page(source_pack, copier_client):
    response = copier_client.post(_save_url(source_pack, "well"))
    assert response.status_code == 302 and response.url == source_pack.get_public_url()


def test_an_item_of_another_pack_is_a_404(source_pack, member, copier, copier_client, make_asset):
    other = Pack.objects.create_pack(member, "Other Kit")
    other.set_visibility("public")
    asset = make_asset(external_id="lamp")
    item, _ = add_to_pack(other, SavedAsset.objects.create(user=member, asset=asset))

    url = reverse("packs:save_item", args=[source_pack.slug, item.pk])
    assert copier_client.post(url).status_code == 404
    assert not SavedAsset.objects.filter(user=copier).exists()


def test_saving_by_share_link_shows_in_library(source_pack, copier, copier_client):
    source_pack.set_visibility("unlisted")
    item = source_pack.ordered_items()[0]
    url = reverse("packs:shared_save_item", args=[source_pack.share_token, item.pk])

    response = copier_client.post(url, headers={"HX-Request": "true"})

    assert response.status_code == 200 and "In your library" in response.content.decode()
    assert SavedAsset.objects.filter(user=copier).count() == 1


# ---------------------------------------------------------------- the pack page's buttons


def _page(client, url):
    html = client.get(url).content.decode()
    return html.split('id="content"', 1)[1].split('id="page-footer"', 1)[0]


def test_a_member_sees_save_on_each_item_and_in_library_for_their_own(
    source_pack, copier, copier_client
):
    roof = source_pack.items.get(saved_asset__asset__external_id="roof").asset
    mine = SavedAsset.objects.create(user=copier, asset=roof)

    content = _page(copier_client, source_pack.get_public_url())

    assert content.count("Save to library") == 2
    assert content.count("In your library") == 1
    assert f'href="{reverse("catalog:entry", args=[mine.pk])}"' in content
    for external_id in ("brick", "well"):
        assert f'hx-post="{_save_url(source_pack, external_id)}"' in content
    # Copy pack opens its confirm, which counts what would join the library.
    assert 'data-dialog-open="pack-copy-dialog"' in content
    assert f'action="{reverse("packs:copy", args=[source_pack.slug])}"' in content
    missing = content.split('id="pack-copy-missing"', 1)[1].split("</p>", 1)[0]
    assert "2 assets you don't have yet go into your library as To review." in missing


def test_the_copy_confirm_says_so_when_nothing_is_missing(source_pack, member_client):
    content = _page(member_client, source_pack.get_public_url())
    missing = content.split('id="pack-copy-missing"', 1)[1].split("</p>", 1)[0]
    assert "Everything in it is already in your library" in missing
    # The owner has every item, so every item says so (and links to their own entry).
    assert content.count("In your library") == 3 and "Save to library" not in content


def test_in_library_reflects_only_the_readers_own_entries(source_pack, copier_client):
    """The owner has every item, but another reader sees Save on each."""
    content = _page(copier_client, source_pack.get_public_url())
    assert "In your library" not in content and content.count("Save to library") == 3


def test_a_visitor_gets_sign_in_links_back_to_the_page(source_pack):
    content = _page(Client(), source_pack.get_public_url())
    back = f"{reverse('accounts:login')}?next={quote(source_pack.get_public_url())}"

    assert content.count("<span>Sign in to save</span>") == 3
    assert f'href="{back}"' in content and "Sign in to copy" in content
    assert "pack-copy-dialog" not in content
    assert "<form" not in content and "hx-post" not in content


def test_the_share_links_page_saves_and_copies_by_the_link(source_pack, copier_client):
    source_pack.set_visibility("unlisted")
    token = source_pack.share_token

    content = _page(copier_client, source_pack.get_share_url())

    item = source_pack.ordered_items()[0]
    assert f'hx-post="{reverse("packs:shared_save_item", args=[token, item.pk])}"' in content
    assert f'action="{reverse("packs:shared_copy", args=[token])}"' in content
    assert reverse("packs:copy", args=[source_pack.slug]) not in content
    visitor = _page(Client(), source_pack.get_share_url())
    assert quote(source_pack.get_share_url()) in visitor


# ---------------------------------------------------------------- sign-in and CSRF


def test_a_visitors_htmx_save_redirects_the_window_to_sign_in(source_pack):
    response = Client().post(_save_url(source_pack, "brick"), headers={"HX-Request": "true"})
    assert response["HX-Redirect"] == (
        f"{reverse('accounts:login')}?next={quote(source_pack.get_public_url())}"
    )
    assert SavedAsset.objects.count() == 3


def test_save_and_copy_reject_a_post_without_a_csrf_token(source_pack, copier):
    client = Client(enforce_csrf_checks=True)
    client.force_login(copier)
    for url in (_save_url(source_pack, "brick"), reverse("packs:copy", args=[source_pack.slug])):
        assert client.post(url, headers={"HX-Request": "true"}).status_code == 403
        assert client.post(url).status_code == 403
    assert not SavedAsset.objects.filter(user=copier).exists()
    assert Pack.objects.count() == 1


def test_save_and_copy_succeed_with_the_pages_csrf_token(source_pack, copier):
    client = Client(enforce_csrf_checks=True)
    client.force_login(copier)
    page = client.get(source_pack.get_public_url()).content.decode()
    header = re.search(r"hx-headers='\{\"X-CSRFToken\": \"([^\"]+)\"\}'", page).group(1)
    field = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', page).group(1)

    saved = client.post(
        _save_url(source_pack, "brick"), headers={"HX-Request": "true", "X-CSRFToken": header}
    )
    copied = client.post(
        reverse("packs:copy", args=[source_pack.slug]), {"csrfmiddlewaretoken": field}
    )

    assert saved.status_code == 200 and copied.status_code == 302
    assert Pack.objects.filter(owner=copier).count() == 1
