"""Sign-up and sign-in flows (access rules live in test_access_control.py)."""

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db

NEW_PASSWORD = "a-Long-pass-123"


def sign_up(client, username="newcomer", password1=NEW_PASSWORD, password2=NEW_PASSWORD, **extra):
    data = {"username": username, "password1": password1, "password2": password2, **extra}
    return client.post(reverse("accounts:signup"), data)


def test_sign_up_creates_account_and_signs_in(client, django_user_model):
    response = sign_up(client)

    user = django_user_model.objects.get(username="newcomer")
    assert response.status_code == 302
    assert response.url == reverse("packs:home")
    assert client.session["_auth_user_id"] == str(user.pk)
    assert b"newcomer" in client.get(reverse("packs:home")).content


def test_sign_up_honours_next(client):
    response = sign_up(client, next=reverse("catalog:library"))
    assert response.url == reverse("catalog:library")


def test_sign_up_ignores_an_off_site_next(client):
    response = sign_up(client, next="https://evil.example/")
    assert response.url == reverse("packs:home")


def test_sign_up_page_carries_next_into_the_form(client):
    response = client.get(reverse("accounts:signup"), {"next": "/library/"})
    assert b'name="next" value="/library/"' in response.content


def test_sign_up_with_mismatched_passwords_shows_error(client, django_user_model):
    response = sign_up(client, password2="something-else-456")
    assert response.status_code == 200
    assert b"The two password fields" in response.content
    assert not django_user_model.objects.filter(username="newcomer").exists()
    assert "_auth_user_id" not in client.session


def test_sign_up_with_taken_username_shows_error(client, member):
    response = sign_up(client, username=member.username)
    assert response.status_code == 200
    assert b"A user with that username already exists." in response.content


def test_signed_in_member_visiting_sign_up_is_sent_home(member_client):
    response = member_client.get(reverse("accounts:signup"))
    assert response.status_code == 302
    assert response.url == reverse("packs:home")


def test_sign_in_with_wrong_password_shows_error(client, member):
    response = client.post(
        reverse("accounts:login"), {"username": member.username, "password": "wrong"}
    )
    assert response.status_code == 200
    assert b"Please enter a correct username and password." in response.content
    assert "_auth_user_id" not in client.session


def test_sign_in_without_next_goes_home(client, member, password):
    response = client.post(
        reverse("accounts:login"), {"username": member.username, "password": password}
    )
    assert response.url == reverse("packs:home")


def test_profile_shows_the_members_details(member_client, member):
    response = member_client.get(reverse("accounts:profile"))
    assert member.username.encode() in response.content
    assert b"Member since" in response.content
