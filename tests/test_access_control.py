"""Access rules for the website, stated explicitly page by page.

Phase 1 rules:
- Signed-out visitors can open Home and Discover.

Phase 2a rules:
- Signed-out visitors can search Discover and load its shelf fragments; a
  shelf opened directly goes to its Discover page, never to sign-in.
- Signed-out visitors who open Library, Packs, Profile or Settings are
  redirected to sign-in with `next` set to that page, and come back to it
  after signing in.
- Sign-out accepts only POST; a GET is rejected and leaves the member
  signed in.
- Sign-up, sign-in and sign-out reject POSTs without a CSRF token.

Phase 2b rules:
- Discover and its shelves stay open to signed-out visitors, and the status
  bar shows them provider status only, never member data.
"""

import re
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


@pytest.mark.parametrize(("kind", "provider"), [("texture", "ambientcg"), ("sound", "openverse")])
def test_anonymous_can_search_discover_and_load_its_shelves(client, monkeypatch, kind, provider):
    from providers import PROVIDERS_BY_KEY, AssetRecord

    found = AssetRecord(
        provider=provider,
        external_id="item_01",
        kind=kind,
        title="Visible To Visitors",
        author="Someone",
        thumbnail_url="https://cdn.example/item_01.png",
        license="CC0",
        license_url="https://creativecommons.org/publicdomain/zero/1.0/",
        attribution="Visible To Visitors by Someone",
        source_url="https://example.com/item_01",
    )
    monkeypatch.setattr(
        PROVIDERS_BY_KEY[provider], "search_records", lambda query, kind, limit=12, page=1: [found]
    )
    page = client.get(reverse("catalog:discover"), {"type": kind, "q": "brick"})
    assert page.status_code == 200
    shelf = client.get(
        reverse("catalog:discover_shelf", args=[kind, provider]) + "?q=brick",
        headers={"HX-Request": "true"},
    )
    assert shelf.status_code == 200
    assert b"Visible To Visitors" in shelf.content
    # Opened directly, a shelf goes to its Discover page, not to sign-in.
    direct = client.get(reverse("catalog:discover_shelf", args=[kind, provider]) + "?q=brick")
    assert direct.status_code == 302
    assert direct.url == f"/discover/?type={kind}&q=brick"


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


# ---------------------------------------------------------------- status bar (Phase 2b)


def test_the_status_bar_shows_visitors_provider_status_and_no_member_data(
    client, member_client, member, monkeypatch
):
    from providers import polyhaven

    monkeypatch.setattr(polyhaven, "search_records", lambda query, kind, limit=12, page=1: [])
    # A member's shelf sets Poly Haven's status, which is shared by everyone...
    member_client.get(
        reverse("catalog:discover_shelf", args=["texture", "polyhaven"]) + "?q=brick",
        headers={"HX-Request": "true"},
    )
    visitor = Client()
    page = visitor.get(reverse("catalog:discover"))
    assert page.status_code == 200
    footer = page.content.decode().split('id="status-bar"', 1)[1]
    bar = footer.split(">", 1)[1].split("</footer>", 1)[0]
    assert 'id="status-polyhaven" data-status="ok"' in bar
    # ...but the visitor's bar holds the Toolbox label and the providers, nothing else.
    text = " ".join(re.sub(r"<[^>]+>", " ", bar).split())
    assert text == (
        "Toolbox ambientCG : status unknown Poly Haven : OK Openverse Audio : status unknown"
    )
    assert member.username not in bar and "saved" not in bar
