"""Around one library entry: similar entries, the public packs featuring it and
Find more (user request, 2026-11-05), plus the full page's centred layout and the
library's folding Tags list."""

from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import pytest
from django.test import Client
from django.urls import reverse

pytestmark = pytest.mark.django_db


def _save(user, make_asset, external_id, kind="texture", tags=(), **fields):
    from catalog.models import SavedAsset, Tag

    fields.setdefault("title", external_id.title())
    asset = make_asset(external_id=external_id, kind=kind, **fields)
    asset.tags.set(Tag.objects.from_names(tags))
    return SavedAsset.objects.create(user=user, asset=asset)


def test_similar_entries_rank_by_shared_tags_then_kind(member, make_asset):
    from catalog.models import SavedAsset

    entry = _save(member, make_asset, "brick", tags=["brick", "wall", "red"])
    two = _save(member, make_asset, "wall_two", kind="model", tags=["brick", "wall"])
    one = _save(member, make_asset, "wall_one", tags=["wall"])
    kind_only = _save(member, make_asset, "plaster", tags=["plaster"])
    _save(member, make_asset, "rain", kind="sound", tags=["rain"])  # shares nothing
    similar = SavedAsset.objects.for_user(member).similar_to(entry)
    assert similar == [two, one, kind_only]
    assert [other.shared_tags for other in similar] == [2, 1, 0]


def test_similar_entries_never_come_from_another_library(member, make_asset, django_user_model):
    from catalog.models import SavedAsset

    entry = _save(member, make_asset, "brick", tags=["brick"])
    other = django_user_model.objects.create_user("other_member")
    SavedAsset.objects.create(user=other, asset=make_asset(external_id="their_brick"))
    assert SavedAsset.objects.for_user(member).similar_to(entry) == []


def test_featured_in_lists_other_members_public_packs_only(member, make_asset, django_user_model):
    from catalog.library import entry_related
    from catalog.models import SavedAsset
    from packs.models import Pack
    from packs.services import add_to_pack

    entry = _save(member, make_asset, "brick", tags=["brick", "wall"])
    other = django_user_model.objects.create_user("other_member")
    theirs = SavedAsset.objects.create(user=other, asset=entry.asset)
    public = Pack.objects.create_pack(other, "Dungeon Kit")
    public.is_public = True
    public.save()
    private = Pack.objects.create_pack(other, "Secret Kit")
    mine = Pack.objects.create_pack(member, "My Public Kit")
    mine.is_public = True
    mine.save()
    for pack, saved in ((public, theirs), (private, theirs), (mine, entry)):
        add_to_pack(pack, saved)
    related = entry_related(member, entry)
    assert [
        (pack.title, pack.owner.username, pack.item_count) for pack in related.public_packs
    ] == [("Dungeon Kit", "other_member", 1)]


def test_find_more_searches_discover_for_the_assets_kind_and_tags(member, make_asset):
    from catalog.library import entry_related

    entry = _save(member, make_asset, "brick", tags=["brick", "wall"])
    _save(member, make_asset, "other", tags=["wall"])  # "wall" is used more widely
    url = urlsplit(entry_related(member, entry).find_more_url)
    assert url.path == reverse("catalog:discover")
    assert parse_qs(url.query) == {"type": ["texture"], "q": ["wall brick"]}
    bare = _save(member, make_asset, "plain", title="Plain Plaster")
    assert parse_qs(urlsplit(entry_related(member, bare).find_more_url).query)["q"] == [
        "Plain Plaster"
    ]


def test_the_full_page_is_centred_with_the_related_column(member_client, member, make_asset):
    entry = _save(member, make_asset, "brick", tags=["brick"])
    _save(member, make_asset, "brick_two", tags=["brick"])
    html = member_client.get(reverse("catalog:entry", args=[entry.pk])).content.decode()
    layout = html.split('<section class="entry-layout">', 1)[1]
    assert layout.index('class="entry-page"') < layout.index('<aside class="entry-aside"')
    aside = layout.split('<aside class="entry-aside"', 1)[1].split("</aside>", 1)[0]
    assert "Similar in your library" in aside and "Brick_Two" in aside
    assert "Featured in public packs" in aside and "Find more like this on Discover" in aside
    # Plain links on the page; the drawer opens them in itself instead.
    assert "hx-get" not in aside.split('id="entry-similar"', 1)[1].split("</ul>", 1)[0]
    drawer = member_client.get(reverse("catalog:entry", args=[entry.pk]), HTTP_HX_REQUEST="true")
    similar = drawer.content.decode().split('id="entry-similar"', 1)[1].split("</ul>", 1)[0]
    assert 'hx-target="#library-drawer"' in similar
    from django.conf import settings

    source = (settings.BASE_DIR / "styles" / "source.css").read_text(encoding="utf-8")
    assert "margin-inline: auto;" in source.split(".entry-layout {", 1)[1].split("}", 1)[0]
    assert ".entry-page { max-width: 46rem;" not in source


def test_another_members_entry_page_stays_a_404(member, make_asset, django_user_model):
    entry = _save(member, make_asset, "brick")
    other = Client()
    other.force_login(django_user_model.objects.create_user("other_member"))
    assert other.get(reverse("catalog:entry", args=[entry.pk])).status_code == 404


# ---------------------------------------------------------------- the folding Tags list


def _tags(count):
    return [SimpleNamespace(name=f"tag {n:02}", uses=60 - n) for n in range(count)]


def test_the_tags_group_shows_eight_and_folds_the_rest():
    from catalog.library import TAG_CHIPS_SHOWN, clean_library_params, filter_groups

    group = filter_groups(clean_library_params({}), _tags(20))[-1]
    assert TAG_CHIPS_SHOWN == 8
    assert [chip.value for chip in group.lead_chips] == [f"tag {n:02}" for n in range(8)]
    assert len(group.more_chips) == 12 and not group.more_open


def test_a_chosen_tag_behind_the_fold_keeps_it_open():
    from catalog.library import clean_library_params, filter_groups

    group = filter_groups(clean_library_params({"tag": ["tag 15"]}), _tags(20))[-1]
    assert group.more_open


def test_the_library_renders_the_fold(member_client, member, make_asset):
    _save(member, make_asset, "many", tags=[f"tag{chr(97 + n)}" for n in range(12)])
    html = member_client.get(reverse("catalog:library")).content.decode()
    tags = html.split('aria-label="Tags"', 1)[1].split("</fieldset>", 1)[0]
    lead, fold = tags.split('<details class="filter-more"', 1)
    assert lead.count('name="tag"') == 8 and fold.count('name="tag"') == 4
    assert 'data-remember="ax-filter-more-tag"' in fold and "Show 4 more" in fold
    assert "open" not in fold.split(">", 1)[0]
    chosen = member_client.get(reverse("catalog:library") + "?tag=tagl").content.decode()
    fold = chosen.split('<details class="filter-more"', 1)[1].split(">", 1)[0]
    assert " open data-forced-open" in fold
