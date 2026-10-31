"""Access rules for the website, stated explicitly page by page.

Phase 1 rules:
- Signed-out visitors can open Home and Discover.
- Signed-out visitors who open Library, Packs, Profile or Settings are
  redirected to sign-in with `next` set to that page, and come back to it
  after signing in.
- Sign-out accepts only POST; a GET is rejected and leaves the member
  signed in.
- Sign-up, sign-in and sign-out reject POSTs without a CSRF token.
"""

from urllib.parse import quote

import pytest
from django.test import Client
from django.urls import reverse

pytestmark = pytest.mark.django_db

PUBLIC_PAGES = ["packs:home", "catalog:discover"]
MEMBERS_ONLY_PAGES = ["catalog:library", "packs:list", "accounts:profile", "accounts:settings"]


def login_url_for(path):
    return f"{reverse('accounts:login')}?next={quote(path)}"


# ---------------------------------------------------------------- signed out


@pytest.mark.parametrize("name", PUBLIC_PAGES)
def test_anonymous_can_open_public_page(client, name):
    response = client.get(reverse(name))
    assert response.status_code == 200


def test_anonymous_can_open_discover(client):
    response = client.get(reverse("catalog:discover"))
    assert response.status_code == 200
    assert b"Find assets for your next pack." in response.content


@pytest.mark.parametrize("name", MEMBERS_ONLY_PAGES)
def test_anonymous_is_redirected_to_sign_in_from_members_only_page(client, name):
    path = reverse(name)
    response = client.get(path)
    assert response.status_code == 302
    assert response.url == login_url_for(path)


@pytest.mark.parametrize("name", MEMBERS_ONLY_PAGES)
def test_anonymous_never_sees_members_only_content(client, name):
    response = client.get(reverse(name), follow=True)
    assert response.redirect_chain[-1][0].startswith(reverse("accounts:login"))
    assert response.templates[0].name == "registration/login.html"


# ---------------------------------------------------------------- signed in


@pytest.mark.parametrize("name", PUBLIC_PAGES + MEMBERS_ONLY_PAGES)
def test_member_can_open_every_page(member_client, name):
    assert member_client.get(reverse(name)).status_code == 200


@pytest.mark.parametrize("name", MEMBERS_ONLY_PAGES)
def test_sign_in_returns_to_the_members_only_page(client, member, password, name):
    path = reverse(name)
    redirect = client.get(path)
    assert redirect.url == login_url_for(path)

    response = client.post(
        redirect.url, {"username": member.username, "password": password, "next": path}
    )

    assert response.status_code == 302
    assert response.url == path
    assert client.get(path).status_code == 200


def test_sign_in_ignores_an_off_site_next(client, member, password):
    response = client.post(
        reverse("accounts:login"),
        {"username": member.username, "password": password, "next": "https://evil.example/"},
    )
    assert response.status_code == 302
    assert response.url == reverse("packs:home")


# ---------------------------------------------------------------- sign-out


def test_sign_out_rejects_get_and_keeps_member_signed_in(member_client):
    response = member_client.get(reverse("accounts:logout"))
    assert response.status_code == 405
    assert member_client.get(reverse("catalog:library")).status_code == 200


def test_sign_out_works_through_post(member_client):
    response = member_client.post(reverse("accounts:logout"))
    assert response.status_code == 302
    assert response.url == reverse("packs:home")

    library = reverse("catalog:library")
    after = member_client.get(library)
    assert after.status_code == 302
    assert after.url == login_url_for(library)


# ---------------------------------------------------------------- CSRF


@pytest.fixture
def csrf_client():
    return Client(enforce_csrf_checks=True)


def test_sign_up_rejects_post_without_csrf_token(csrf_client, django_user_model):
    response = csrf_client.post(
        reverse("accounts:signup"),
        {"username": "newcomer", "password1": "a-Long-pass-123", "password2": "a-Long-pass-123"},
    )
    assert response.status_code == 403
    assert not django_user_model.objects.filter(username="newcomer").exists()


def test_sign_in_rejects_post_without_csrf_token(csrf_client, member, password):
    response = csrf_client.post(
        reverse("accounts:login"), {"username": member.username, "password": password}
    )
    assert response.status_code == 403
    assert "_auth_user_id" not in csrf_client.session


def test_sign_out_rejects_post_without_csrf_token(csrf_client, member):
    csrf_client.force_login(member)
    response = csrf_client.post(reverse("accounts:logout"))
    assert response.status_code == 403
    assert csrf_client.get(reverse("catalog:library")).status_code == 200


def test_sign_in_succeeds_with_the_forms_csrf_token(csrf_client, member, password):
    csrf_client.get(reverse("accounts:login"))
    token = csrf_client.cookies["csrftoken"].value
    response = csrf_client.post(
        reverse("accounts:login"),
        {"username": member.username, "password": password, "csrfmiddlewaretoken": token},
    )
    assert response.status_code == 302
    assert csrf_client.session["_auth_user_id"] == str(member.pk)
