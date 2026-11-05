"""Packs called directly: add_to_pack(), the default variant, Discover's
save-then-add, creating packs and their tags, and what deleting cascades to."""

import pytest

from catalog.models import Asset, SavedAsset
from packs.models import Pack, PackItem, default_variant
from packs.services import NotYourEntryError, add_from_provider, add_to_pack
from providers import ProviderError, polyhaven
from tests.test_library_save import full_record

pytestmark = pytest.mark.django_db


@pytest.fixture
def other(django_user_model, password):
    return django_user_model.objects.create_user(username="other_member", password=password)


@pytest.fixture
def pack(member):
    return Pack.objects.create_pack(member, "Medieval Village")


def test_add_to_pack_appends_once_and_refuses_another_members_entry(
    pack, member, other, make_asset
):
    brick = SavedAsset.objects.create(user=member, asset=make_asset(external_id="brick"))
    moss = SavedAsset.objects.create(user=member, asset=make_asset(external_id="moss"))

    first, first_created = add_to_pack(pack, brick)
    second, second_created = add_to_pack(pack, moss)
    again, again_created = add_to_pack(pack, brick)

    assert (first_created, second_created, again_created) == (True, True, False)
    assert again.pk == first.pk
    # One item per entry, each new one at the end.
    assert list(pack.ordered_items().values_list("saved_asset", flat=True)) == [brick.pk, moss.pk]

    # Another member's entry, even for an asset the owner has too, is refused.
    theirs = SavedAsset.objects.create(user=other, asset=brick.asset)
    with pytest.raises(NotYourEntryError):
        add_to_pack(pack, theirs)
    assert PackItem.objects.filter(pack=pack).count() == 2


def _variants(*labels):
    return [{"label": label, "files": [], "total_size": None} for label in labels]


@pytest.mark.parametrize(
    ("kind", "labels", "expected"),
    [
        # A 2K JPG wins, wherever it's listed; ambientCG writes it "2K-JPG".
        ("texture", ("1K JPG", "2K PNG", "2K JPG", "4K JPG"), "2K JPG"),
        ("hdri", ("1K-JPG", "2K-JPG", "4K-JPG"), "2K-JPG"),
        # A sound takes its MP3, never a 2K JPG.
        ("sound", ("WAV", "MP3", "FLAC"), "MP3"),
        ("sound", ("2K JPG", "OGG"), "2K JPG"),
        # No preferred variant: the first one listed.
        ("model", ("1K glTF", "2K Blend"), "1K glTF"),
        ("texture", ("MP3", "4K EXR"), "MP3"),
        # No variants at all.
        ("texture", (), ""),
    ],
)
def test_default_variant_is_a_2k_jpg_or_an_mp3_for_sounds_else_the_first(kind, labels, expected):
    assert default_variant(kind, _variants(*labels)) == expected


def test_adding_a_discover_result_saves_it_first_reuses_an_entry_and_writes_nothing_on_failure(
    pack, member, make_asset, monkeypatch
):
    # A result the member hasn't saved: fetched, saved as To review, then added.
    monkeypatch.setattr(
        polyhaven, "fetch_record", lambda external_id: full_record(external_id=external_id)
    )
    item, created = add_from_provider(pack, "polyhaven", "red_brick_03")
    new_entry = SavedAsset.objects.filter(user=member, asset__external_id="red_brick_03").first()
    assert new_entry is not None and created and item.saved_asset == new_entry
    assert (new_entry.status, new_entry.rating, new_entry.notes) == ("to_review", None, "")
    assert item.preferred_variant == "2K JPG"

    # A result already in the library: that entry is added untouched, with no fetch.
    reviewed = SavedAsset.objects.create(
        user=member,
        asset=make_asset(external_id="moss"),
        status="approved",
        rating=4,
        notes="Used on the well.",
    )
    monkeypatch.setattr(polyhaven, "fetch_record", _must_not_fetch)
    item, created = add_from_provider(pack, "polyhaven", "moss")
    reviewed_after = SavedAsset.objects.get(pk=reviewed.pk)
    assert created and item.saved_asset == reviewed
    assert (reviewed_after.status, reviewed_after.rating, reviewed_after.notes) == (
        "approved",
        4,
        "Used on the well.",
    )

    # A provider failure: its message comes through, and nothing is saved or added.
    def failing(external_id):
        raise ProviderError("Poly Haven didn't answer in time. Try again in a moment.")

    monkeypatch.setattr(polyhaven, "fetch_record", failing)
    entries, items = SavedAsset.objects.count(), PackItem.objects.count()
    with pytest.raises(ProviderError, match="didn't answer in time"):
        add_from_provider(pack, "polyhaven", "rusty_metal")
    assert (SavedAsset.objects.count(), PackItem.objects.count()) == (entries, items)
    assert not Asset.objects.filter(external_id="rusty_metal").exists()


def _must_not_fetch(external_id):
    raise AssertionError("fetch_record() was called for an asset already stored")


# ---------------------------------------------------------------- packs and their tags


def test_typed_tags_are_tidied_and_deduplicated(member):
    pack = Pack.objects.create_pack(member, "Quarry", tags="Rocks, rock, 2048,  Mossy  Stones")
    assert sorted(pack.tags.values_list("name", flat=True)) == ["mossy stone", "rock"]
    assert pack.tags_text == "mossy stone, rock"


def test_a_new_pack_is_private_with_a_site_wide_unique_slug(member, other):
    first = Pack.objects.create_pack(member, "Medieval Village")
    second = Pack.objects.create_pack(other, "Medieval  village!")
    third = Pack.objects.create_pack(member, "Medieval Village")
    assert not first.is_public and first.copied_from is None
    assert [first.slug, second.slug, third.slug] == [
        "medieval-village",
        "medieval-village-2",
        "medieval-village-3",
    ]
    # A title with nothing to slugify still gets a slug.
    assert Pack.objects.create_pack(member, "★★★").slug == "pack"


def test_a_rename_keeps_the_slug(pack):
    from packs.forms import PackDetailsForm

    form = PackDetailsForm({"title": "Old Town"}, pack=pack)
    assert form.is_valid()
    form.save()
    pack.refresh_from_db()
    assert (pack.title, pack.slug) == ("Old Town", "medieval-village")


# ---------------------------------------------------------------- items


def _entry(member, make_asset, external_id, **fields):
    return SavedAsset.objects.create(
        user=member, asset=make_asset(external_id=external_id, **fields)
    )


def test_a_new_item_starts_on_the_default_variant_with_a_blank_path(pack, member, make_asset):
    entry = _entry(member, make_asset, "brick", variants=_variants("1K JPG", "2K JPG"))
    item, _ = add_to_pack(pack, entry)
    assert (item.preferred_variant, item.import_path) == ("2K JPG", "")
    assert item.default_import_path == "textures/brick/"


def test_one_entry_can_differ_in_two_packs(pack, member, make_asset):
    entry = _entry(member, make_asset, "brick", variants=_variants("2K JPG", "4K JPG"))
    other_pack = Pack.objects.create_pack(member, "Castle")
    first, _ = add_to_pack(pack, entry)
    second, _ = add_to_pack(other_pack, entry)
    PackItem.objects.filter(pk=second.pk).update(
        preferred_variant="4K JPG", import_path="castle/walls/"
    )
    first.refresh_from_db()
    second.refresh_from_db()
    assert (first.preferred_variant, first.import_path) == ("2K JPG", "")
    assert (second.preferred_variant, second.import_path) == ("4K JPG", "castle/walls/")


def test_moving_an_item_swaps_it_with_its_neighbour(pack, member, make_asset):
    from packs.services import move_item

    items = [add_to_pack(pack, _entry(member, make_asset, name))[0] for name in "abc"]

    def order():
        return [item.saved_asset.asset.external_id for item in pack.ordered_items()]

    assert move_item(items[2], -1)
    assert order() == ["a", "c", "b"]
    assert move_item(items[0], 1)
    assert order() == ["c", "a", "b"]
    # Nothing past either end.
    assert not move_item(PackItem.objects.get(pk=items[2].pk), -1)
    assert not move_item(PackItem.objects.get(pk=items[1].pk), 1)
    assert order() == ["c", "a", "b"]


def test_moving_closes_the_gaps_a_remove_leaves(pack, member, make_asset):
    from packs.services import move_item

    items = [add_to_pack(pack, _entry(member, make_asset, name))[0] for name in "abcd"]
    items[1].delete()
    move_item(items[3], -1)
    assert list(pack.ordered_items().values_list("position", flat=True)) == [0, 1, 2]


def test_removing_an_item_keeps_the_entry_and_the_asset(pack, member, make_asset):
    entry = _entry(member, make_asset, "brick")
    item, _ = add_to_pack(pack, entry)
    item.delete()
    assert SavedAsset.objects.filter(pk=entry.pk).exists()
    assert Asset.objects.filter(pk=entry.asset_id).exists()


def test_deleting_an_entry_takes_it_out_of_every_pack_and_nothing_else(pack, member, make_asset):
    gone = _entry(member, make_asset, "brick")
    kept = _entry(member, make_asset, "moss")
    other_pack = Pack.objects.create_pack(member, "Castle")
    for each in (pack, other_pack):
        add_to_pack(each, gone)
        add_to_pack(each, kept)
    gone.delete()
    assert not PackItem.objects.filter(saved_asset_id=gone.pk).exists()
    assert PackItem.objects.filter(saved_asset=kept).count() == 2
    assert Asset.objects.filter(external_id="brick").exists()
    assert Pack.objects.count() == 2


def test_deleting_a_pack_removes_its_items_but_none_of_the_entries(pack, member, make_asset):
    entries = [_entry(member, make_asset, name) for name in "ab"]
    for entry in entries:
        add_to_pack(pack, entry)
    pack.delete()
    assert PackItem.objects.count() == 0
    assert SavedAsset.objects.count() == 2 and Asset.objects.count() == 2


def test_a_pack_item_can_only_point_at_its_owners_entry_through_add_to_pack(
    pack, other, make_asset
):
    theirs = SavedAsset.objects.create(user=other, asset=make_asset(external_id="brick"))
    with pytest.raises(NotYourEntryError):
        add_to_pack(pack, theirs)
    assert not PackItem.objects.exists()


def test_a_discover_add_for_an_unknown_provider_saves_nothing(pack):
    from catalog.library import UnknownProviderError

    with pytest.raises(UnknownProviderError):
        add_from_provider(pack, "sketchfab", "anything")
    assert not SavedAsset.objects.exists() and not PackItem.objects.exists()
