"""The library API: /api/library/ and /api/library/<id>/ (Phase 6).

Access rules:
- Signed-out requests are refused (401) and change nothing.
- Another member's entry, or one that doesn't exist, is a 404 for GET,
  PATCH, PUT and DELETE, and nothing changes.
- The list only ever holds the caller's entries.
- A session POST, PATCH, PUT or DELETE without a CSRF token is refused
  (403); the same request signed with a token succeeds without one.

Provider functions are replaced with monkeypatch, never reached over HTTP.
"""

import json

import pytest
from django.test import Client
from django.urls import reverse

from catalog.models import Asset, SavedAsset
from providers import PROVIDERS, ProviderError, polyhaven

pytestmark = pytest.mark.django_db


@pytest.fixture
def other_member(django_user_model, password):
    return django_user_model.objects.create_user(username="other_member", password=password)


@pytest.fixture
def fetches(monkeypatch):
    """Replace every provider's fetch_record(); the list records each (provider, ID) asked for."""
    from tests.test_library_save import full_record

    calls = []
    for source in PROVIDERS:

        def fake(external_id, key=source.KEY):
            calls.append((key, external_id))
            return full_record(provider=key, external_id=external_id)

        monkeypatch.setattr(source, "fetch_record", fake)
    return calls


def entry_url(entry):
    return reverse("catalog:api_entry", args=[entry.pk])


def send(client, method, url, data=None):
    """One API request with a JSON body, as a script would send it (none for GET)."""
    if method == "get":
        return client.get(url)
    body = json.dumps(data) if data is not None else ""
    return getattr(client, method)(url, data=body, content_type="application/json")


# ---------------------------------------------------------------- access


@pytest.mark.parametrize(
    "method, data",
    [
        ("get", None),
        ("patch", {"notes": "mine now", "rating": 1, "status": "rejected"}),
        ("put", {"notes": "mine now", "rating": 1, "status": "rejected"}),
        ("delete", None),
    ],
)
def test_another_members_entry_is_404_and_unchanged(
    member_client, other_member, make_asset, method, data
):
    theirs = SavedAsset.objects.create(
        user=other_member, asset=make_asset(), notes="private", rating=5, status="approved"
    )

    response = send(member_client, method, entry_url(theirs), data)

    assert response.status_code == 404
    assert "private" not in response.content.decode()
    theirs.refresh_from_db()
    assert (theirs.notes, theirs.rating, theirs.status) == ("private", 5, "approved")


# ---------------------------------------------------------------- create


def test_create_for_an_asset_already_in_the_library_is_400_and_changes_nothing(
    member_client, member, make_asset, fetches
):
    mine = SavedAsset.objects.create(
        user=member, asset=make_asset(), notes="keep me", rating=4, status="testing"
    )

    response = send(
        member_client,
        "post",
        reverse("catalog:api_library"),
        {"provider": "polyhaven", "external_id": "red_brick_03", "notes": "new", "rating": 1},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Already in your library."}
    assert fetches == []
    assert SavedAsset.objects.filter(user=member).count() == 1
    mine.refresh_from_db()
    assert (mine.notes, mine.rating, mine.status) == ("keep me", 4, "testing")


def test_create_with_a_provider_failure_is_502_with_its_message_and_saves_nothing(
    member, monkeypatch
):
    message = "Poly Haven didn't answer in time. Try again in a moment."

    def failing(external_id):
        raise ProviderError(message)

    monkeypatch.setattr(polyhaven, "fetch_record", failing)
    client = Client(raise_request_exception=False)
    client.force_login(member)

    response = send(
        client,
        "post",
        reverse("catalog:api_library"),
        {"provider": "polyhaven", "external_id": "red_brick_03", "notes": "hello"},
    )

    assert response.status_code == 502
    assert response.json() == {"detail": message}
    assert not Asset.objects.exists()
    assert not SavedAsset.objects.exists()


def test_create_for_a_new_asset_fetches_it_once_and_stores_the_review(
    member_client, member, fetches
):
    response = send(
        member_client,
        "post",
        reverse("catalog:api_library"),
        {
            "provider": "polyhaven",
            "external_id": "red_brick_03",
            "notes": "line one\r\nline two",
            "rating": 4,
            "status": "testing",
        },
    )

    assert response.status_code == 201
    assert fetches == [("polyhaven", "red_brick_03")]
    entry = SavedAsset.objects.get(user=member)
    assert (entry.notes, entry.rating, entry.status) == ("line one\nline two", 4, "testing")
    body = response.json()
    assert body["id"] == entry.pk
    assert body["asset"]["external_id"] == "red_brick_03"
    assert body["asset"]["tags"] == ["mossy stone", "rock"]
    assert body["community"] == {"average": 4.0, "count": 1}
    assert "provider" not in body and "external_id" not in body


def test_create_with_only_provider_and_id_starts_as_to_review_unrated(member_client, fetches):
    response = send(
        member_client,
        "post",
        reverse("catalog:api_library"),
        {"provider": "polyhaven", "external_id": "red_brick_03"},
    )

    assert response.status_code == 201
    body = response.json()
    assert (body["notes"], body["rating"], body["status"]) == ("", None, "to_review")
    assert body["community"] is None


def test_create_for_an_asset_stored_by_another_member_reuses_it_without_fetching(
    member_client, member, other_member, make_asset, fetches
):
    asset = make_asset()
    SavedAsset.objects.create(user=other_member, asset=asset)

    response = send(
        member_client,
        "post",
        reverse("catalog:api_library"),
        {"provider": "polyhaven", "external_id": "red_brick_03"},
    )

    assert response.status_code == 201
    assert fetches == []
    assert SavedAsset.objects.get(user=member).asset == asset
    assert Asset.objects.count() == 1


@pytest.mark.parametrize(
    "data, field",
    [
        ({"provider": "sketchfab", "external_id": "x"}, "provider"),
        ({"external_id": "x"}, "provider"),
        ({"provider": "polyhaven"}, "external_id"),
        ({"provider": "polyhaven", "external_id": ""}, "external_id"),
        ({"provider": "polyhaven", "external_id": "x" * 201}, "external_id"),
        ({"provider": "polyhaven", "external_id": "x", "rating": 6}, "rating"),
        ({"provider": "polyhaven", "external_id": "x", "rating": 0}, "rating"),
        ({"provider": "polyhaven", "external_id": "x", "status": "done"}, "status"),
        ({"provider": "polyhaven", "external_id": "x", "notes": "n" * 10_001}, "notes"),
    ],
)
def test_create_with_bad_values_is_400_before_any_provider_call(
    member_client, fetches, data, field
):
    response = send(member_client, "post", reverse("catalog:api_library"), data)

    assert response.status_code == 400
    assert field in response.json()
    assert fetches == []
    assert not SavedAsset.objects.exists()


# ---------------------------------------------------------------- list


@pytest.fixture
def library(member, other_member, make_asset):
    """A small library for the member (plus one entry of another member's)."""
    from catalog.models import Tag

    brick, moss = Tag.objects.create(name="brick"), Tag.objects.create(name="moss")
    rows = [
        ("Red Brick", "polyhaven", "texture", 5, "approved", [brick]),
        ("Mossy Rock", "ambientcg", "texture", None, "testing", [moss]),
        ("Brick Wall", "ambientcg", "texture", 3, "to_review", [brick, moss]),
        ("Forest HDRI", "polyhaven", "hdri", 4, "to_review", []),
        ("Rain Loop", "openverse", "sound", None, "rejected", []),
    ]
    entries = []
    for number, (title, provider, kind, rating, status, tags) in enumerate(rows):
        asset = make_asset(provider=provider, external_id=f"asset_{number}", kind=kind, title=title)
        asset.tags.set(tags)
        entries.append(
            SavedAsset.objects.create(
                user=member, asset=asset, rating=rating, status=status, notes=f"note {title}"
            )
        )
    # Another member rates the HDRI, so the community sort differs from the rating sort.
    SavedAsset.objects.create(user=other_member, asset=entries[3].asset, rating=5)
    SavedAsset.objects.create(
        user=other_member, asset=make_asset(external_id="theirs", title="Their Brick"), rating=5
    )
    return entries


@pytest.mark.parametrize(
    "query",
    [
        "",
        "q=brick",
        "type=texture&provider=ambientcg",
        "status=to_review&status=testing",
        "tag=brick&tag=moss",
        "min_rating=4",
        "sort=title",
        "sort=rating",
        "sort=community",
        "sort=oldest",
        "sort=nonsense&type=nonsense",
    ],
)
def test_list_returns_the_same_entries_in_the_same_order_as_the_library_page(
    member_client, library, query
):
    page = member_client.get(f"{reverse('catalog:library')}?{query}")
    api = member_client.get(f"{reverse('catalog:api_library')}?{query}")

    assert api.status_code == 200
    website_ids = [entry.pk for entry in page.context["entries"]]
    assert [row["id"] for row in api.json()["results"]] == website_ids
    assert api.json()["count"] == page.context["results"].page.paginator.count


def test_list_holds_only_the_callers_entries_with_their_review(member_client, library):
    body = member_client.get(reverse("catalog:api_library")).json()

    assert body["count"] == 5
    assert "Their Brick" not in json.dumps(body)
    hdri = next(row for row in body["results"] if row["asset"]["title"] == "Forest HDRI")
    assert (hdri["notes"], hdri["rating"], hdri["status"]) == ("note Forest HDRI", 4, "to_review")
    assert hdri["community"] == {"average": 4.5, "count": 2}


def test_list_pages_by_12_with_tidy_api_links(member_client, member, make_asset):
    for number in range(14):
        SavedAsset.objects.create(user=member, asset=make_asset(external_id=f"a{number}"))
    url = reverse("catalog:api_library")

    first = member_client.get(f"{url}?sort=title&type=nonsense").json()
    second = member_client.get(f"{url}?sort=title&page=2").json()
    past_the_end = member_client.get(f"{url}?page=99").json()

    assert (first["count"], first["page"], first["num_pages"]) == (14, 1, 2)
    assert len(first["results"]) == 12
    assert first["previous"] is None
    assert first["next"] == f"http://testserver{url}?sort=title&page=2"
    assert len(second["results"]) == 2
    assert second["previous"] == f"http://testserver{url}?sort=title"
    assert second["next"] is None
    assert past_the_end["page"] == 2


def test_list_for_an_empty_library(member_client):
    body = member_client.get(reverse("catalog:api_library")).json()

    assert body == {
        "count": 0,
        "page": 1,
        "num_pages": 1,
        "next": None,
        "previous": None,
        "results": [],
    }


# ---------------------------------------------------------------- one entry


@pytest.fixture
def mine(member, make_asset):
    return SavedAsset.objects.create(
        user=member, asset=make_asset(), notes="first", rating=2, status="testing"
    )


def test_get_reads_one_entry(member_client, mine):
    body = member_client.get(entry_url(mine)).json()

    assert body["id"] == mine.pk
    assert (body["notes"], body["rating"], body["status"]) == ("first", 2, "testing")
    assert body["asset"]["title"] == "Red Brick 03"
    assert body["community"] == {"average": 2.0, "count": 1}


def test_patch_changes_only_the_fields_sent(member_client, mine):
    response = send(member_client, "patch", entry_url(mine), {"rating": 5})

    assert response.status_code == 200
    assert response.json()["community"] == {"average": 5.0, "count": 1}
    mine.refresh_from_db()
    assert (mine.notes, mine.rating, mine.status) == ("first", 5, "testing")


def test_patch_can_clear_the_rating(member_client, mine):
    response = send(member_client, "patch", entry_url(mine), {"rating": None})

    assert response.status_code == 200
    mine.refresh_from_db()
    assert mine.rating is None


def test_put_changes_notes_rating_and_status(member_client, mine):
    response = send(
        member_client,
        "put",
        entry_url(mine),
        {"notes": "second", "rating": 3, "status": "approved"},
    )

    assert response.status_code == 200
    mine.refresh_from_db()
    assert (mine.notes, mine.rating, mine.status) == ("second", 3, "approved")


@pytest.mark.parametrize("method", ["patch", "put"])
def test_asset_fields_in_an_update_are_ignored(member_client, mine, method):
    response = send(
        member_client,
        method,
        entry_url(mine),
        {
            "notes": "changed",
            "id": 999,
            "saved_at": "2000-01-01T00:00:00Z",
            "provider": "openverse",
            "external_id": "other",
            "title": "Hijacked",
            "asset": {"title": "Hijacked", "license": "none", "external_id": "other"},
            "community": {"average": 5, "count": 99},
        },
    )

    assert response.status_code == 200
    mine.refresh_from_db()
    assert mine.notes == "changed"
    assert mine.pk == response.json()["id"]
    assert mine.saved_at.year != 2000
    asset = Asset.objects.get()
    assert (asset.title, asset.license, asset.external_id) == (
        "Red Brick 03",
        "CC0",
        "red_brick_03",
    )
    assert response.json()["community"] == {"average": 2.0, "count": 1}


@pytest.mark.parametrize(
    "data, field",
    [({"rating": 6}, "rating"), ({"rating": 0}, "rating"), ({"status": "done"}, "status")],
)
def test_bad_update_values_are_400_and_save_nothing(member_client, mine, data, field):
    response = send(member_client, "patch", entry_url(mine), data)

    assert response.status_code == 400
    assert field in response.json()
    mine.refresh_from_db()
    assert (mine.notes, mine.rating, mine.status) == ("first", 2, "testing")


def test_delete_removes_the_entry_and_leaves_the_shared_asset(member_client, other_member, mine):
    SavedAsset.objects.create(user=other_member, asset=mine.asset)

    response = member_client.delete(entry_url(mine))

    assert response.status_code == 204
    assert not SavedAsset.objects.filter(pk=mine.pk).exists()
    assert Asset.objects.filter(pk=mine.asset_id).exists()
    assert SavedAsset.objects.filter(user=other_member).count() == 1


def test_the_entry_endpoints_documentation_says_delete_also_leaves_your_packs(member_client, mine):
    description = member_client.options(entry_url(mine)).json()["description"]

    assert "DELETE removes the entry from your library and from every one of your packs" in (
        " ".join(description.split())
    )


def test_an_entry_that_doesnt_exist_is_404(member_client):
    assert member_client.get(reverse("catalog:api_entry", args=[9999])).status_code == 404


# ---------------------------------------------------------------- signed out


@pytest.mark.parametrize(
    "method, name",
    [
        ("get", "catalog:api_library"),
        ("post", "catalog:api_library"),
        ("get", "catalog:api_entry"),
        ("patch", "catalog:api_entry"),
        ("put", "catalog:api_entry"),
        ("delete", "catalog:api_entry"),
    ],
)
def test_signed_out_requests_are_refused_and_change_nothing(
    client, member, make_asset, fetches, method, name
):
    entry = SavedAsset.objects.create(user=member, asset=make_asset(), notes="kept")
    url = reverse(name, args=[entry.pk] if name == "catalog:api_entry" else [])

    data = None if method == "get" else {"provider": "polyhaven", "external_id": "x", "notes": "no"}
    response = send(client, method, url, data)

    assert response.status_code == 401
    assert response["WWW-Authenticate"] == "Token"
    assert "kept" not in response.content.decode()
    entry.refresh_from_db()
    assert entry.notes == "kept"
    assert SavedAsset.objects.count() == 1
    assert fetches == []


def test_a_wrong_token_is_refused(client, mine):
    response = client.get(
        reverse("catalog:api_library"), headers={"Authorization": "Token not-a-real-key"}
    )

    assert response.status_code == 401


# ---------------------------------------------------------------- CSRF and tokens

WRITES = [
    ("post", "catalog:api_library", {"provider": "polyhaven", "external_id": "new_one"}, 201),
    ("patch", "catalog:api_entry", {"notes": "changed"}, 200),
    ("put", "catalog:api_entry", {"notes": "changed", "rating": 3, "status": "approved"}, 200),
    ("delete", "catalog:api_entry", None, 204),
]


def _write_url(name, entry):
    return reverse(name, args=[entry.pk] if name == "catalog:api_entry" else [])


@pytest.mark.parametrize("method, name, data, ok", WRITES)
def test_a_session_write_without_a_csrf_token_is_refused(
    member, mine, fetches, method, name, data, ok
):
    browser = Client(enforce_csrf_checks=True)
    browser.force_login(member)

    response = send(browser, method, _write_url(name, mine), data)

    assert response.status_code == 403
    assert "CSRF" in response.json()["detail"]
    mine.refresh_from_db()
    assert (mine.notes, mine.rating, mine.status) == ("first", 2, "testing")
    assert SavedAsset.objects.count() == 1
    assert fetches == []


@pytest.mark.parametrize("method, name, data, ok", WRITES)
def test_a_session_write_with_the_csrf_token_succeeds(
    member, mine, fetches, method, name, data, ok
):
    browser = Client(enforce_csrf_checks=True)
    browser.force_login(member)
    browser.get(reverse("accounts:profile"))  # any page sets the csrftoken cookie
    token = browser.cookies["csrftoken"].value

    body = json.dumps(data) if data is not None else ""
    response = getattr(browser, method)(
        _write_url(name, mine),
        data=body,
        content_type="application/json",
        headers={"X-CSRFToken": token},
    )

    assert response.status_code == ok


@pytest.mark.parametrize("method, name, data, ok", WRITES)
def test_the_same_write_signed_with_a_token_needs_no_csrf_token(
    member, mine, fetches, method, name, data, ok
):
    from rest_framework.authtoken.models import Token

    key = Token.objects.create(user=member).key
    script = Client(enforce_csrf_checks=True)

    body = json.dumps(data) if data is not None else ""
    response = getattr(script, method)(
        _write_url(name, mine),
        data=body,
        content_type="application/json",
        headers={"Authorization": f"Token {key}"},
    )

    assert response.status_code == ok


def test_a_token_reads_only_its_own_members_library(member, other_member, mine, make_asset):
    from rest_framework.authtoken.models import Token

    SavedAsset.objects.create(user=other_member, asset=make_asset(external_id="theirs"))
    key = Token.objects.create(user=other_member).key
    script = Client()

    body = script.get(
        reverse("catalog:api_library"), headers={"Authorization": f"Token {key}"}
    ).json()
    mine_response = script.get(entry_url(mine), headers={"Authorization": f"Token {key}"})

    assert [row["asset"]["external_id"] for row in body["results"]] == ["theirs"]
    assert mine_response.status_code == 404
