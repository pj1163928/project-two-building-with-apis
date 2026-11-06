"""The public gallery (Phase 9): filter_public_packs() called directly, the
gallery cards' type summary and mosaic, and the gallery on the main page.

App tests, so provider functions are never reached.
"""

import pytest

from catalog.models import SavedAsset
from packs.gallery import filter_public_packs
from packs.models import Pack
from packs.services import add_to_pack

pytestmark = pytest.mark.django_db

KINDS = ("texture", "hdri", "model", "sound")


@pytest.fixture
def other(django_user_model, password):
    return django_user_model.objects.create_user(username="other_member", password=password)


@pytest.fixture
def fill(make_asset):
    """Add one new asset of each given kind to `pack`, through the owner's library."""
    counter = iter(range(10_000))

    def add(pack, *kinds):
        for kind in kinds:
            number = next(counter)
            asset = make_asset(
                external_id=f"asset_{number:04d}", kind=kind, title=f"Asset {number:04d}"
            )
            entry = SavedAsset.objects.create(user=pack.owner, asset=asset)
            add_to_pack(pack, entry)
        return pack

    return add


def _every_pack(params):
    """Every pack the gallery lists for `params`, across all of its pages."""
    first = filter_public_packs(params)
    found = list(first.page.object_list)
    for number in first.page.paginator.page_range[1:]:
        found += filter_public_packs({**params, "page": str(number)}).page.object_list
    return found


# Each query the gallery can run, the hidden packs matching every one of them.
QUERIES = [
    {},
    {"q": "castle"},  # matches the titles
    {"q": "fortress"},  # matches a tag only
    {"q": "Castle FORTRESS"},  # a title word and a tag word, case ignored
    {"type": "sound"},
    {"type": "hdri", "q": "castle"},
    {"sort": "items"},  # the hidden packs hold the most items
    {"sort": "newest"},  # and are the newest
    {"page": "2"},
    {"q": "castle", "sort": "items", "page": "2"},
]


@pytest.mark.parametrize("params", QUERIES)
def test_the_gallery_never_lists_a_private_or_unlisted_pack(member, other, fill, params):
    """Private and unlisted packs that match the search, the type, both sorts and
    every page are still never listed, by anyone's query."""
    public = [
        fill(
            Pack.objects.create_pack(other, f"Castle walls {n}", "", "castle, fortress"),
            "texture",
            "hdri",
            "sound",
        )
        for n in range(13)  # more than one page of 12
    ]
    for pack in public:
        pack.set_visibility(Pack.Visibility.PUBLIC)
    hidden = []
    for owner, title, visibility in (
        (member, "Castle keep", Pack.Visibility.PRIVATE),
        (other, "Castle gate", Pack.Visibility.UNLISTED),
        (member, "Castle tower", Pack.Visibility.UNLISTED),
    ):
        pack = fill(Pack.objects.create_pack(owner, title, "", "castle, fortress"), *KINDS, *KINDS)
        pack.set_visibility(visibility)
        hidden.append(pack)

    listed = _every_pack(params)

    assert listed, "the query matches the public packs, so it must list some"
    assert {pack.pk for pack in listed} <= {pack.pk for pack in public}
    assert not {pack.pk for pack in listed} & {pack.pk for pack in hidden}


# ------------------------------------------------- filter_public_packs(): search, type, sorts


def _public(owner, title, tags="", *, fill=None, kinds=()):
    pack = Pack.objects.create_pack(owner, title, "", tags)
    if fill and kinds:
        fill(pack, *kinds)
    pack.set_visibility(Pack.Visibility.PUBLIC)
    return pack


def _titles(params):
    return [pack.title for pack in filter_public_packs(params).page.object_list]


def test_search_matches_the_title_ignoring_case(other):
    _public(other, "Medieval Village")
    _public(other, "Sci-fi Corridor")
    assert _titles({"q": "VILLAGE"}) == ["Medieval Village"]


def test_search_matches_a_tag_tidied_like_a_tag(other):
    _public(other, "Market square", "stone, timber")
    _public(other, "Spaceship", "metal")
    assert _titles({"q": "Stones"}) == ["Market square"]


def test_every_search_word_must_match_the_title_or_a_tag(other):
    _public(other, "Medieval Village", "stone")
    _public(other, "Medieval Castle", "metal")
    assert _titles({"q": "medieval stone"}) == ["Medieval Village"]
    assert _titles({"q": "medieval glass"}) == []


def test_a_pack_with_several_matching_tags_is_listed_once(other):
    _public(other, "Forest", "forest floor, forest bird, forest night")
    assert _titles({"q": "forest"}) == ["Forest"]


def test_the_type_filter_keeps_packs_holding_that_type(other, fill):
    _public(other, "Night sounds", fill=fill, kinds=("sound", "sound"))
    _public(other, "Mixed kit", fill=fill, kinds=("texture", "sound"))
    _public(other, "Walls", fill=fill, kinds=("texture",))
    _public(other, "Empty")
    assert sorted(_titles({"type": "sound"})) == ["Mixed kit", "Night sounds"]
    assert _titles({"type": "model"}) == []


def test_newest_is_the_default_sort(other):
    for title in ("First", "Second", "Third"):
        _public(other, title)
    assert _titles({}) == ["Third", "Second", "First"]
    assert _titles({"sort": "newest"}) == ["Third", "Second", "First"]


def test_most_items_sorts_by_item_count_then_newest(other, fill):
    _public(other, "Two", fill=fill, kinds=("texture", "hdri"))
    _public(other, "Three", fill=fill, kinds=("texture", "hdri", "sound"))
    _public(other, "Also two", fill=fill, kinds=("model", "sound"))
    _public(other, "None")
    assert _titles({"sort": "items"}) == ["Three", "Also two", "Two", "None"]


def test_pages_hold_twelve_packs(other):
    for n in range(26):
        _public(other, f"Pack {n:02d}")
    first = filter_public_packs({})
    third = filter_public_packs({"page": "3"})
    assert len(first.page.object_list) == 12
    assert first.page.paginator.num_pages == 3
    assert [pack.title for pack in third.page.object_list] == ["Pack 01", "Pack 00"]
    assert first.next_url == "/?page=2" and first.previous_url == ""
    assert third.previous_url == "/?page=2" and third.next_url == ""


def test_filters_combine(other, fill):
    _public(other, "Forest sounds", "forest", fill=fill, kinds=("sound",))
    _public(other, "Forest floor", "forest", fill=fill, kinds=("texture",))
    _public(other, "City sounds", "city", fill=fill, kinds=("sound",))
    assert _titles({"q": "forest", "type": "sound"}) == ["Forest sounds"]


@pytest.mark.parametrize(
    "params",
    [
        {"type": "vehicle", "sort": "popular", "page": "abc"},
        {"type": "", "sort": "", "page": "0"},
        {"page": "-3"},
        {"page": "9" * 40},
    ],
)
def test_unknown_values_fall_back_to_the_defaults(other, params):
    for title in ("Old", "New"):
        _public(other, title)
    result = filter_public_packs(params)
    assert [pack.title for pack in result.page.object_list] == ["New", "Old"]
    assert (result.params.type, result.params.sort, result.params.page) == ("", "newest", 1)


def test_a_page_past_the_end_is_the_last_page(other):
    for n in range(13):
        _public(other, f"Pack {n:02d}")
    result = filter_public_packs({"page": "99"})
    assert result.page.number == 2 and result.params.page == 2


def test_the_tidy_url_leaves_out_defaults():
    from packs.gallery import clean_gallery_params

    assert clean_gallery_params({}).url() == "/"
    params = clean_gallery_params({"q": "  red   brick ", "type": "texture", "sort": "items"})
    assert params.url() == "/?q=red+brick&type=texture&sort=items"
    assert params.url(page=2) == "/?q=red+brick&type=texture&sort=items&page=2"


def test_a_query_dict_works_like_a_plain_dict(other, rf):
    _public(other, "Medieval Village")
    _public(other, "Spaceship")
    request = rf.get("/", {"q": "medieval"})
    assert [p.title for p in filter_public_packs(request.GET).page.object_list] == [
        "Medieval Village"
    ]


# ------------------------------------------------- a gallery card: the count by type (TDD)


@pytest.mark.parametrize(
    ("kinds", "expected"),
    [
        (
            ["sound", "texture", "hdri", "texture", "sound", "texture"],
            "3 textures · 1 HDRI · 2 sounds",
        ),
        (["texture", "hdri", "model", "sound"], "1 texture · 1 HDRI · 1 model · 1 sound"),
        (["hdri", "hdri", "model", "model"], "2 HDRIs · 2 models"),
        (["sound"], "1 sound"),
        ([], "No items yet"),
    ],
)
def test_type_summary_counts_each_type_in_discover_order(kinds, expected):
    """Singular for one, plural for more, Discover's order whatever the items' order,
    and types with no items left out; an empty pack says so."""
    from packs.gallery import type_summary

    assert type_summary(kinds) == expected
