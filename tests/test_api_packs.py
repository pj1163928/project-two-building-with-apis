"""The pack API: /api/packs/, /api/packs/<id>/ and /api/packs/<id>/export/ (Phase 8).

Access rules (the PRD's pack rows, on the API, with the website's alongside):
- A private pack's detail and export are a 404 to signed-out visitors and to
  other members, by token or session, and work for the owner.
- A public pack's detail and export work for everyone.
- The list never holds another member's private pack.
- ?mine=1 is refused (401) when signed out.
- POST, PUT, PATCH and DELETE are a 405 on every pack URL, and change nothing.
"""

import json

import pytest
from django.test import Client
from django.urls import reverse
from rest_framework.authtoken.models import Token

from catalog.models import SavedAsset
from packs.models import Pack
from packs.services import add_to_pack

pytestmark = pytest.mark.django_db


@pytest.fixture
def other(django_user_model, password):
    return django_user_model.objects.create_user(username="other_member", password=password)


def _pack(owner, title, *, public=False, assets=()):
    pack = Pack.objects.create_pack(owner, title, "For a test.", "stone")
    for asset in assets:
        entry, _ = SavedAsset.objects.get_or_create(user=owner, asset=asset)
        add_to_pack(pack, entry)
    if public:
        pack.set_visibility("public")
    return pack


@pytest.fixture
def private_pack(member, make_asset):
    return _pack(member, "Private Kit", assets=[make_asset()])


@pytest.fixture
def public_pack(member, make_asset):
    return _pack(member, "Public Kit", public=True, assets=[make_asset(external_id="moss_01")])


def _token_client(user):
    return Client(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=user).key}")


def _session_client(user):
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def readers(member, other):
    """Every kind of caller, by name: the owner (session and token), another
    member (session and token) and a signed-out visitor."""
    return {
        "owner_session": _session_client(member),
        "owner_token": _token_client(member),
        "other_session": _session_client(other),
        "other_token": _token_client(other),
        "visitor": Client(),
    }


OWNER = ("owner_session", "owner_token")
NOT_OWNER = ("other_session", "other_token", "visitor")


# ---------------------------------------------------------------- the export rule asked for by name


def test_a_private_packs_export_is_404_to_a_visitor_and_another_member_and_works_for_the_owner(
    private_pack, member, other
):
    """Both export endpoints, the website download and the API's: a signed-out
    visitor and another signed-in member get a 404, and the owner gets the
    manifest."""
    urls = [
        reverse("packs:export", args=[private_pack.slug]),
        reverse("packs:api_pack_export", args=[private_pack.pk]),
    ]
    visitor = Client()
    another_member = _session_client(other)
    owner = _session_client(member)
    for url in urls:
        assert visitor.get(url).status_code == 404, url
        assert another_member.get(url).status_code == 404, url
        response = owner.get(url)
        assert response.status_code == 200, url
        manifest = json.loads(response.content)
        assert manifest["format"] == "axcenity-pack"
        assert manifest["pack"]["slug"] == private_pack.slug


# ---------------------------------------------------------------- the access table, row by row


@pytest.mark.parametrize("who", NOT_OWNER)
def test_a_private_pack_is_404_everywhere_to_anyone_but_its_owner(readers, private_pack, who):
    client = readers[who]
    urls = [
        reverse("packs:public", args=[private_pack.slug]),
        reverse("packs:export", args=[private_pack.slug]),
        reverse("packs:api_pack", args=[private_pack.pk]),
        reverse("packs:api_pack_export", args=[private_pack.pk]),
    ]
    for url in urls:
        assert client.get(url).status_code == 404, f"{who}: {url}"


@pytest.mark.parametrize("who", OWNER)
def test_a_private_pack_works_everywhere_for_its_owner(readers, private_pack, who):
    client = readers[who]
    for url in (
        reverse("packs:api_pack", args=[private_pack.pk]),
        reverse("packs:api_pack_export", args=[private_pack.pk]),
    ):
        assert client.get(url).status_code == 200, f"{who}: {url}"
    if who == "owner_session":
        assert client.get(reverse("packs:public", args=[private_pack.slug])).status_code == 200
        assert client.get(reverse("packs:export", args=[private_pack.slug])).status_code == 200


@pytest.mark.parametrize("who", OWNER + NOT_OWNER)
def test_a_public_pack_works_everywhere_for_everyone(readers, public_pack, who):
    client = readers[who]
    urls = [
        reverse("packs:public", args=[public_pack.slug]),
        reverse("packs:export", args=[public_pack.slug]),
        reverse("packs:api_pack", args=[public_pack.pk]),
        reverse("packs:api_pack_export", args=[public_pack.pk]),
    ]
    for url in urls:
        assert client.get(url).status_code == 200, f"{who}: {url}"


def test_a_pack_that_doesnt_exist_is_404(readers):
    for client in readers.values():
        assert client.get(reverse("packs:api_pack", args=[9999])).status_code == 404
        assert client.get(reverse("packs:api_pack_export", args=[9999])).status_code == 404
        assert client.get(reverse("packs:public", args=["no-such-pack"])).status_code == 404


# ---------------------------------------------------------------- the list


def _titles(response):
    assert response.status_code == 200
    return {pack["title"] for pack in response.json()["results"]}


def test_the_list_is_public_packs_plus_the_callers_own(readers, member, other, make_asset):
    _pack(member, "Mine Private")
    _pack(member, "Mine Public", public=True)
    _pack(other, "Theirs Private")
    _pack(other, "Theirs Public", public=True)
    url = reverse("packs:api_packs")

    assert _titles(readers["visitor"].get(url)) == {"Mine Public", "Theirs Public"}
    for who in OWNER:
        assert _titles(readers[who].get(url)) == {"Mine Private", "Mine Public", "Theirs Public"}
    for who in ("other_session", "other_token"):
        assert _titles(readers[who].get(url)) == {"Theirs Private", "Theirs Public", "Mine Public"}


def test_mine_lists_only_the_callers_own_packs(readers, member, other):
    _pack(member, "Mine Private")
    _pack(member, "Mine Public", public=True)
    _pack(other, "Theirs Public", public=True)
    url = reverse("packs:api_packs") + "?mine=1"

    for who in OWNER:
        assert _titles(readers[who].get(url)) == {"Mine Private", "Mine Public"}


def test_mine_is_refused_when_signed_out(public_pack):
    response = Client().get(reverse("packs:api_packs") + "?mine=1")

    assert response.status_code == 401
    assert response["WWW-Authenticate"] == "Token"
    assert "results" not in response.json()


def test_the_list_pages_by_twelve_newest_change_first(member):
    for number in range(14):
        _pack(member, f"Kit {number:02d}", public=True)
    url = reverse("packs:api_packs")

    first = Client().get(url).json()
    assert (first["count"], first["page"], first["num_pages"]) == (14, 1, 2)
    assert len(first["results"]) == 12
    assert first["results"][0]["title"] == "Kit 13"
    assert first["previous"] is None
    assert first["next"] == "http://testserver/api/packs/?page=2"
    second = Client().get(first["next"]).json()
    assert [pack["title"] for pack in second["results"]] == ["Kit 01", "Kit 00"]
    # A bad page is the first; one past the end is the last, as on the library API.
    assert Client().get(url + "?page=abc").json()["page"] == 1
    assert Client().get(url + "?page=99").json()["page"] == 2


def test_mine_keeps_itself_in_the_page_links(readers, member):
    for number in range(13):
        _pack(member, f"Kit {number:02d}")

    data = readers["owner_token"].get(reverse("packs:api_packs") + "?mine=1").json()

    assert data["next"] == "http://testserver/api/packs/?mine=1&page=2"


def test_a_listed_pack_says_where_to_read_see_and_export_it(public_pack):
    data = Client().get(reverse("packs:api_packs")).json()["results"][0]

    assert data["id"] == public_pack.pk
    assert data["slug"] == "public-kit"
    assert data["author"] == "demo_member"
    assert data["tags"] == ["stone"]
    assert data["visibility"] == "public"
    assert data["item_count"] == 1
    assert data["url"] == f"http://testserver/api/packs/{public_pack.pk}/"
    assert data["export_url"] == f"http://testserver/api/packs/{public_pack.pk}/export/"
    assert data["page_url"] == "http://testserver/packs/public-kit/"
    assert "items" not in data


# ---------------------------------------------------------------- detail


def test_detail_lists_items_in_position_order_with_pack_item_and_asset_fields(member, make_asset):
    pack = _pack(
        member,
        "Ordered",
        public=True,
        assets=[make_asset(external_id="first_01"), make_asset(external_id="second_02")],
    )
    first, second = pack.ordered_items()
    first.position, second.position = 1, 0
    first.import_path = "props/first/"
    first.save()
    second.save()

    data = Client().get(reverse("packs:api_pack", args=[pack.pk])).json()

    assert [item["asset"]["external_id"] for item in data["items"]] == ["second_02", "first_01"]
    item = data["items"][1]
    assert set(item) == {
        "id",
        "position",
        "preferred_variant",
        "import_path",
        "default_import_path",
        "asset",
    }
    assert item["import_path"] == "props/first/"
    assert item["default_import_path"] == "textures/first_01/"
    assert item["asset"]["provider"] == "polyhaven"
    assert item["asset"]["license"] == "CC0"


# ---------------------------------------------------------------- export


def test_the_website_download_and_the_api_export_are_the_same_manifest(
    public_pack, member, monkeypatch
):
    from datetime import UTC, datetime

    from django.utils import timezone

    frozen = datetime(2026, 11, 5, 12, 0, tzinfo=UTC)
    monkeypatch.setattr(timezone, "now", lambda: frozen)

    for client in (Client(), _session_client(member), _token_client(member)):
        site = client.get(reverse("packs:export", args=[public_pack.slug]))
        api = client.get(reverse("packs:api_pack_export", args=[public_pack.pk]))
        assert json.loads(site.content) == api.json()
    manifest = api.json()
    assert manifest["exported_at"] == "2026-11-05T12:00:00+00:00"
    assert manifest["pack"]["source_url"] == "http://testserver/packs/public-kit/"


def test_the_website_download_is_a_json_file_named_for_the_pack(public_pack):
    response = Client().get(reverse("packs:export", args=[public_pack.slug]))

    assert response["Content-Type"] == "application/json"
    assert response["Content-Disposition"] == 'attachment; filename="public-kit.axcenity-pack.json"'


# ---------------------------------------------------------------- read-only


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
@pytest.mark.parametrize("who", ["owner_session", "owner_token", "other_token", "visitor"])
def test_the_pack_api_is_read_only(readers, public_pack, method, who):
    client = readers[who]
    urls = [
        reverse("packs:api_packs"),
        reverse("packs:api_pack", args=[public_pack.pk]),
        reverse("packs:api_pack_export", args=[public_pack.pk]),
    ]
    body = json.dumps({"title": "Renamed", "visibility": "private"})
    for url in urls:
        response = getattr(client, method)(url, data=body, content_type="application/json")
        assert response.status_code == 405, f"{who} {method} {url}"
    public_pack.refresh_from_db()
    assert (public_pack.title, public_pack.is_public) == ("Public Kit", True)
    assert Pack.objects.count() == 1


def test_the_website_download_is_get_only(member_client, public_pack):
    response = member_client.post(reverse("packs:export", args=[public_pack.slug]))

    assert response.status_code == 405
