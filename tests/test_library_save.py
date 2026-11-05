"""Saving to the library: the shared Asset, the member's SavedAsset, and the Save button.

App tests, so provider functions are replaced with `monkeypatch` (see
docs/TESTING.md); no test here fakes HTTP.
"""

import re
from urllib.parse import quote

import pytest
from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils.html import escape

from catalog.library import UnknownProviderError, save_to_library
from catalog.models import Asset, SavedAsset, Tag
from providers import PROVIDERS, AssetRecord, ProviderError, polyhaven
from providers.records import Variant, VariantFile

pytestmark = pytest.mark.django_db

VARIANTS = (
    Variant("2K JPG", (VariantFile("https://dl.polyhaven.org/d_2k.jpg", "d_2k.jpg", 400),)),
    Variant("4K JPG", (VariantFile("https://dl.polyhaven.org/d_4k.jpg", "d_4k.jpg", None),)),
)


def full_record(provider="polyhaven", external_id="red_brick_03", kind="texture", **fields):
    """An AssetRecord as fetch_record() returns it: every field, variants included."""
    values = {
        "title": "Red Brick 03",
        "author": "Rob Tuytel",
        "thumbnail_url": f"https://cdn.polyhaven.com/thumbs/{external_id}.png",
        "license": "CC0",
        "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        "attribution": '"Red Brick 03" by Rob Tuytel, from Poly Haven, CC0 1.0',
        "source_url": f"https://polyhaven.com/a/{external_id}",
        "tags": ("Rocks", "rock", "2048", "Mossy  Stones"),
        "variants": VARIANTS,
    }
    values.update(fields)
    return AssetRecord(provider=provider, external_id=external_id, kind=kind, **values)


@pytest.fixture
def fetches(monkeypatch):
    """Replace Poly Haven's fetch_record; the list records each ID it was asked for."""
    calls = []

    def fake(external_id):
        calls.append(external_id)
        return full_record(external_id=external_id)

    monkeypatch.setattr(polyhaven, "fetch_record", fake)
    return calls


@pytest.fixture
def other_member(django_user_model, password):
    return django_user_model.objects.create_user(username="other_member", password=password)


# ---------------------------------------------------------------- the save service


def test_first_save_fetches_once_and_every_later_save_reuses_the_shared_asset(
    fetches, member, other_member
):
    # The first save by anyone fetches the asset and stores it, tags normalized.
    saved, created = save_to_library(member, "polyhaven", "red_brick_03")
    assert fetches == ["red_brick_03"]
    assert created
    asset = Asset.objects.get()
    assert (asset.provider, asset.external_id, asset.kind) == (
        "polyhaven",
        "red_brick_03",
        "texture",
    )
    assert sorted(asset.tags.values_list("name", flat=True)) == ["mossy stone", "rock"]
    assert asset.variants == [variant.as_dict() for variant in VARIANTS]
    assert (saved.user, saved.asset) == (member, asset)

    # Another member's save reuses that Asset and doesn't fetch again.
    theirs, created = save_to_library(other_member, "polyhaven", "red_brick_03")
    assert fetches == ["red_brick_03"]
    assert created
    assert theirs.asset == asset
    assert Asset.objects.count() == 1

    # Saving it again creates no second entry: the existing one comes back.
    again, created = save_to_library(member, "polyhaven", "red_brick_03")
    assert not created
    assert again == saved
    assert fetches == ["red_brick_03"]
    assert SavedAsset.objects.count() == 2


def test_a_provider_failure_saves_nothing_and_keeps_its_message(monkeypatch, member):
    message = "Poly Haven did not respond within 10 seconds. Try again in a moment."

    def failing(external_id):
        raise ProviderError(message)

    monkeypatch.setattr(polyhaven, "fetch_record", failing)
    with pytest.raises(ProviderError) as caught:
        save_to_library(member, "polyhaven", "red_brick_03")
    assert str(caught.value) == message
    assert not Asset.objects.exists()
    assert not SavedAsset.objects.exists()
    assert not Tag.objects.exists()

    # The failure isn't remembered: once the provider answers, the save works.
    monkeypatch.setattr(polyhaven, "fetch_record", lambda external_id: full_record())
    saved, created = save_to_library(member, "polyhaven", "red_brick_03")
    assert created
    assert saved.asset.title == "Red Brick 03"


def test_a_new_entry_starts_as_to_review_with_no_rating(fetches, member):
    saved, _ = save_to_library(member, "polyhaven", "red_brick_03")
    saved.refresh_from_db()
    assert saved.status == SavedAsset.Status.TO_REVIEW
    assert saved.get_status_display() == "To review"
    assert saved.rating is None
    assert saved.notes == ""


def test_an_unknown_provider_is_refused_without_fetching(fetches, member):
    with pytest.raises(UnknownProviderError):
        save_to_library(member, "freesound", "123")
    assert fetches == []
    assert not Asset.objects.exists()


def _must_not_fetch(external_id):
    raise AssertionError("fetch_record() was called for an asset already stored")


def test_a_stored_asset_is_reused_untouched_and_the_provider_isnt_asked(
    make_asset, member, monkeypatch
):
    make_asset(title="Stored Title")
    monkeypatch.setattr(polyhaven, "fetch_record", _must_not_fetch)
    saved, created = save_to_library(member, "polyhaven", " red_brick_03 ")
    assert created
    assert saved.asset.title == "Stored Title"


# ---------------------------------------------------------------- model rules


def test_deleting_an_entry_leaves_the_shared_asset(make_asset, member):
    asset = make_asset()
    entry = SavedAsset.objects.create(user=member, asset=asset)
    entry.delete()
    assert Asset.objects.filter(pk=asset.pk).exists()


def test_the_database_allows_one_entry_per_member_and_asset(make_asset, member):
    asset = make_asset()
    SavedAsset.objects.create(user=member, asset=asset)
    with pytest.raises(IntegrityError), transaction.atomic():
        SavedAsset.objects.create(user=member, asset=asset)


def test_the_database_allows_one_asset_per_provider_id(make_asset):
    make_asset()
    with pytest.raises(IntegrityError), transaction.atomic():
        make_asset()


@pytest.mark.parametrize("rating", [0, 6])
def test_the_database_refuses_a_rating_outside_one_to_five(make_asset, member, rating):
    with pytest.raises(IntegrityError), transaction.atomic():
        SavedAsset.objects.create(user=member, asset=make_asset(), rating=rating)


def test_tags_from_names_normalizes_and_drops_duplicates():
    tags = Tag.objects.from_names(["Rocks", "rock", "2048", "  Mossy  Stones", "", 7])
    assert [tag.name for tag in tags] == ["rock", "mossy stone"]
    assert Tag.objects.from_names(["ROCK"]) == [tags[0]]  # reused, not duplicated
    assert Tag.objects.count() == 2


# ---------------------------------------------------------------- the save view

HTMX = {"HX-Request": "true", "HX-Current-URL": "http://testserver/discover/?type=texture&q=brick"}
COUNT_ONE = '<b class="text-fg-strong">1</b> saved'


def save(client, provider="polyhaven", external_id="red_brick_03", headers=HTMX):
    return client.post(
        reverse("catalog:save"), {"provider": provider, "external_id": external_id}, headers=headers
    )


def test_saving_swaps_the_button_for_in_library_and_updates_the_count(
    fetches, member, member_client
):
    response = save(member_client)
    assert response.status_code == 200
    html = response.content.decode()
    assert re.search(r'<a href="/library/" class="save-slot in-library"><i class="mark[^"]*"', html)
    assert "In library" in html
    assert "Save to library" not in html
    # The status bar's count comes along out of band.
    assert '<span id="saved-count" class="ml-auto" hx-swap-oob="true">' in html
    assert COUNT_ONE in html
    assert SavedAsset.objects.filter(user=member).count() == 1


def test_saving_an_asset_already_in_the_library_shows_in_library_and_adds_nothing(
    fetches, member, member_client
):
    save(member_client)
    html = save(member_client).content.decode()
    assert "In library" in html
    assert COUNT_ONE in html
    assert SavedAsset.objects.filter(user=member).count() == 1
    assert fetches == ["red_brick_03"]


@pytest.mark.parametrize(
    "message",
    [
        "Poly Haven has nothing at that address (HTTP 404). "
        "If you entered an asset ID, check it and try again.",
        'Poly Haven said <b onclick="x()">busy</b> & "try later".',
    ],
    ids=["not-found", "markup"],
)
def test_a_provider_failure_replaces_the_button_with_its_message(
    monkeypatch, member_client, message
):
    def failing(external_id):
        raise ProviderError(message)

    monkeypatch.setattr(polyhaven, "fetch_record", failing)
    response = save(member_client)
    assert response.status_code == 200
    html = response.content.decode()
    # The message, unchanged and escaped, in the button's place, with Try again.
    assert '<p class="save-error-text" role="alert">' in html
    assert escape(message) in html
    assert "<b onclick" not in html
    assert '<form class="save-slot save-error" hx-post="/library/save/"' in html
    assert '<input type="hidden" name="external_id" value="red_brick_03">' in html
    assert "Try again" in html
    assert "In library" not in html and "saved-count" not in html
    assert not Asset.objects.exists() and not SavedAsset.objects.exists()


@pytest.mark.parametrize(
    ("provider", "external_id"),
    [
        ("freesound", "123"),
        ("", "123"),
        ("polyhaven", ""),
        ("polyhaven", "   "),
        ("polyhaven", "x" * 201),
    ],
    ids=["unknown-provider", "no-provider", "no-id", "blank-id", "long-id"],
)
def test_a_bad_save_is_a_400_before_any_provider_is_called(
    monkeypatch, member_client, provider, external_id
):
    for source in PROVIDERS:
        monkeypatch.setattr(source, "fetch_record", _must_not_fetch)
    response = save(member_client, provider, external_id)
    assert response.status_code == 400
    assert not SavedAsset.objects.exists()


def test_saving_is_post_only(member_client):
    assert member_client.get(reverse("catalog:save")).status_code == 405


# ---------------------------------------------------------------- "In library" on Discover


@pytest.fixture
def two_results(monkeypatch):
    results = [
        full_record(external_id="red_brick_03", variants=()),
        full_record(external_id="blue_tiles", variants=()),
    ]
    monkeypatch.setattr(polyhaven, "search_records", lambda query, kind, limit=12, page=1: results)


def shelf(client, page=None):
    url = reverse("catalog:discover_shelf", args=["texture", "polyhaven"]) + "?q=brick"
    if page:
        url += f"&page={page}"
    return client.get(url, headers={"HX-Request": "true"}).content.decode()


def save_slots(html):
    """{external_id: the card's Save slot HTML}, for each result card."""
    pattern = r'href="https://polyhaven\.com/a/(\w+)".*?<div class="result-actions">(.*?)</div>\n'
    return dict(re.findall(pattern, html, re.S))


def test_results_the_member_has_saved_render_as_in_library(
    two_results, make_asset, member, member_client
):
    SavedAsset.objects.create(user=member, asset=make_asset(external_id="red_brick_03"))
    slots = save_slots(shelf(member_client))
    assert set(slots) == {"red_brick_03", "blue_tiles"}
    assert "In library" in slots["red_brick_03"]
    assert "hx-post" not in slots["red_brick_03"]
    form = slots["blue_tiles"]
    assert "Save to library" in form
    assert (
        '<form class="save-slot" hx-post="/library/save/" hx-target="this" hx-swap="outerHTML"'
        in form
    )
    assert '<input type="hidden" name="provider" value="polyhaven">' in form
    assert '<input type="hidden" name="external_id" value="blue_tiles">' in form


def test_load_more_pages_also_show_in_library(two_results, make_asset, member, member_client):
    SavedAsset.objects.create(user=member, asset=make_asset(external_id="blue_tiles"))
    slots = save_slots(shelf(member_client, page=2))
    assert "In library" in slots["blue_tiles"]
    assert "Save to library" in slots["red_brick_03"]


def test_another_members_library_never_marks_a_result_in_library(
    two_results, make_asset, other_member, member_client
):
    SavedAsset.objects.create(user=other_member, asset=make_asset(external_id="red_brick_03"))
    slots = save_slots(shelf(member_client))
    assert slots and all("In library" not in slot for slot in slots.values())


def test_a_visitors_save_button_is_a_link_to_sign_in_and_back_to_discover(two_results, client):
    slots = save_slots(shelf(client))
    back = quote("/discover/?type=texture&q=brick")
    assert slots
    for slot in slots.values():
        assert f'<a class="save-slot save-button" href="/accounts/login/?next={back}"' in slot
        assert "hx-post" not in slot


def test_the_in_library_badge_never_sits_on_a_thumbnail(
    two_results, make_asset, member, member_client
):
    """The badge carries the logo mark, and the logo never goes on a provider's image."""
    SavedAsset.objects.create(user=member, asset=make_asset(external_id="red_brick_03"))
    html = shelf(member_client)
    thumbs = re.findall(r'<div class="result-thumb">(.*?)</div>', html, re.S)
    assert thumbs
    for thumb in thumbs:
        assert "mark" not in thumb and "In library" not in thumb
