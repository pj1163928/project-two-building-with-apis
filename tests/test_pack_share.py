"""Unlisted packs and their share links (user request, 2026-11-05, after Phase 8).

A pack can be private, unlisted or public. An unlisted pack opens for
anyone holding its share link (/packs/link/<token>/), and for no one else:
its slug page, the API and every list treat it as private for everyone but
its owner. The owner can make a new link, which retires the old one at once.

Access rules:
- An unlisted pack's slug page, download, API detail and API export are a
  404 to a visitor and another member (token or session), and work for the
  owner. The API list never holds another member's unlisted pack.
- Its share link's page and download work for everyone.
- A replaced link, a private pack's link and an unknown link are a 404.
- New link is the owner's alone (404 for another member, sign-in for a
  visitor), POST only, with CSRF (see also test_access_control.py).
"""

import json
import re

import pytest
from django.test import Client
from django.urls import reverse
from rest_framework.authtoken.models import Token

from catalog.models import SavedAsset
from packs.models import Pack
from packs.services import add_to_pack
from tests.test_pack_public import (  # noqa: F401 (pytest fixtures)
    PRIVATE_KEYS,
    SENTINEL,
    _keys,
    golden_pack,
)

pytestmark = pytest.mark.django_db

HTMX = {"HX-Request": "true"}
TOKEN_SHAPE = re.compile(r"^[A-Za-z0-9_-]{22}$")


@pytest.fixture
def other(django_user_model, password):
    return django_user_model.objects.create_user(username="other_member", password=password)


@pytest.fixture
def unlisted(member, make_asset):
    pack = Pack.objects.create_pack(member, "Secret Garden", "Shared with my team.", "moss")
    add_to_pack(pack, SavedAsset.objects.create(user=member, asset=make_asset()))
    pack.set_visibility("unlisted")
    return pack


def _signed_in(user):
    client = Client()
    client.force_login(user)
    return client


def _by_token(user):
    return Client(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=user).key}")


def _share_urls(pack):
    return [pack.get_share_url(), reverse("packs:shared_export", args=[pack.share_token])]


def _owner_urls(pack):
    """Every address by slug or id: the owner's alone while the pack is unlisted."""
    return [
        reverse("packs:public", args=[pack.slug]),
        reverse("packs:export", args=[pack.slug]),
        reverse("packs:api_pack", args=[pack.pk]),
        reverse("packs:api_pack_export", args=[pack.pk]),
    ]


# ---------------------------------------------------------------- the model


def test_unlisting_makes_an_unguessable_link_that_survives_visibility_changes(member):
    pack = Pack.objects.create_pack(member, "Kit")
    assert pack.share_token is None and pack.get_share_url() == ""

    pack.set_visibility("unlisted")
    token = pack.share_token
    assert TOKEN_SHAPE.match(token)
    assert pack.get_share_url() == f"/packs/link/{token}/"

    pack.set_visibility("private")
    pack.set_visibility("unlisted")
    pack.refresh_from_db()
    assert pack.share_token == token
    assert Pack.objects.create_pack(member, "Kit 2").share_token is None


def test_every_pack_gets_its_own_link(member):
    tokens = set()
    for number in range(5):
        pack = Pack.objects.create_pack(member, f"Kit {number}")
        pack.set_visibility("unlisted")
        tokens.add(pack.share_token)
    assert len(tokens) == 5


def test_an_unknown_visibility_is_refused(member):
    pack = Pack.objects.create_pack(member, "Kit")
    with pytest.raises(ValueError):
        pack.set_visibility("secret")
    pack.refresh_from_db()
    assert pack.visibility == "private"


def test_a_new_link_retires_the_old_one(unlisted):
    old = unlisted.share_token

    new = unlisted.rotate_share_token()

    assert new != old and TOKEN_SHAPE.match(new)
    assert not Pack.objects.shared_by_link(old).exists()
    assert Pack.objects.shared_by_link(new).get() == unlisted
    unlisted.refresh_from_db()
    assert unlisted.visibility == "unlisted"


def test_a_link_opens_an_unlisted_or_public_pack_but_never_a_private_one(unlisted):
    token = unlisted.share_token
    assert Pack.objects.shared_by_link(token).get() == unlisted
    unlisted.set_visibility("public")
    assert Pack.objects.shared_by_link(token).get() == unlisted
    unlisted.set_visibility("private")
    assert not Pack.objects.shared_by_link(token).exists()
    assert not Pack.objects.shared_by_link("").exists()


def test_an_unlisted_pack_is_never_listed_for_anyone_else(member, other, unlisted):
    from django.contrib.auth.models import AnonymousUser

    assert unlisted in Pack.objects.visible_to(member)
    assert unlisted not in Pack.objects.visible_to(other)
    assert unlisted not in Pack.objects.visible_to(AnonymousUser())
    assert unlisted not in Pack.objects.public()


def test_featured_in_public_packs_never_lists_an_unlisted_pack(unlisted, other):
    asset = unlisted.ordered_items()[0].asset
    assert not Pack.objects.public_featuring(asset, exclude_owner=other).exists()


# ---------------------------------------------------------------- reading by link and by slug


@pytest.mark.parametrize("who", ["visitor", "other", "owner"])
def test_the_share_link_opens_the_page_and_the_download_for_anyone(unlisted, member, other, who):
    client = {"visitor": Client(), "other": _signed_in(other), "owner": _signed_in(member)}[who]
    page_url, export_url = _share_urls(unlisted)

    page = client.get(page_url)
    assert page.status_code == 200
    html = page.content.decode()
    assert "Secret Garden" in html and "Unlisted pack" in html
    assert f'<a href="{export_url}"' in html
    assert page["X-Robots-Tag"] == "noindex, nofollow"
    # The token never leaves the site in a Referer header (SecurityMiddleware).
    assert page["Referrer-Policy"] == "same-origin"

    download = client.get(export_url)
    assert download.status_code == 200
    assert download["X-Robots-Tag"] == "noindex, nofollow"
    manifest = json.loads(download.content)
    assert manifest["pack"]["source_url"] == f"http://testserver{page_url}"
    assert len(manifest["items"]) == 1


@pytest.mark.parametrize("who", ["visitor", "other_session", "other_token"])
def test_an_unlisted_pack_is_404_by_slug_and_id_to_anyone_else(unlisted, other, who):
    client = {
        "visitor": Client(),
        "other_session": _signed_in(other),
        "other_token": _by_token(other),
    }[who]
    for url in _owner_urls(unlisted):
        assert client.get(url).status_code == 404, f"{who}: {url}"


@pytest.mark.parametrize("client_for", [_signed_in, _by_token])
def test_the_owner_still_reads_their_unlisted_pack_by_slug_and_id(unlisted, member, client_for):
    client = client_for(member)
    urls = _owner_urls(unlisted)
    if client_for is _by_token:
        urls = urls[2:]  # the website pages go by session
    for url in urls:
        assert client.get(url).status_code == 200, url


def test_the_api_list_holds_an_unlisted_pack_for_its_owner_only(unlisted, member, other):
    url = reverse("packs:api_packs")
    assert Client().get(url).json()["results"] == []
    assert _by_token(other).get(url).json()["results"] == []

    mine = _by_token(member).get(url).json()["results"]
    assert [pack["visibility"] for pack in mine] == ["unlisted"]
    assert mine[0]["page_url"] == f"http://testserver{unlisted.get_share_url()}"


def test_a_replaced_link_is_404_and_the_new_one_works(unlisted):
    old_urls = _share_urls(unlisted)
    unlisted.rotate_share_token()

    for url in old_urls:
        assert Client().get(url).status_code == 404, url
    for url in _share_urls(unlisted):
        assert Client().get(url).status_code == 200, url


def test_a_private_packs_link_is_404(unlisted, member):
    urls = _share_urls(unlisted)
    unlisted.set_visibility("private")

    for url in urls:
        assert Client().get(url).status_code == 404, url
        # Even for the owner: a private pack is read by its slug.
        assert _signed_in(member).get(url).status_code == 404, url


def test_a_public_packs_link_goes_to_its_page(unlisted):
    unlisted.set_visibility("public")

    response = Client().get(unlisted.get_share_url())

    assert response.status_code == 302
    assert response.url == reverse("packs:public", args=[unlisted.slug])


def test_an_unknown_link_is_404():
    for url in ("/packs/link/not-a-real-token-at-all/", "/packs/link/nope/export/"):
        assert Client().get(url).status_code == 404


def test_link_is_never_a_pack_slug(member):
    assert Pack.objects.create_pack(member, "Link").slug == "link-2"


def test_the_owners_review_never_shows_through_the_share_link(golden_pack, member, other):  # noqa: F811
    entry = SavedAsset.objects.get(user=member, asset__external_id="red_brick_03")
    entry.notes, entry.rating, entry.status = SENTINEL, 4, SavedAsset.Status.REJECTED
    entry.save()
    golden_pack.set_visibility("unlisted")
    page_url, export_url = _share_urls(golden_pack)

    for client in (Client(), _signed_in(other), _signed_in(member)):
        html = client.get(page_url).content.decode()
        content = html.split('id="content"', 1)[1].split('id="page-footer"', 1)[0]
        assert SENTINEL not in html
        for private in ("Rejected", "rejected", "star-rating", "rate-star", "community"):
            assert private not in content
        body = client.get(export_url).content.decode()
        assert SENTINEL not in body and "rejected" not in body.lower()
        assert not _keys(json.loads(body)) & PRIVATE_KEYS


# ---------------------------------------------------------------- the builder


def test_choosing_unlisted_shows_the_share_link(member_client, member):
    pack = Pack.objects.create_pack(member, "Kit")

    response = member_client.post(
        reverse("packs:visibility", args=[pack.pk]), {"visibility": "unlisted"}, headers=HTMX
    )

    assert response.status_code == 200
    pack.refresh_from_db()
    assert pack.visibility == "unlisted" and pack.share_token
    html = response.content.decode()
    assert 'value="unlisted" checked' in html
    assert "Anyone with the link can view and export it. It isn't listed anywhere." in html
    assert f'value="http://testserver{pack.get_share_url()}" readonly' in html
    assert 'data-copy="pack-share-url"' in html
    assert 'data-dialog-open="pack-rotate-dialog"' in html


@pytest.mark.parametrize(
    "visibility, shown", [("private", False), ("public", False), ("unlisted", True)]
)
def test_the_builder_shows_the_share_link_only_while_unlisted(
    member_client, member, visibility, shown
):
    pack = Pack.objects.create_pack(member, "Kit")
    pack.set_visibility(visibility)

    html = member_client.get(reverse("packs:builder", args=[pack.pk])).content.decode()

    assert html.count('name="visibility"') == 3
    assert ('id="pack-share"' in html) is shown
    assert 'id="pack-rotate-dialog"' in html
    assert re.search(rf'<a id="pack-page-link" href="{re.escape(pack.reader_url)}"', html)


def test_new_link_replaces_the_link_and_says_so(member_client, unlisted):
    old = unlisted.share_token

    response = member_client.post(reverse("packs:rotate_link", args=[unlisted.pk]), headers=HTMX)

    assert response.status_code == 200
    unlisted.refresh_from_db()
    assert unlisted.share_token != old
    html = response.content.decode()
    assert html.lstrip().startswith('<div id="pack-share"')
    assert f'value="http://testserver{unlisted.get_share_url()}"' in html
    assert "New link made. The old one no longer works." in html


def test_new_link_without_htmx_goes_back_to_the_builder(member_client, unlisted):
    response = member_client.post(reverse("packs:rotate_link", args=[unlisted.pk]))

    assert response.status_code == 302
    assert response.url == reverse("packs:builder", args=[unlisted.pk])


def test_new_link_is_post_only(member_client, unlisted):
    old = unlisted.share_token
    assert member_client.get(reverse("packs:rotate_link", args=[unlisted.pk])).status_code == 405
    unlisted.refresh_from_db()
    assert unlisted.share_token == old


def test_new_link_needs_csrf(member, unlisted):
    old = unlisted.share_token
    client = Client(enforce_csrf_checks=True)
    client.force_login(member)

    response = client.post(reverse("packs:rotate_link", args=[unlisted.pk]), headers=HTMX)

    assert response.status_code == 403
    unlisted.refresh_from_db()
    assert unlisted.share_token == old


def test_the_pack_list_marks_an_unlisted_pack_and_links_its_share_link(member_client, unlisted):
    html = member_client.get(reverse("packs:list")).content.decode()

    assert '<span class="status-chip micro" data-visibility="unlisted">Unlisted</span>' in html
    assert f'href="{unlisted.get_share_url()}" class="pack-card-page' in html


def test_the_owner_sees_their_unlisted_pack_marked_link_only(member_client, unlisted):
    html = member_client.get(reverse("packs:public", args=[unlisted.slug])).content.decode()

    assert "Unlisted · link only" in html
