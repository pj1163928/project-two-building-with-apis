"""The library drawer: one entry at /library/<id>/, and saving its review.

An HTMX request (a card's title) gets the drawer's fragment; any other
request gets the same entry as a full page. Status, rating and notes post to
catalog:update, which saves only the fields posted, so two quick changes
never overwrite each other. A status or rating change from the library also
sends the card behind the drawer out of band. Access rules are in
test_access_control.py.
"""

import re

import pytest
from django.urls import reverse

from providers import PROVIDERS, ProviderError

pytestmark = pytest.mark.django_db

HTMX = {"HX-Request": "true"}


@pytest.fixture
def entry(member, make_asset):
    from catalog.models import SavedAsset, Tag

    asset = make_asset(
        variants=[
            {
                "label": "2K JPG",
                "files": [
                    {
                        "url": "https://dl.polyhaven.org/red_brick_03_diff_2k.jpg",
                        "filename": "red_brick_03_diff_2k.jpg",
                        "size": 2_500_000,
                    },
                    {
                        "url": "https://dl.polyhaven.org/red_brick_03_nor_gl_2k.jpg",
                        "filename": "red_brick_03_nor_gl_2k.jpg",
                        "size": 3_000_000,
                    },
                ],
                "total_size": 5_500_000,
            },
            {
                "label": "glTF",
                "files": [
                    {
                        "url": "https://dl.polyhaven.org/red_brick_03.gltf",
                        "filename": "red_brick_03.gltf",
                        "size": None,
                    }
                ],
                "total_size": None,
            },
        ]
    )
    asset.tags.set(Tag.objects.from_names(["brick", "wall"]))
    return SavedAsset.objects.create(
        user=member,
        asset=asset,
        notes="Tiles well at 2 m.",
        rating=4,
        status=SavedAsset.Status.TESTING,
    )


def _update(client, entry, data, current="http://testserver/library/"):
    headers = {**HTMX, "HX-Current-URL": current}
    return client.post(reverse("catalog:update", args=[entry.pk]), data, headers=headers)


# ---------------------------------------------------------------- saving the review (TDD 1)


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({"notes": "Seams show up close."}, ("Seams show up close.", 4, "testing")),
        ({"rating": "2"}, ("Tiles well at 2 m.", 2, "testing")),
        ({"status": "approved"}, ("Tiles well at 2 m.", 4, "approved")),
    ],
)
def test_an_update_changes_only_the_field_it_posts(entry, member_client, data, expected):
    response = _update(member_client, entry, data)
    assert response.status_code == 200
    entry.refresh_from_db()
    assert (entry.notes, entry.rating, entry.status) == expected


# ---------------------------------------------------------------- the rating (TDD 2)


@pytest.mark.parametrize(("posted", "stored"), [("1", 1), ("5", 5), ("", None)])
def test_a_rating_from_1_to_5_saves_and_an_empty_one_clears_it(
    entry, member_client, posted, stored
):
    response = _update(member_client, entry, {"rating": posted})
    assert response.status_code == 200
    entry.refresh_from_db()
    assert entry.rating == stored


@pytest.mark.parametrize("posted", ["0", "6", "-1", "4.5", "abc", "99999999999"])
def test_a_rating_outside_1_to_5_is_a_400_and_nothing_changes(entry, member_client, posted):
    response = _update(member_client, entry, {"rating": posted, "notes": "Changed too."})
    assert response.status_code == 400
    assert "Choose a rating from 1 to 5." in response.content.decode()
    entry.refresh_from_db()
    assert (entry.rating, entry.notes) == (4, "Tiles well at 2 m.")


def test_bad_status_long_notes_or_nothing_at_all_is_a_400_and_nothing_changes(entry, member_client):
    from catalog.forms import NOTES_MAX_LENGTH

    for data, message in (
        ({"status": "loved"}, "Choose one of the four statuses."),
        ({"notes": "x" * (NOTES_MAX_LENGTH + 1)}, "Notes can be up to 10,000 characters."),
        ({}, "There was nothing to save."),
        ({"title": "Renamed", "user": "1"}, "There was nothing to save."),
    ):
        response = _update(member_client, entry, data)
        assert response.status_code == 400, data
        html = response.content.decode()
        assert 'data-save-status="error" role="alert"' in html and message in html
        assert "data-save-retry" in html
    entry.refresh_from_db()
    assert (entry.notes, entry.rating, entry.status) == ("Tiles well at 2 m.", 4, "testing")
    assert entry.asset.title == "Red Brick 03"


# ---------------------------------------------------------------- the drawer and the page


def _fragment(client, entry, **headers):
    return client.get(reverse("catalog:entry", args=[entry.pk]), headers={**HTMX, **headers})


def test_an_htmx_request_returns_the_drawer_and_a_direct_visit_the_full_page(entry, member_client):
    drawer = _fragment(member_client, entry)
    html = drawer.content.decode()
    assert drawer.status_code == 200
    assert html.strip().startswith('<div class="drawer-panel">')
    assert "<html" not in html and 'id="side-panel"' not in html
    assert '<h2 id="entry-title" class="entry-title">Red Brick 03</h2>' in html
    url = reverse("catalog:entry", args=[entry.pk])
    assert f'href="{url}" class="picker-close" aria-label="Open as a page"' in html
    assert "data-drawer-close" in html

    page = member_client.get(url)
    html = page.content.decode()
    assert page.status_code == 200
    assert 'id="side-panel"' in html and 'class="drawer-panel"' not in html
    assert '<h1 id="entry-title" class="entry-title">Red Brick 03</h1>' in html
    assert "<title>Red Brick 03 · Library · Axcenity Toolbox</title>" in html
    assert 'aria-label="Library" class="act' in html and 'aria-current="page"' in html


@pytest.mark.parametrize(
    "headers", [{"HX-Boosted": "true"}, {"HX-History-Restore-Request": "true"}]
)
def test_boosted_and_history_restore_requests_get_the_full_page(entry, member_client, headers):
    html = _fragment(member_client, entry, **headers).content.decode()
    assert 'id="side-panel"' in html and '<h1 id="entry-title"' in html


def test_the_drawer_shows_the_assets_details_license_source_and_files(entry, member_client):
    html = _fragment(member_client, entry).content.decode()
    text = " ".join(re.sub(r"<[^>]+>", " ", html).split())
    assert "Texture · Poly Haven" in text and "By Rob Tuytel" in text
    assert (
        '<a href="https://creativecommons.org/publicdomain/zero/1.0/" target="_blank" '
        'rel="noopener noreferrer" class="entry-link">CC0</a>'
    ) in html
    assert "&quot;Red Brick 03&quot; by Rob Tuytel, from Poly Haven, CC0 1.0" in html
    assert 'href="https://polyhaven.com/a/red_brick_03"' in html and "View on Poly Haven" in text
    assert "Tags brick, wall" in text
    # Each variant, told apart by resolution, format and package, with its file count
    # and size, opening to its files, each labelled with the map it holds.
    assert "2K JPG Loose maps Your default 2 files · 5.2 MB" in text
    assert "glTF Bundle 1 file" in text and "glTF Bundle 1 file ·" not in text
    assert 'href="https://dl.polyhaven.org/red_brick_03_diff_2k.jpg"' in html
    assert "Color red_brick_03_diff_2k.jpg 2.4 MB" in text
    assert "Normal GL red_brick_03_nor_gl_2k.jpg 2.9 MB" in text
    assert "Scene red_brick_03.gltf" in text
    # Thumbnail: the provider's URL over the type icon, never the logo.
    thumb = html.split('<div class="entry-thumb">', 1)[1].split("</div>", 1)[0]
    assert 'src="https://cdn.polyhaven.com/thumbs/red_brick_03.png"' in thumb
    assert 'referrerpolicy="no-referrer"' in thumb and "mark" not in thumb
    # The packs it's in (none yet), after "License and credit".
    assert text.index("License and credit") < text.index("Your packs") < text.index("Files")
    assert "It isn't in any of your packs yet." in text
    # And Remove, through the same URL as a card's: it opens the library's Remove dialog.
    remove = reverse("catalog:remove", args=[entry.pk])
    assert f'hx-get="{remove}" hx-target="#remove-dialog"' in html
    assert "hx-confirm" not in html


def test_an_asset_with_no_files_says_so(member, make_asset, member_client):
    from catalog.models import SavedAsset

    bare = SavedAsset.objects.create(user=member, asset=make_asset(external_id="bare"))
    html = _fragment(member_client, bare).content.decode()
    assert "Poly Haven listed no downloadable files for this asset." in html


def test_the_review_shows_the_stored_status_rating_and_notes(entry, member_client):
    html = _fragment(member_client, entry).content.decode()
    assert re.findall(r'name="status" value="(\w+)" checked', html) == ["testing"]
    assert re.findall(r'name="rating" value="(\d*)" checked', html) == ["4"]
    assert ">Tiles well at 2 m.</textarea>" in html
    assert "Changes save as you make them." in html


def test_each_control_posts_only_its_own_field_with_no_save_button(entry, member_client):
    html = _fragment(member_client, entry).content.decode()
    update = reverse("catalog:update", args=[entry.pk])
    forms = re.findall(r'<form class="entry-form".*?</form>', html, re.S)
    assert len(forms) == 3
    for form, field in zip(forms, ("status", "rating", "notes"), strict=True):
        assert f'hx-post="{update}"' in form and 'hx-target="#entry-save-status"' in form
        # A save swaps only the status line, outside the page transition, which would
        # otherwise fade the whole content area behind the drawer on every save.
        assert 'hx-swap="outerHTML transition:false"' in form
        names = set(re.findall(r'name="(\w+)"', form)) - {"csrfmiddlewaretoken"}
        assert names == {field}
        assert 'type="submit"' not in form
    status, rating, notes = forms
    assert 'hx-trigger="change"' in status and 'hx-trigger="change"' in rating
    # Notes: after a pause in typing, and when the box is left; queued, never dropped.
    assert 'hx-trigger="input changed delay:700ms, change"' in notes
    assert 'hx-sync="this:queue last"' in notes
    assert f'data-draft-key="ax-notes-{entry.pk}"' in notes
    assert 'maxlength="10000"' in notes


def test_the_drawer_renders_from_local_data_with_every_provider_down(
    entry, member_client, monkeypatch
):
    def down(*args, **kwargs):
        raise ProviderError("Every provider is down.")

    for provider in PROVIDERS:
        for name in ("search", "get_details", "search_records", "fetch_record"):
            monkeypatch.setattr(provider, name, down)
    for response in (
        _fragment(member_client, entry),
        member_client.get(reverse("catalog:entry", args=[entry.pk])),
    ):
        assert response.status_code == 200
        html = response.content.decode()
        assert "Red Brick 03" in html and "red_brick_03_diff_2k.jpg" in html
        assert "Every provider is down." not in html


def test_the_library_holds_one_drawer_and_each_title_opens_it(entry, member_client):
    html = member_client.get(reverse("catalog:library")).content.decode()
    assert html.count('<dialog id="library-drawer" class="drawer-dialog"') == 1
    url = reverse("catalog:entry", args=[entry.pk])
    # Outside the page transition: run through it, the content behind faded out and
    # back in as the drawer opened, so the drawer seemed to flicker.
    assert (
        f'hx-get="{url}" hx-target="#library-drawer" hx-swap="innerHTML transition:false"' in html
    )


# ---------------------------------------------------------------- saving and the card behind


def _card(html, entry):
    match = re.search(
        rf'<li class="result-card library-card" id="entry-{entry.pk}"[^>]*>.*?</li>', html, re.S
    )
    return match.group(0) if match else ""


def test_a_status_change_updates_the_card_behind_the_drawer(entry, member_client):
    response = _update(member_client, entry, {"status": "approved"})
    html = response.content.decode()
    assert '<p id="entry-save-status" class="entry-save-status" data-save-status="saved"' in html
    assert "Saved" in html
    card = _card(html, entry)
    assert 'hx-swap-oob="true"' in card
    assert 'data-status="approved">Approved</span>' in card


def test_setting_or_clearing_the_rating_updates_the_card(entry, member_client):
    card = _card(_update(member_client, entry, {"rating": "5"}).content.decode(), entry)
    assert 'aria-label="Rated 5 out of 5"' in card and card.count('class="star is-on"') == 5
    card = _card(_update(member_client, entry, {"rating": ""}).content.decode(), entry)
    assert "Not rated" in card and "star-rating" not in card


def test_notes_and_saves_from_the_full_page_send_no_card(entry, member_client):
    assert _card(_update(member_client, entry, {"notes": "New"}).content.decode(), entry) == ""
    page = f"http://testserver{reverse('catalog:entry', args=[entry.pk])}"
    html = _update(member_client, entry, {"status": "approved"}, current=page).content.decode()
    assert _card(html, entry) == "" and "Saved" in html


def test_saved_notes_survive_a_reload_exactly_as_typed(entry, member_client):
    typed = "  Use on the north wall.\n\nSeams show at 4 m.  "
    assert _update(member_client, entry, {"notes": typed}).status_code == 200
    html = member_client.get(reverse("catalog:entry", args=[entry.pk])).content.decode()
    assert f">{typed}</textarea>" in html
    entry.refresh_from_db()
    assert entry.notes == typed


def test_a_plain_update_returns_to_the_entrys_page(entry, member_client):
    response = member_client.post(
        reverse("catalog:update", args=[entry.pk]), {"status": "approved"}
    )
    assert response.status_code == 302
    assert response.url == reverse("catalog:entry", args=[entry.pk])
    entry.refresh_from_db()
    assert entry.status == "approved"


def test_the_update_url_is_post_only(entry, member_client):
    assert member_client.get(reverse("catalog:update", args=[entry.pk])).status_code == 405


# ---------------------------------------------------------------- Remove from the drawer or the page


def test_remove_from_the_drawer_refreshes_the_library_behind_it(entry, member_client):
    from catalog.models import Asset, SavedAsset

    response = member_client.post(
        reverse("catalog:remove", args=[entry.pk]),
        headers={**HTMX, "HX-Current-URL": "http://testserver/library/?sort=title"},
    )
    assert response.status_code == 200
    assert response.content.decode().strip().startswith('<div id="library-results"')
    assert response["HX-Replace-Url"] == "/library/?sort=title"
    assert not SavedAsset.objects.filter(pk=entry.pk).exists()
    assert Asset.objects.filter(pk=entry.asset_id).exists()


def test_remove_from_the_full_page_returns_to_the_library(entry, member_client):
    from catalog.models import SavedAsset

    html = member_client.get(reverse("catalog:entry", args=[entry.pk])).content.decode()
    remove = reverse("catalog:remove", args=[entry.pk])
    # The page links to the confirm as a page, whose form is a plain (boosted) POST.
    assert f'<a href="{remove}" class="btn btn-quiet btn-sm gap-1.5">' in html
    confirm = member_client.get(remove).content.decode()
    form = re.search(rf'<form method="post" action="{remove}"[^>]*>', confirm).group(0)
    assert "hx-post" not in form
    # Boosted, as the page's form is sent: the whole library comes back, not a fragment.
    response = member_client.post(remove, headers={**HTMX, "HX-Boosted": "true"})
    assert response.status_code == 302 and response.url == reverse("catalog:library")
    assert not SavedAsset.objects.filter(pk=entry.pk).exists()


def test_notes_line_breaks_are_stored_as_typed(entry, member_client):
    """Browsers send CRLF; the box counts LF, so the limit holds for both."""
    from catalog.forms import NOTES_MAX_LENGTH

    lines = "a\r\n" * (NOTES_MAX_LENGTH // 2)
    assert _update(member_client, entry, {"notes": lines}).status_code == 200
    entry.refresh_from_db()
    assert entry.notes == "a\n" * (NOTES_MAX_LENGTH // 2)


def test_the_entry_page_uses_type_colour_only_for_the_assets_type(entry, member_client):
    html = member_client.get(reverse("catalog:entry", args=[entry.pk])).content.decode()
    content = html.split('id="content"', 1)[1].split('id="page-footer"', 1)[0]
    coloured = re.findall(
        r'class="([^"]*\b(?:text|bg)-(?:texture|hdri|model|sound)\b[^"]*)"', content
    )
    assert {classes.split()[0] for classes in coloured} == {"library-type-icon", "result-fallback"}
    chrome = html.split('id="content"', 1)[0] + html.split('id="status-bar"', 1)[1]
    assert not re.search(r"\b(?:text|bg)-(?:texture|hdri|model|sound)\b", chrome)
