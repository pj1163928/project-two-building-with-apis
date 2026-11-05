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

Phase 3 rules:
- Saving needs sign-in: a visitor's save is sent to sign-in and back to
  Discover (an HTMX save redirects the whole page back to its search), and
  nothing is saved or fetched.
- Saving needs a valid CSRF token; the header base.html sends is enough.
- The status bar's saved count only ever counts the current member's
  entries. (/library/ itself is in MEMBERS_ONLY_PAGES; the grid's
  own-entries rule is in test_library_page.py.)

Phase 4 rules:
- A signed-out visitor's library URL with a search, filters, sort and page
  is sent to sign-in and back to that same view. The results fragment (an
  HTMX request) redirects the whole window there instead of swapping the
  sign-in page into the results.
- No search, filter, sort or page parameter on the page or its fragment
  shows another member's entries. (filter_library()'s own rule is in
  test_library_filter.py.)

Phase 4 polish rules (Remove, tags):
- Removing an entry needs sign-in: a visitor is sent to sign-in and back to
  the library (an HTMX remove redirects the whole window), and nothing is
  removed.
- Another member's entry, or one that doesn't exist, is a 404, and stays.
- Removing needs a valid CSRF token; the header base.html sends is enough.
- The tag filter and the side panel's tag chips never show another
  member's entries or tags.

Phase 5 rules (the drawer):
- Another member's entry, or one that doesn't exist, is a 404 for viewing
  (the drawer and the full page) and for every update, and nothing changes.
- A signed-out visitor opening an entry is sent to sign-in and back to it
  (the drawer's request redirects the whole window). A signed-out update
  saves nothing: a plain POST goes to sign-in, and an HTMX save gets a 401
  status line with a sign-in link, so the notes being typed stay on the page.
- Every update needs a valid CSRF token; the header base.html sends is
  enough.

Phase 7 rules (packs):
- New pack, the builder and every pack URL send signed-out visitors to
  sign-in (an HTMX request redirects the whole window), back to the builder
  (or the Discover page a picker was on), and change nothing.
- Another member's pack is a 404 for the builder and every edit URL, and
  stays as it was.
- Adding another member's SavedAsset to your pack is a 404 through the
  builder's Add and the picker (add_to_pack()'s own refusal is in
  test_packs.py). Adding your SavedAsset to another member's pack is a 404.
- Removing an entry from the library: the confirm (GET) is a 404 for
  another member's entry too.
- Every pack write needs a valid CSRF token; the header base.html sends is
  enough.

Phase 6 rules:
- The API token page sends signed-out visitors to sign-in and back (it's in
  MEMBERS_ONLY_PAGES). The library API's own rules (401 signed out, 404 for
  another member's entry, session writes need CSRF, token writes don't) are
  in test_api_library.py.
"""

import re
from html import unescape
from urllib.parse import quote

import pytest
from django.test import Client
from django.urls import reverse

pytestmark = pytest.mark.django_db

PUBLIC_PAGES = ["packs:home", "catalog:discover"]
MEMBERS_ONLY_PAGES = [
    "catalog:library",
    "packs:list",
    "packs:create",
    "accounts:profile",
    "accounts:settings",
    "accounts:token",
]


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


# ---------------------------------------------------------------- saving (Phase 3)


@pytest.fixture
def saving_fetches(monkeypatch):
    """Poly Haven's fetch_record, replaced; the list records each call."""
    from providers import AssetRecord, polyhaven

    calls = []

    def fake(external_id):
        calls.append(external_id)
        return AssetRecord(
            provider="polyhaven",
            external_id=external_id,
            kind="texture",
            title="Red Brick 03",
            author="Rob Tuytel",
            thumbnail_url="https://cdn.polyhaven.com/thumbs/red_brick_03.png",
            license="CC0",
            license_url="https://creativecommons.org/publicdomain/zero/1.0/",
            attribution="Red Brick 03 by Rob Tuytel",
            source_url="https://polyhaven.com/a/red_brick_03",
        )

    monkeypatch.setattr(polyhaven, "fetch_record", fake)
    return calls


SAVE_BODY = {"provider": "polyhaven", "external_id": "red_brick_03"}


def test_a_visitors_save_is_sent_to_sign_in_and_back_to_discover(client, saving_fetches):
    from catalog.models import SavedAsset

    response = client.post(reverse("catalog:save"), SAVE_BODY)
    assert response.status_code == 302
    # Back to Discover, never to the POST-only save URL.
    assert response.url == login_url_for(reverse("catalog:discover"))
    assert saving_fetches == [] and not SavedAsset.objects.exists()


def test_a_visitors_htmx_save_redirects_the_whole_page_back_to_its_search(client, saving_fetches):
    from catalog.models import SavedAsset

    headers = {
        "HX-Request": "true",
        "HX-Current-URL": "http://testserver/discover/?type=texture&q=brick",
    }
    response = client.post(reverse("catalog:save"), SAVE_BODY, headers=headers)
    assert response.status_code == 200
    assert response["HX-Redirect"] == login_url_for("/discover/?type=texture&q=brick")
    assert saving_fetches == [] and not SavedAsset.objects.exists()


def test_signing_in_from_save_returns_to_the_discover_search(client, member, password):
    back = "/discover/?type=texture&q=brick"
    response = client.post(login_url_for(back), {"username": member.username, "password": password})
    assert response.status_code == 302
    assert response.url == back


def test_saving_rejects_a_post_without_a_csrf_token(csrf_client, member, saving_fetches):
    from catalog.models import SavedAsset

    csrf_client.force_login(member)
    response = csrf_client.post(reverse("catalog:save"), SAVE_BODY, headers={"HX-Request": "true"})
    assert response.status_code == 403
    assert saving_fetches == [] and not SavedAsset.objects.exists()


def test_saving_succeeds_with_the_pages_csrf_header(csrf_client, member, saving_fetches):
    """The header base.html sends on every HTMX request is enough."""
    from catalog.models import SavedAsset

    csrf_client.force_login(member)
    page = csrf_client.get(reverse("catalog:discover")).content.decode()
    token = re.search(r"hx-headers='\{\"X-CSRFToken\": \"([^\"]+)\"\}'", page).group(1)
    response = csrf_client.post(
        reverse("catalog:save"), SAVE_BODY, headers={"HX-Request": "true", "X-CSRFToken": token}
    )
    assert response.status_code == 200
    assert SavedAsset.objects.filter(user=member).count() == 1


def test_the_saved_count_counts_only_the_current_members_entries(
    member_client, member, make_asset, django_user_model, password
):
    from catalog.models import SavedAsset

    other = django_user_model.objects.create_user("other_member", password=password)
    assets = [make_asset(external_id=f"asset_{n}") for n in range(5)]
    for asset in assets[:2]:
        SavedAsset.objects.create(user=member, asset=asset)
    for asset in assets:
        SavedAsset.objects.create(user=other, asset=asset)

    def count(client):
        bar = (
            client.get(reverse("catalog:discover")).content.decode().split('id="status-bar"', 1)[1]
        )
        return re.search(r'id="saved-count"[^>]*>Library · <b[^>]*>(\d+)</b> saved', bar).group(1)

    assert count(member_client) == "2"
    theirs = Client()
    theirs.force_login(other)
    assert count(theirs) == "5"
    # A visitor's bar holds no count at all.
    assert 'id="saved-count"' not in Client().get(reverse("catalog:discover")).content.decode()


# ---------------------------------------------------------------- library browsing (Phase 4)

LIBRARY_VIEW = "/library/?q=brick&type=texture&status=approved&sort=rating&page=2"


def test_a_visitors_library_view_is_sent_to_sign_in_and_back_to_it(client, member, password):
    response = client.get(LIBRARY_VIEW)
    assert response.status_code == 302
    assert response.url == login_url_for(LIBRARY_VIEW)
    signed_in = client.post(response.url, {"username": member.username, "password": password})
    assert signed_in.url == LIBRARY_VIEW


def test_a_visitors_results_fragment_redirects_the_whole_window_to_sign_in(client):
    response = client.get(LIBRARY_VIEW, headers={"HX-Request": "true"})
    assert response.status_code == 200
    assert response["HX-Redirect"] == login_url_for(LIBRARY_VIEW)
    assert 'id="library-results"' not in response.content.decode()


@pytest.mark.parametrize("headers", [{}, {"HX-Request": "true", "HX-Boosted": "true"}])
def test_a_visitors_boosted_library_request_is_an_ordinary_redirect(client, headers):
    response = client.get(LIBRARY_VIEW, headers=headers)
    assert response.status_code == 302
    assert response.url == login_url_for(LIBRARY_VIEW)


@pytest.mark.parametrize("htmx", [False, True])
def test_library_parameters_never_show_another_members_entries(
    member_client, member, make_asset, django_user_model, password, htmx
):
    from catalog.models import SavedAsset

    other = django_user_model.objects.create_user("other_member", password=password)
    SavedAsset.objects.create(user=member, asset=make_asset(external_id="mine", title="Mine Brick"))
    their_asset = make_asset(external_id="theirs", title="Their Secret Brick")
    SavedAsset.objects.create(
        user=other, asset=their_asset, notes="secret note", rating=5, status="approved"
    )
    headers = {"HX-Request": "true"} if htmx else {}
    for query in (
        "",
        "?q=secret",
        "?q=brick&status=approved&min_rating=5",
        f"?user={other.pk}&owner={other.username}",
        "?sort=rating&page=2",
    ):
        html = member_client.get(reverse("catalog:library") + query, headers=headers)
        html = html.content.decode()
        assert "Their Secret Brick" not in html and "secret note" not in html, query


# ---------------------------------------------------------------- Remove and tags (Phase 4 polish)


@pytest.fixture
def mine(member, make_asset):
    from catalog.models import SavedAsset

    return SavedAsset.objects.create(user=member, asset=make_asset(external_id="mine"))


def test_a_visitors_remove_is_sent_to_sign_in_and_back_to_the_library(client, mine):
    from catalog.models import SavedAsset

    url = reverse("catalog:remove", args=[mine.pk])
    response = client.post(url)
    assert response.status_code == 302
    assert response.url == login_url_for(reverse("catalog:library"))
    htmx = client.post(url, headers={"HX-Request": "true"})
    assert htmx["HX-Redirect"] == login_url_for(reverse("catalog:library"))
    assert SavedAsset.objects.filter(pk=mine.pk).exists()


def test_removing_another_members_entry_is_a_404_and_it_stays(
    member_client, make_asset, django_user_model, password
):
    from catalog.models import SavedAsset

    other = django_user_model.objects.create_user("other_member", password=password)
    theirs = SavedAsset.objects.create(user=other, asset=make_asset(external_id="theirs"))
    for headers in ({}, {"HX-Request": "true"}):
        response = member_client.post(reverse("catalog:remove", args=[theirs.pk]), headers=headers)
        assert response.status_code == 404
    assert SavedAsset.objects.filter(pk=theirs.pk).exists()
    assert member_client.post(reverse("catalog:remove", args=[99999])).status_code == 404


def test_removing_rejects_a_post_without_a_csrf_token(csrf_client, member, mine):
    from catalog.models import SavedAsset

    csrf_client.force_login(member)
    url = reverse("catalog:remove", args=[mine.pk])
    assert csrf_client.post(url, headers={"HX-Request": "true"}).status_code == 403
    assert SavedAsset.objects.filter(pk=mine.pk).exists()


def test_removing_succeeds_with_the_pages_csrf_header(csrf_client, member, mine):
    from catalog.models import SavedAsset

    csrf_client.force_login(member)
    page = csrf_client.get(reverse("catalog:library")).content.decode()
    token = re.search(r"hx-headers='\{\"X-CSRFToken\": \"([^\"]+)\"\}'", page).group(1)
    response = csrf_client.post(
        reverse("catalog:remove", args=[mine.pk]),
        headers={"HX-Request": "true", "X-CSRFToken": token},
    )
    assert response.status_code == 200
    assert not SavedAsset.objects.filter(pk=mine.pk).exists()


def test_tags_never_show_another_members_entries_or_tags(
    member_client, mine, make_asset, django_user_model, password
):
    from catalog.models import SavedAsset, Tag

    mine.asset.tags.set(Tag.objects.from_names(["brick"]))
    other = django_user_model.objects.create_user("other_member", password=password)
    theirs = make_asset(external_id="theirs", title="Their Secret Brick")
    theirs.tags.set(Tag.objects.from_names(["brick", "classified"]))
    SavedAsset.objects.create(user=other, asset=theirs)
    for query in ("?tag=brick", "?tag=classified", "?tag=brick&tag=classified"):
        html = member_client.get(reverse("catalog:library") + query).content.decode()
        assert "Their Secret Brick" not in html, query
        assert 'value="classified"' not in html.split('id="library-filters"', 1)[1], query


# ---------------------------------------------------------------- the drawer (Phase 5)


@pytest.fixture
def theirs(make_asset, django_user_model, password):
    """Another member's entry, with private notes, a rating and a status."""
    from catalog.models import SavedAsset

    other = django_user_model.objects.create_user("other_member", password=password)
    return SavedAsset.objects.create(
        user=other,
        asset=make_asset(external_id="theirs", title="Their Secret Brick"),
        notes="their secret note",
        rating=2,
        status=SavedAsset.Status.REJECTED,
    )


def test_another_members_entry_is_a_404_to_view_and_to_update(member_client, theirs):
    from catalog.models import SavedAsset

    view = reverse("catalog:entry", args=[theirs.pk])
    update = reverse("catalog:update", args=[theirs.pk])
    for headers in ({}, {"HX-Request": "true"}):
        response = member_client.get(view, headers=headers)
        assert response.status_code == 404
        assert "their secret note" not in response.content.decode()
        for data in ({"notes": "mine now"}, {"rating": "5"}, {"status": "approved"}):
            assert member_client.post(update, data, headers=headers).status_code == 404
    theirs.refresh_from_db()
    assert (theirs.notes, theirs.rating, theirs.status) == (
        "their secret note",
        2,
        SavedAsset.Status.REJECTED,
    )
    # An entry that doesn't exist is the same 404.
    assert member_client.get(reverse("catalog:entry", args=[99999])).status_code == 404
    assert member_client.post(reverse("catalog:update", args=[99999])).status_code == 404


def test_a_visitor_opening_an_entry_is_sent_to_sign_in_and_back(client, member, password, mine):
    url = reverse("catalog:entry", args=[mine.pk])
    response = client.get(url)
    assert response.status_code == 302 and response.url == login_url_for(url)
    # The drawer's request redirects the whole window, not into the drawer.
    htmx = client.get(url, headers={"HX-Request": "true"})
    assert htmx["HX-Redirect"] == login_url_for(url)
    signed_in = client.post(response.url, {"username": member.username, "password": password})
    assert signed_in.url == url


def test_a_visitors_update_saves_nothing_and_keeps_the_text_on_the_page(client, mine):
    url = reverse("catalog:update", args=[mine.pk])
    entry_url = reverse("catalog:entry", args=[mine.pk])
    plain = client.post(url, {"notes": "typed while signed out"})
    assert plain.status_code == 302 and plain.url == login_url_for(entry_url)
    # An HTMX save gets a 401 status line, not a redirect that would lose the notes.
    htmx = client.post(url, {"notes": "typed while signed out"}, headers={"HX-Request": "true"})
    html = unescape(htmx.content.decode())
    assert htmx.status_code == 401 and "HX-Redirect" not in htmx
    assert "You're signed out, so this didn't save. Your text is still here." in html
    assert f'href="{login_url_for(entry_url)}" target="_blank" rel="noopener"' in html
    assert "data-save-retry" in html
    mine.refresh_from_db()
    assert mine.notes == ""


def test_updating_rejects_a_post_without_a_csrf_token(csrf_client, member, mine):
    csrf_client.force_login(member)
    url = reverse("catalog:update", args=[mine.pk])
    for data in ({"notes": "no token"}, {"rating": "5"}, {"status": "approved"}):
        assert csrf_client.post(url, data, headers={"HX-Request": "true"}).status_code == 403
    mine.refresh_from_db()
    assert (mine.notes, mine.rating, mine.status) == ("", None, "to_review")


def test_updating_succeeds_with_the_pages_csrf_header(csrf_client, member, mine):
    csrf_client.force_login(member)
    page = csrf_client.get(reverse("catalog:entry", args=[mine.pk])).content.decode()
    token = re.search(r"hx-headers='\{\"X-CSRFToken\": \"([^\"]+)\"\}'", page).group(1)
    response = csrf_client.post(
        reverse("catalog:update", args=[mine.pk]),
        {"rating": "5"},
        headers={"HX-Request": "true", "X-CSRFToken": token},
    )
    assert response.status_code == 200
    mine.refresh_from_db()
    assert mine.rating == 5


# ---------------------------------------------------------------- packs (Phase 7)


@pytest.fixture
def my_pack(member, mine):
    from packs.models import Pack
    from packs.services import add_to_pack

    pack = Pack.objects.create_pack(member, "My Pack")
    add_to_pack(pack, mine)
    return pack


@pytest.fixture
def their_pack(theirs):
    from packs.models import Pack
    from packs.services import add_to_pack

    pack = Pack.objects.create_pack(theirs.user, "Their Pack", tags="secret")
    add_to_pack(pack, theirs)
    return pack


def _pack_gets(pack):
    """Every GET on one pack: the builder and Add from my library."""
    return [
        reverse("packs:builder", args=[pack.pk]),
        reverse("packs:library_search", args=[pack.pk]),
    ]


def _pack_writes(pack, entry):
    """Every POST that changes one pack, with data that would succeed for its owner."""
    item = pack.items.get()
    return [
        (reverse("packs:details", args=[pack.pk]), {"title": "Changed"}),
        (reverse("packs:visibility", args=[pack.pk]), {"visibility": "public"}),
        (reverse("packs:add_item", args=[pack.pk]), {"entry": entry.pk}),
        (reverse("packs:item_update", args=[pack.pk, item.pk]), {"import_path": "changed/"}),
        (reverse("packs:item_move", args=[pack.pk, item.pk]), {"direction": "down"}),
        (reverse("packs:item_remove", args=[pack.pk, item.pk]), {}),
        (reverse("packs:picker_add", args=[pack.pk]), {"entry": entry.pk}),
        (reverse("packs:delete", args=[pack.pk]), {}),
    ]


def _pack_state(pack):
    from packs.models import Pack

    pack = Pack.objects.filter(pk=pack.pk).first()
    if pack is None:
        return None
    items = list(pack.items.values_list("saved_asset", "import_path", "position"))
    return (pack.title, pack.is_public, items)


def test_a_visitor_is_sent_to_sign_in_from_every_pack_url_and_nothing_changes(
    client, my_pack, mine
):
    builder = reverse("packs:builder", args=[my_pack.pk])
    before = _pack_state(my_pack)
    for url in _pack_gets(my_pack):
        assert client.get(url).url == login_url_for(builder)
    for url, data in _pack_writes(my_pack, mine):
        response = client.post(url, data)
        assert response.status_code == 302 and response.url.startswith(reverse("accounts:login"))
        htmx = client.post(url, data, headers={"HX-Request": "true"})
        assert htmx["HX-Redirect"].startswith(reverse("accounts:login"))
    assert _pack_state(my_pack) == before


def test_a_visitors_builder_returns_to_it_after_sign_in(client, member, password, my_pack):
    builder = reverse("packs:builder", args=[my_pack.pk])
    response = client.post(
        login_url_for(builder), {"username": member.username, "password": password}
    )
    assert response.url == builder


def test_a_visitors_picker_goes_to_sign_in_and_back_to_the_page_it_was_on(client, mine):
    discover = "/discover/?type=texture&q=brick"
    response = client.get(
        reverse("packs:picker"),
        {"entry": mine.pk},
        headers={"HX-Request": "true", "HX-Current-URL": f"http://testserver{discover}"},
    )
    assert response["HX-Redirect"] == login_url_for(discover)


def test_another_members_pack_is_a_404_everywhere_and_stays(
    member_client, their_pack, theirs, mine
):
    before = _pack_state(their_pack)
    for url in _pack_gets(their_pack):
        assert member_client.get(url, headers={"HX-Request": "true"}).status_code == 404
    # Even with the member's own entry, so the entry check isn't what refuses it.
    for url, data in _pack_writes(their_pack, mine):
        assert member_client.post(url, data, headers={"HX-Request": "true"}).status_code == 404
    assert _pack_state(their_pack) == before
    html = member_client.get(reverse("packs:list")).content.decode()
    assert "Their Pack" not in html


def test_adding_another_members_entry_to_your_pack_is_a_404(member_client, my_pack, theirs):
    before = _pack_state(my_pack)
    for url in (
        reverse("packs:add_item", args=[my_pack.pk]),
        reverse("packs:picker_add", args=[my_pack.pk]),
    ):
        response = member_client.post(url, {"entry": theirs.pk}, headers={"HX-Request": "true"})
        assert response.status_code == 404
    picker = member_client.get(reverse("packs:picker"), {"entry": theirs.pk})
    assert picker.status_code == 404
    assert _pack_state(my_pack) == before


def test_the_remove_confirm_is_a_404_for_another_members_entry(member_client, theirs, their_pack):
    response = member_client.get(
        reverse("catalog:remove", args=[theirs.pk]), headers={"HX-Request": "true"}
    )
    assert response.status_code == 404
    assert "Their Pack" not in response.content.decode()


def test_every_pack_write_rejects_a_post_without_a_csrf_token(csrf_client, member, my_pack, mine):
    csrf_client.force_login(member)
    before = _pack_state(my_pack)
    for url, data in _pack_writes(my_pack, mine):
        assert csrf_client.post(url, data, headers={"HX-Request": "true"}).status_code == 403
    assert csrf_client.post(reverse("packs:create"), {"title": "New"}).status_code == 403
    assert _pack_state(my_pack) == before


def test_pack_writes_succeed_with_the_pages_csrf_header(csrf_client, member, my_pack, mine):
    from packs.models import Pack

    csrf_client.force_login(member)
    page = csrf_client.get(reverse("packs:builder", args=[my_pack.pk])).content.decode()
    token = re.search(r"hx-headers='\{\"X-CSRFToken\": \"([^\"]+)\"\}'", page).group(1)
    headers = {"HX-Request": "true", "X-CSRFToken": token}
    for url, data in _pack_writes(my_pack, mine):
        assert csrf_client.post(url, data, headers=headers).status_code in (200, 302)
    assert not Pack.objects.filter(pk=my_pack.pk).exists()
