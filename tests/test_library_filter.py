"""filter_library(): the one search, filter, sort and paging function behind
the library page (and, from Phase 6, the library API).

Every test here calls the function directly. The page's use of it is in
test_library_page.py.
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from catalog.library import filter_library
from catalog.models import SavedAsset

pytestmark = pytest.mark.django_db


@pytest.fixture
def other(django_user_model, password):
    return django_user_model.objects.create_user(username="other_member", password=password)


@pytest.fixture
def save(member, make_asset):
    """Save an asset for `user` (the member by default), `days_ago` days back."""
    counter = iter(range(1000))

    def make(user=None, days_ago=0, notes="", rating=None, status="to_review", **asset_fields):
        asset_fields.setdefault("external_id", f"asset_{next(counter)}")
        return SavedAsset.objects.create(
            user=user or member,
            asset=make_asset(**asset_fields),
            notes=notes,
            rating=rating,
            status=status,
            saved_at=timezone.now() - timedelta(days=days_ago),
        )

    return make


def _titles(result):
    return [entry.asset.title for entry in result.page.object_list]


# ---------------------------------------------------------------- privacy (TDD 1)


def test_never_returns_another_members_entries_whatever_the_parameters(
    member, other, save, make_asset
):
    save(title="Mine Brick", notes="my brick", rating=5, status="approved")
    # The other member's entries match every parameter below, and one shares
    # the member's own asset, so only the owner check can keep them out.
    theirs = save(user=other, title="Their Brick", notes="brick", rating=5, status="approved")
    SavedAsset.objects.create(user=other, asset=SavedAsset.objects.get(user=member).asset)

    every_kind_of_params = [
        {},
        {"q": "brick"},
        {"type": "texture", "provider": "polyhaven", "status": "approved", "min_rating": "5"},
        {"sort": "rating"},
        {"sort": "title", "page": "1"},
        {"user": str(other.pk), "user_id": str(other.pk), "owner": other.username},
        {"q": "brick", "page": "2"},  # past the last page: clamped, still the member's own
    ]
    assert theirs.asset.title == "Their Brick"
    for params in every_kind_of_params:
        entries = list(filter_library(member, params).page.object_list)
        assert entries and all(entry.user_id == member.pk for entry in entries), params

    # A signed-out visitor has no library at all.
    from django.contrib.auth.models import AnonymousUser

    assert list(filter_library(AnonymousUser(), {}).page.object_list) == []


# ---------------------------------------------------------------- rating sort (TDD 2)


def test_rating_sort_is_high_to_low_with_unrated_entries_last(member, save):
    save(title="Unrated old", days_ago=5)
    save(title="Three old", rating=3, days_ago=4)
    save(title="Five", rating=5, days_ago=3)
    save(title="Unrated new", days_ago=0)
    save(title="Three new", rating=3, days_ago=1)
    save(title="One", rating=1, days_ago=2)

    # Equal ratings (and the unrated) fall back to newest saved first.
    assert _titles(filter_library(member, {"sort": "rating"})) == [
        "Five",
        "Three new",
        "Three old",
        "One",
        "Unrated new",
        "Unrated old",
    ]


# ---------------------------------------------------------------- fallbacks (TDD 3)


def test_unknown_sort_filter_and_page_values_fall_back_to_the_defaults(member, save):
    from catalog.library import LibraryParams

    # 14 entries: two pages, newest saved first by default.
    for day in range(14):
        save(title=f"Entry {day:02}", rating=(day % 5) + 1, status="approved", days_ago=day)
    default = filter_library(member, {})
    assert len(default.page.object_list) == 12

    unknown = [
        {"type": "planet"},
        {"provider": "nasa"},
        {"status": "lost"},
        {"min_rating": "9"},
        {"min_rating": "0"},
        {"min_rating": "abc"},
        {"sort": "sideways"},
        {"sort": ""},
        {"page": "abc"},
        {"page": "0"},
        {"page": "-3"},
        {"page": "²"},
        {"page": "9" * 5000},  # too long for int(): still not an error
        {"q": "   "},
    ]
    for params in unknown:
        result = filter_library(member, params)
        assert _titles(result) == _titles(default), params
        # The tidied parameters are the defaults too, so the URL drops them.
        assert result.params == LibraryParams(), params

    # An unknown value among known ones is dropped; the known ones still apply.
    mixed = filter_library(member, {"type": ["planet", "texture"], "status": ["lost", "approved"]})
    assert mixed.params.types == ("texture",) and mixed.params.statuses == ("approved",)
    assert _titles(mixed) == _titles(default)

    # A page past the end shows the last page.
    past = filter_library(member, {"page": "99"})
    assert past.params.page == 2
    assert _titles(past) == ["Entry 12", "Entry 13"]


# ---------------------------------------------------------------- search


def test_search_matches_the_title_ignoring_case(member, save):
    save(title="Red Brick Wall")
    save(title="Mossy Rock")
    assert _titles(filter_library(member, {"q": "BRICK"})) == ["Red Brick Wall"]


def test_search_matches_tags_including_their_plural(member, save):
    from catalog.models import Tag

    tagged = save(title="Cobbles")
    tagged.asset.tags.set(Tag.objects.from_names(["Stone", "Path"]))
    save(title="Sky")
    assert _titles(filter_library(member, {"q": "stone"})) == ["Cobbles"]
    # Words are tidied like tags first, so the plural finds the tag "stone".
    assert _titles(filter_library(member, {"q": "Stones"})) == ["Cobbles"]


def test_search_matches_the_members_own_notes(member, other, save):
    save(title="Planks", notes="Worked well for the tavern floor")
    save(title="Grass")
    # Another member's notes on an asset the member also has never count for the member.
    SavedAsset.objects.create(user=other, asset=save(title="Ice").asset, notes="tavern")
    assert _titles(filter_library(member, {"q": "tavern"})) == ["Planks"]


def test_every_search_word_must_match_but_each_in_any_field(member, save):
    from catalog.models import Tag

    one = save(title="Brick Wall", notes="")
    one.asset.tags.set(Tag.objects.from_names(["red"]))
    save(title="Brick Floor", notes="dusty")
    save(title="Red Sky")
    assert _titles(filter_library(member, {"q": "brick red"})) == ["Brick Wall"]
    assert _titles(filter_library(member, {"q": "  dusty   brick "})) == ["Brick Floor"]


def test_an_entry_matching_several_tags_is_listed_once(member, save):
    from catalog.models import Tag

    entry = save(title="Bricks")
    entry.asset.tags.set(Tag.objects.from_names(["brick", "brick wall", "red brick"]))
    result = filter_library(member, {"q": "brick"})
    assert _titles(result) == ["Bricks"]
    assert result.page.paginator.count == 1


# ---------------------------------------------------------------- filters


@pytest.fixture
def mixed(save):
    """Four entries across kinds, providers, statuses and ratings, newest first in this list."""
    save(title="Sound", kind="sound", provider="openverse", status="approved", rating=5, days_ago=0)
    save(title="HDRI", kind="hdri", provider="ambientcg", status="testing", rating=3, days_ago=1)
    save(
        title="Model",
        kind="model",
        provider="polyhaven",
        status="rejected",
        rating=None,
        days_ago=2,
    )
    save(
        title="Texture",
        kind="texture",
        provider="polyhaven",
        status="to_review",
        rating=1,
        days_ago=3,
    )


@pytest.mark.parametrize(
    ("params", "expected"),
    [
        ({"type": "hdri"}, ["HDRI"]),
        ({"type": ["texture", "sound"]}, ["Sound", "Texture"]),
        ({"provider": "polyhaven"}, ["Model", "Texture"]),
        ({"provider": ["openverse", "ambientcg"]}, ["Sound", "HDRI"]),
        ({"status": "rejected"}, ["Model"]),
        ({"status": ["approved", "to_review"]}, ["Sound", "Texture"]),
        # Minimum rating keeps that rating and above; unrated entries never pass it.
        ({"min_rating": "1"}, ["Sound", "HDRI", "Texture"]),
        ({"min_rating": "3"}, ["Sound", "HDRI"]),
        ({"min_rating": "5"}, ["Sound"]),
        ({"min_rating": ""}, ["Sound", "HDRI", "Model", "Texture"]),
    ],
)
def test_each_filter(member, mixed, params, expected):
    assert _titles(filter_library(member, params)) == expected


def test_filters_combine_with_each_other(member, mixed):
    params = {"provider": "polyhaven", "type": ["texture", "model"], "min_rating": "1"}
    assert _titles(filter_library(member, params)) == ["Texture"]


def test_a_query_dict_carries_several_values_for_one_filter(member, mixed):
    from django.http import QueryDict

    params = QueryDict("type=texture&type=hdri&sort=oldest")
    assert _titles(filter_library(member, params)) == ["Texture", "HDRI"]


# ---------------------------------------------------------------- sorts


@pytest.fixture
def sortable(save):
    save(title="banana", rating=2, days_ago=2)
    save(title="Apple", rating=None, days_ago=0)
    save(title="cherry", rating=4, days_ago=1)


@pytest.mark.parametrize(
    ("sort", "expected"),
    [
        (None, ["Apple", "cherry", "banana"]),  # newest saved is the default
        ("newest", ["Apple", "cherry", "banana"]),
        ("oldest", ["banana", "cherry", "Apple"]),
        ("title", ["Apple", "banana", "cherry"]),  # A–Z, ignoring case
        ("rating", ["cherry", "banana", "Apple"]),
    ],
)
def test_each_sort(member, sortable, sort, expected):
    params = {"sort": sort} if sort else {}
    assert _titles(filter_library(member, params)) == expected


# ---------------------------------------------------------------- pages


def test_pages_hold_twelve_entries(member, save):
    for day in range(25):
        save(title=f"Entry {day:02}", days_ago=day)
    first = filter_library(member, {})
    assert first.page.paginator.count == 25
    assert first.page.paginator.num_pages == 3
    assert _titles(first) == [f"Entry {day:02}" for day in range(12)]
    assert _titles(filter_library(member, {"page": "2"})) == [
        f"Entry {day:02}" for day in range(12, 24)
    ]
    assert _titles(filter_library(member, {"page": "3"})) == ["Entry 24"]


def test_an_empty_library_is_one_empty_page(member):
    result = filter_library(member, {"page": "4"})
    assert list(result.page.object_list) == []
    assert result.page.number == 1 and result.params.page == 1


def test_search_filters_sort_and_page_combine(member, save):
    from catalog.models import Tag

    for n in range(15):
        entry = save(
            title=f"Stone {n:02}",
            kind="texture" if n % 3 else "hdri",
            status="approved",
            rating=(n % 5) + 1,
            days_ago=n,
        )
        entry.asset.tags.set(Tag.objects.from_names(["stone"]))
    save(title="Wood", status="approved", rating=5)
    params = {"q": "stone", "type": "texture", "min_rating": "2", "sort": "title", "page": "1"}
    result = filter_library(member, params)
    # Textures are the n not divisible by 3; rating >= 2 drops n % 5 == 0.
    expected = [f"Stone {n:02}" for n in range(15) if n % 3 and n % 5]
    assert result.page.paginator.count == len(expected) == 8
    assert _titles(result) == expected


# ---------------------------------------------------------------- URLs


def test_the_url_holds_search_filters_sort_and_page_and_leaves_out_defaults(member, save):
    from catalog.library import LibraryParams

    assert LibraryParams().url() == "/library/"
    assert not LibraryParams().is_filtered
    for day in range(13):
        save(title=f"Red Brick {day}", status="approved", rating=4, days_ago=day)
    result = filter_library(
        member,
        {
            "q": " red  brick ",
            "type": ["hdri", "texture"],
            "provider": "polyhaven",
            "status": "approved",
            "min_rating": "4",
            "sort": "rating",
            "page": "2",
        },
    )
    assert result.params.is_filtered
    assert result.url == (
        "/library/?q=red+brick&type=texture&type=hdri&provider=polyhaven&status=approved"
        "&min_rating=4&sort=rating&page=2"
    )
    assert result.previous_url == result.url.replace("&page=2", "")
    assert result.next_url == ""


# ---------------------------------------------------------------- tags (Phase 4 polish)


def _tag(entry, *names):
    from catalog.models import Tag

    entry.asset.tags.set(Tag.objects.from_names(names))
    return entry


def test_a_tag_filter_finds_entries_from_every_provider(member, save):
    _tag(save(title="ACG Bricks", provider="ambientcg"), "brick", "red")
    _tag(save(title="PH Bricks", provider="polyhaven"), "Bricks")
    _tag(save(title="OV Brick Hit", provider="openverse", kind="sound"), "brick")
    _tag(save(title="Wood"), "wood")
    result = filter_library(member, {"tag": "brick"})
    assert sorted(_titles(result)) == ["ACG Bricks", "OV Brick Hit", "PH Bricks"]


def test_several_tags_need_every_one(member, save):
    _tag(save(title="Red Brick"), "brick", "red")
    _tag(save(title="Grey Brick"), "brick", "grey")
    assert _titles(filter_library(member, {"tag": ["brick", "red"]})) == ["Red Brick"]
    assert _titles(filter_library(member, {"tag": ["red", "grey"]})) == []


def test_an_entry_is_listed_once_whatever_tags_and_search_match_it(member, save):
    _tag(save(title="Brick Wall"), "brick", "brick wall", "red brick")
    result = filter_library(member, {"tag": ["brick", "red brick"], "q": "brick"})
    assert _titles(result) == ["Brick Wall"]


def test_tag_values_are_tidied_like_tags_and_junk_is_dropped(member, save):
    from catalog.library import MAX_TAG_FILTERS

    _tag(save(title="Mossy"), "mossy stone")
    result = filter_library(member, {"tag": ["  Mossy   Stones ", "2048", "", "mossy stone"]})
    assert result.params.tags == ("mossy stone",)
    assert _titles(result) == ["Mossy"]
    # Only the first MAX_TAG_FILTERS values are read; the rest are ignored.
    many = [f"tag {n}" for n in range(MAX_TAG_FILTERS)] + ["mossy stone"]
    assert "mossy stone" not in filter_library(member, {"tag": many}).params.tags
    # A tag nobody has finds nothing, rather than failing.
    assert _titles(filter_library(member, {"tag": "planet"})) == []


def test_a_tag_filter_never_reaches_another_members_entries(member, other, save):
    mine = _tag(save(title="Mine"), "rock")
    # The other member shares the same asset and has their own tagged one.
    SavedAsset.objects.create(user=other, asset=mine.asset)
    _tag(save(user=other, title="Theirs"), "rock", "secret")
    assert _titles(filter_library(member, {"tag": "rock"})) == ["Mine"]
    assert _titles(filter_library(member, {"tag": "secret"})) == []


def test_the_url_holds_the_chosen_tags_a_to_z(member, save):
    result = filter_library(member, {"tag": ["wood", "brick"], "type": "texture"})
    assert result.params.is_filtered
    assert result.url == "/library/?type=texture&tag=brick&tag=wood"


def test_in_library_lists_only_the_members_tags_most_used_first(member, other, save):
    from django.contrib.auth.models import AnonymousUser

    from catalog.models import Tag

    _tag(save(title="A", provider="ambientcg"), "brick", "red")
    _tag(save(title="B", provider="openverse", kind="sound"), "brick", "loud")
    _tag(save(user=other, title="C"), "brick", "secret")
    tags = Tag.objects.in_library(member)
    # Counts only the member's own entries; ties go A–Z.
    assert [(tag.name, tag.uses) for tag in tags] == [("brick", 2), ("loud", 1), ("red", 1)]
    assert not Tag.objects.in_library(AnonymousUser()).exists()


def test_the_tag_chips_show_the_most_used_and_keep_a_chosen_one_beyond_them():
    from types import SimpleNamespace

    from catalog.library import TAG_CHIP_LIMIT, clean_library_params, filter_groups

    tags = [SimpleNamespace(name=f"tag {n:02}", uses=50 - n) for n in range(TAG_CHIP_LIMIT + 5)]
    chosen = f"tag {TAG_CHIP_LIMIT + 3:02}"
    groups = filter_groups(clean_library_params({"tag": chosen}), tags)
    [group] = [group for group in groups if group.name == "tag"]
    assert group.title == "Tags" and group.multiple
    names = [chip.value for chip in group.chips]
    assert names == [f"tag {n:02}" for n in range(TAG_CHIP_LIMIT)] + [chosen]
    assert [chip.value for chip in group.chips if chip.checked] == [chosen]
    assert group.chips[0].count == 50
