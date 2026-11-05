"""The community rating: every member's average rating for an asset, and how many rated it.

Added 2026-11-05 at the user's request. Each member's own rating stays
private: only the average and the count are shown, never who rated, and never
anyone's notes or status. It shows on library cards, in the drawer and on
Discover results, and the library can sort by it.
"""

import re

import pytest
from django.test import Client
from django.urls import reverse

from providers import AssetRecord, polyhaven

pytestmark = pytest.mark.django_db


@pytest.fixture
def members(django_user_model, password):
    return [
        django_user_model.objects.create_user(f"rater_{n}", password=password) for n in range(3)
    ]


def _save(user, asset, rating=None, **fields):
    from catalog.models import SavedAsset

    return SavedAsset.objects.create(user=user, asset=asset, rating=rating, **fields)


# ---------------------------------------------------------------- the queries


def test_the_average_counts_every_members_rating_and_skips_unrated(member, members, make_asset):
    from catalog.models import SavedAsset

    brick = make_asset(external_id="brick")
    mine = _save(member, brick, rating=4)
    _save(members[0], brick, rating=5)
    _save(members[1], brick, rating=2)
    _save(members[2], brick)  # saved, never rated: not counted
    entry = SavedAsset.objects.with_community_rating().get(pk=mine.pk)
    assert entry.community_rating == pytest.approx(11 / 3)
    assert entry.community_count == 3
    assert entry.community.count == 3


def test_an_asset_no_one_has_rated_has_no_community_rating(member, members, make_asset):
    from catalog.models import SavedAsset

    asset = make_asset()
    mine = _save(member, asset)
    _save(members[0], asset)
    entry = SavedAsset.objects.with_community_rating().get(pk=mine.pk)
    assert (entry.community_rating, entry.community_count, entry.community) == (None, 0, None)


def test_the_annotation_keeps_one_row_per_entry_and_only_the_members_own(
    member, members, make_asset
):
    from catalog.models import SavedAsset

    brick, sky = make_asset(external_id="brick"), make_asset(external_id="sky", kind="hdri")
    for user in [member, *members]:
        _save(user, brick, rating=3)
    _save(member, sky, rating=1)
    entries = SavedAsset.objects.for_user(member).with_community_rating()
    assert entries.count() == 2
    assert {e.asset.external_id: e.community_count for e in entries} == {"brick": 4, "sky": 1}


def test_discover_lookup_is_keyed_by_id_for_one_provider_and_skips_unrated(
    member, members, make_asset
):
    from catalog.models import CommunityRating, SavedAsset

    _save(member, make_asset(external_id="brick"), rating=4)
    _save(members[0], make_asset(external_id="tiles"))
    _save(members[1], make_asset(provider="ambientcg", external_id="brick"), rating=1)
    ratings = SavedAsset.objects.community_ratings("polyhaven", ["brick", "tiles", "unknown"])
    assert ratings == {"brick": CommunityRating(4.0, 1)}


def test_the_library_sorts_by_community_rating_with_unrated_assets_last(
    member, members, make_asset
):
    from catalog.library import filter_library

    top, tied_more, tied_fewer, none = (
        make_asset(external_id=name, title=name)
        for name in ("top", "tied_more", "tied_fewer", "none")
    )
    for asset in (none, tied_fewer, tied_more, top):
        _save(member, asset)
    _save(members[0], top, rating=5)
    for user in members[:2]:
        _save(user, tied_more, rating=3)
    _save(members[2], tied_fewer, rating=3)
    page = filter_library(member, {"sort": "community"}).page
    assert [entry.asset.title for entry in page] == ["top", "tied_more", "tied_fewer", "none"]


# ---------------------------------------------------------------- the pages


def _cards(html):
    return dict(
        re.findall(
            r'<li class="result-card library-card" id="entry-\d+" data-kind="\w+">.*?'
            r'class="result-link">([^<]+)</a>(.*?)</li>',
            html,
            re.S,
        )
    )


def _text(html):
    return " ".join(re.sub(r"<[^>]+>", " ", html).split())


def test_library_cards_show_the_average_and_count_never_who_rated(
    member, members, make_asset, member_client
):
    brick, sky = (
        make_asset(external_id="brick", title="Brick"),
        make_asset(external_id="sky", title="Sky"),
    )
    _save(member, brick, rating=4)
    _save(members[0], brick, rating=5, notes="secret rater note", status="rejected")
    _save(member, sky)
    html = member_client.get(reverse("catalog:library")).content.decode()
    cards = _cards(html)
    assert "Community rating 4.5 · 2 ratings" in _text(cards["Brick"])
    assert "community-rating" not in cards["Sky"]
    assert "rater_0" not in html and "secret rater note" not in html


def test_the_drawer_shows_the_community_rating_and_updates_it_after_a_rating(
    member, members, make_asset, member_client
):
    brick = make_asset(external_id="brick")
    mine = _save(member, brick)
    url = reverse("catalog:entry", args=[mine.pk])
    html = member_client.get(url, headers={"HX-Request": "true"}).content.decode()
    assert "No one has rated this yet." in html
    _save(members[0], brick, rating=2, notes="their private note", status="rejected")
    response = member_client.post(
        reverse("catalog:update", args=[mine.pk]),
        {"rating": "5"},
        headers={"HX-Request": "true", "HX-Current-URL": f"http://testserver{url}"},
    )
    html = response.content.decode()
    assert "their private note" not in html and "rater_0" not in html
    community = re.search(r'<p id="entry-community"[^>]*>.*?</p>', html, re.S)
    assert 'hx-swap-oob="true"' in community.group(0)
    assert "Community rating 3.5 · 2 ratings from every member who rated it, you included" in (
        _text(community.group(0))
    )


def test_a_status_or_notes_change_sends_no_community_rating(member, make_asset, member_client):
    mine = _save(member, make_asset())
    for data in ({"status": "approved"}, {"notes": "Hm."}):
        html = member_client.post(
            reverse("catalog:update", args=[mine.pk]), data, headers={"HX-Request": "true"}
        ).content.decode()
        assert 'id="entry-community"' not in html


def test_discover_results_show_their_community_rating_to_everyone(
    member, members, make_asset, monkeypatch
):
    def two_results(query, kind, limit=12, page=1):
        fields = {"title": "T", "author": "A", "thumbnail_url": "", "license": "CC0"}
        fields |= {"license_url": "", "attribution": "", "source_url": "", "tags": ()}
        return [
            AssetRecord(provider="polyhaven", external_id=external_id, kind="texture", **fields)
            for external_id in ("rated", "unrated")
        ]

    monkeypatch.setattr(polyhaven, "search_records", two_results)
    rated = make_asset(external_id="rated")
    _save(member, rated, rating=5, notes="secret note")
    _save(members[0], rated, rating=4)
    url = f"{reverse('catalog:discover_shelf', args=['texture', 'polyhaven'])}?q=brick"
    html = Client().get(url, headers={"HX-Request": "true"}).content.decode()
    cards = re.findall(r'<li class="result-card".*?</li>', html, re.S)
    assert len(cards) == 2
    assert "Community rating 4.5 · 2 ratings" in _text(cards[0])
    assert "community-rating" not in cards[1]
    assert "secret note" not in html and "demo_member" not in html and "rater_0" not in html
