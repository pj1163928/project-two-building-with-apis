"""The API token page (accounts:token): the member's token, created on the first visit.

Its access rule (signed-out visitors go to sign-in and back) is in
test_access_control.py, with the other members-only pages.
"""

import re

import pytest
from django.test import Client
from django.urls import reverse
from rest_framework.authtoken.models import Token

pytestmark = pytest.mark.django_db


def test_the_first_visit_creates_the_token_and_shows_it(member_client, member):
    assert not Token.objects.filter(user=member).exists()

    response = member_client.get(reverse("accounts:token"))

    assert response.status_code == 200
    token = Token.objects.get(user=member)
    assert f'value="{token.key}"' in response.content.decode()


def test_later_visits_show_the_same_token(member_client, member):
    member_client.get(reverse("accounts:token"))
    first = Token.objects.get(user=member).key

    response = member_client.get(reverse("accounts:token"))

    assert Token.objects.filter(user=member).count() == 1
    assert Token.objects.get(user=member).key == first
    assert first in response.content.decode()


def test_the_page_shows_only_the_members_own_token(member_client, django_user_model, password):
    other = django_user_model.objects.create_user(username="other_member", password=password)
    theirs = Token.objects.create(user=other).key

    response = member_client.get(reverse("accounts:token"))

    assert theirs not in response.content.decode()


def test_the_page_is_never_cached(member_client):
    response = member_client.get(reverse("accounts:token"))

    assert "no-store" in response["Cache-Control"]
    assert "private" in response["Cache-Control"]


def test_the_page_explains_the_header_with_a_working_example(member_client, member):
    html = member_client.get(reverse("accounts:token")).content.decode()
    key = Token.objects.get(user=member).key

    assert f"Authorization: Token {key}" in html
    assert "http://testserver/api/library/" in html
    assert "don&#x27;t need a CSRF token" in html or "don't need a CSRF token" in html


def test_the_token_shown_signs_api_requests(member_client, member, make_asset):
    from catalog.models import SavedAsset

    SavedAsset.objects.create(user=member, asset=make_asset())
    html = member_client.get(reverse("accounts:token")).content.decode()
    key = re.search(r'id="api-token"[^>]*value="([0-9a-f]+)"', html).group(1)

    response = Client().get(
        reverse("catalog:api_library"), headers={"Authorization": f"Token {key}"}
    )

    assert response.status_code == 200
    assert response.json()["count"] == 1


@pytest.mark.parametrize(
    "name, current",
    [
        ("accounts:profile", "Profile"),
        ("accounts:settings", "Settings"),
        ("accounts:token", "API token"),
    ],
)
def test_every_account_page_lists_the_token_page_and_marks_its_own_row(
    member_client, name, current
):
    html = member_client.get(reverse(name)).content.decode()

    assert f'href="{reverse("accounts:token")}"' in html
    assert re.search(
        rf'class="panel-row"[^>]*aria-current="page">(?:(?!</a>).)*>{current}<', html, re.S
    )
    assert len(re.findall(r'class="panel-row"[^>]*aria-current="page"', html)) == 1


def test_the_profile_links_to_the_token_page(member_client):
    html = member_client.get(reverse("accounts:profile")).content.decode()

    assert re.search(
        rf'<a class="link[^"]*" href="{reverse("accounts:token")}">Your API token<', html
    )


# ---------------------------------------------------------------- new token


def api_status(key):
    """The library API's status code for a request signed with `key`."""
    return (
        Client()
        .get(reverse("catalog:api_library"), headers={"Authorization": f"Token {key}"})
        .status_code
    )


def test_the_page_offers_a_new_token_behind_a_confirm(member_client):
    html = member_client.get(reverse("accounts:token")).content.decode()

    assert 'data-dialog-open="token-rotate-dialog"' in html
    assert 'id="token-rotate-dialog"' in html
    assert f'action="{reverse("accounts:rotate_token")}"' in html
    assert 'data-copy="api-token"' in html


def test_a_new_token_replaces_the_old_one(member_client, member):
    old = Token.objects.create(user=member).key

    response = member_client.post(reverse("accounts:rotate_token"))

    assert response.status_code == 302
    assert response.url == reverse("accounts:token")
    new = Token.objects.get(user=member).key
    assert new != old
    assert api_status(old) == 401
    assert api_status(new) == 200


def test_the_token_page_shows_the_new_key_and_says_the_old_one_is_gone(member_client, member):
    Token.objects.create(user=member)

    response = member_client.post(reverse("accounts:rotate_token"), follow=True)

    html = response.content.decode()
    assert f'value="{Token.objects.get(user=member).key}"' in html
    assert "New token made. The old one no longer works" in html
    # The message shows once; the next visit is back to the created date.
    again = member_client.get(reverse("accounts:token")).content.decode()
    assert "New token made" not in again
    assert "Created " in again


def test_a_member_without_a_token_gets_their_first(member_client, member):
    member_client.post(reverse("accounts:rotate_token"))

    assert Token.objects.filter(user=member).count() == 1


def test_a_new_token_leaves_other_members_tokens_alone(
    member_client, member, django_user_model, password
):
    other = django_user_model.objects.create_user(username="other_member", password=password)
    theirs = Token.objects.create(user=other).key
    Token.objects.create(user=member)

    member_client.post(reverse("accounts:rotate_token"))

    assert Token.objects.get(user=other).key == theirs
    assert api_status(theirs) == 200


def test_a_new_token_is_post_only(member_client, member):
    old = Token.objects.create(user=member).key

    assert member_client.get(reverse("accounts:rotate_token")).status_code == 405
    assert Token.objects.get(user=member).key == old


def test_a_new_token_needs_csrf(member):
    old = Token.objects.create(user=member).key
    client = Client(enforce_csrf_checks=True)
    client.force_login(member)

    response = client.post(reverse("accounts:rotate_token"))

    assert response.status_code == 403
    assert Token.objects.get(user=member).key == old


def test_signed_out_a_new_token_goes_to_sign_in(client):
    response = client.post(reverse("accounts:rotate_token"))

    assert response.status_code == 302
    assert response.url.startswith(reverse("accounts:login"))
    assert not Token.objects.exists()
