"""Discover's drawer (user request, 2026-11-06): a result opens in a slide-over
drawer, like the library's, with View on <provider> still a click away.

App tests: provider functions are replaced with `monkeypatch` (docs/TESTING.md).
"""

import re

import pytest
from django.test import Client
from django.urls import reverse

from catalog.models import Asset, SavedAsset
from catalog.preview import asset_preview
from providers import AssetRecord, ProviderError, openverse, polyhaven
from providers.records import Variant, VariantFile

pytestmark = pytest.mark.django_db

HTMX = {"HX-Request": "true"}
PREVIEW = "https://cdn.freesound.org/previews/rain.mp3"


def asset_url(provider="polyhaven", external_id="red_brick_03"):
    return reverse("catalog:discover_asset", args=[provider, external_id])


def fetched(provider="polyhaven", external_id="red_brick_03", kind="texture", **fields):
    values = {
        "title": "Red Brick 03",
        "author": "Rob Tuytel",
        "thumbnail_url": f"https://cdn.example/{external_id}.png",
        "license": "CC0",
        "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        "attribution": "Red Brick 03 by Rob Tuytel",
        "source_url": f"https://polyhaven.com/a/{external_id}",
        "tags": ("brick", "wall"),
        "variants": (
            Variant(
                "2K JPG",
                (
                    VariantFile("https://dl.example/red_brick_03_diff_2k.jpg", "diff_2k.jpg", 100),
                    VariantFile(
                        "https://dl.example/red_brick_03_nor_gl_2k.jpg", "nor_gl_2k.jpg", 200
                    ),
                ),
            ),
        ),
    }
    values.update(fields)
    return AssetRecord(provider=provider, external_id=external_id, kind=kind, **values)


@pytest.fixture
def fetches(monkeypatch):
    """Replace Poly Haven's and Openverse's fetch_record; the list records each call."""
    calls = []

    def fake_for(provider, kind):
        def fake(external_id):
            calls.append((provider.KEY, external_id))
            extra = {"preview_url": PREVIEW} if kind == "sound" else {}
            return fetched(provider=provider.KEY, external_id=external_id, kind=kind, **extra)

        return fake

    monkeypatch.setattr(polyhaven, "fetch_record", fake_for(polyhaven, "texture"))
    monkeypatch.setattr(openverse, "fetch_record", fake_for(openverse, "sound"))
    return calls


def test_a_cards_title_opens_the_drawer_and_the_page_holds_one(client):
    html = client.get(reverse("catalog:discover")).content.decode()
    assert html.count('<dialog id="discover-drawer" class="drawer-dialog"') == 1


def test_the_drawer_shows_the_result_with_view_on_the_provider(client, fetches):
    html = client.get(asset_url(), headers=HTMX).content.decode()
    assert '<div class="drawer-panel">' in html and "<html" not in html
    assert "Discover result" in html
    assert '<h2 id="entry-title" class="entry-title">Red Brick 03</h2>' in html
    # The source site: in the drawer's head and as the primary action, in a new tab.
    source = 'href="https://polyhaven.com/a/red_brick_03" target="_blank" rel="noopener noreferrer"'
    assert html.count(source) == 3  # head, actions, Source row
    assert re.search(source + r' class="btn btn-primary[^"]*">.*?View on Poly Haven', html, re.S)
    # The license: its symbols, "Can I use it?" and its card in the guide.
    assert (
        'class="license-symbols is-large" role="img" aria-label="CC0: Public domain dedication"'
        in html
    )
    assert 'class="use-grid" aria-label="Can I use it?"' in html
    assert 'href="/attribution/#license-cc0"' in html
    assert "brick, wall" in html
    assert '<span class="file-badge">2K</span><span class="file-badge">JPG</span>' in html
    assert "2 files · 300" in html
    assert fetches == [("polyhaven", "red_brick_03")]


def test_viewing_a_result_saves_nothing_and_is_cached(client, fetches):
    client.get(asset_url(), headers=HTMX)
    client.get(asset_url(), headers=HTMX)
    assert fetches == [("polyhaven", "red_brick_03")]
    assert not Asset.objects.exists()


def test_a_stored_asset_is_shown_without_asking_the_provider(client, fetches, make_asset):
    make_asset(title="Stored Brick")
    html = client.get(asset_url(), headers=HTMX).content.decode()
    assert "Stored Brick" in html
    assert fetches == []


def test_a_direct_visit_gets_the_same_result_as_a_centred_page(client, fetches):
    response = client.get(asset_url())
    html = response.content.decode()
    assert response.status_code == 200
    assert '<section class="discover-asset-page space-y-5">' in html
    assert '<h1 id="entry-title" class="entry-title">Red Brick 03</h1>' in html
    assert "Back to Discover" in html


def test_a_bad_provider_or_id_is_a_400_before_any_provider(client, fetches):
    assert client.get(asset_url("freesound", "x"), headers=HTMX).status_code == 400
    assert client.get(asset_url("polyhaven", "x" * 201), headers=HTMX).status_code == 400
    assert fetches == []


def test_a_provider_error_shows_its_message_with_retry(client, monkeypatch):
    def fail(external_id):
        raise ProviderError("Poly Haven didn't answer in time. Try again in a moment.")

    monkeypatch.setattr(polyhaven, "fetch_record", fail)
    html = client.get(asset_url(), headers=HTMX).content.decode()
    assert "Poly Haven is unavailable" in html
    assert "answer in time. Try again in a moment." in html
    assert f'hx-get="{asset_url()}" hx-target="#discover-drawer"' in html
    assert 'href="https://polyhaven.com" target="_blank"' in html


def test_a_visitor_is_offered_sign_in_back_to_their_search(client, fetches):
    back = "/discover/?type=texture&q=brick"
    headers = {**HTMX, "HX-Current-URL": f"http://testserver{back}"}
    html = client.get(asset_url(), headers=headers).content.decode()
    assert "Sign in to save" in html and "Sign in to add to a pack" in html
    assert "next=/discover/%3Ftype%3Dtexture%26q%3Dbrick" in html
    assert "hx-post" not in html


def test_a_member_saves_from_the_drawer(member, member_client, fetches):
    html = member_client.get(asset_url(), headers=HTMX).content.decode()
    assert '<input type="hidden" name="slot" value="drawer">' in html
    assert 'data-picker="pack-picker"' in html
    response = member_client.post(
        reverse("catalog:save"),
        {"provider": "polyhaven", "external_id": "red_brick_03", "slot": "drawer"},
        headers=HTMX,
    )
    reply = response.content.decode()
    assert '<div class="preview-save">' in reply and "In your library" in reply
    assert 'id="saved-count"' in reply  # the status bar's count, out of band
    assert SavedAsset.objects.filter(user=member, asset__external_id="red_brick_03").exists()
    # Opened again, it says so straight away.
    assert "In your library" in member_client.get(asset_url(), headers=HTMX).content.decode()


def test_a_failed_save_from_the_drawer_says_try_again(member_client, monkeypatch):
    def fail(external_id):
        raise ProviderError("Poly Haven is busy right now.")

    monkeypatch.setattr(polyhaven, "fetch_record", fail)
    reply = member_client.post(
        reverse("catalog:save"),
        {"provider": "polyhaven", "external_id": "red_brick_03", "slot": "drawer"},
        headers=HTMX,
    ).content.decode()
    assert "Try again" in reply and "Poly Haven is busy right now." in reply


def test_a_sound_plays_in_the_drawer(client, fetches):
    html = client.get(asset_url("openverse", "rain-1"), headers=HTMX).content.decode()
    assert re.search(
        r'<article class="entry discover-entry" data-kind="sound" data-sound-card', html
    )
    assert f'data-sound-preview="{PREVIEW}"' in html


def test_asset_preview_lists_the_records_variants(fetches):
    preview = asset_preview("polyhaven", "red_brick_03")
    assert preview.kind_label == "Texture" and preview.provider_name == "Poly Haven"
    assert [variant.label for variant in preview.variants] == ["2K JPG"]
    assert preview.license_info.key == "cc0"


def test_the_drawer_opens_and_closes_like_the_librarys(client):
    from django.conf import settings

    script = (settings.BASE_DIR / "static" / "js" / "entry-drawer.js").read_text(encoding="utf-8")
    assert 'document.querySelector("dialog.drawer-dialog")' in script


def test_another_client_never_sees_a_members_saved_state(member, member_client, fetches):
    SavedAsset.objects.create(user=member, asset=Asset.objects.from_record(fetched(variants=())))
    assert "In your library" in member_client.get(asset_url(), headers=HTMX).content.decode()
    assert "In your library" not in Client().get(asset_url(), headers=HTMX).content.decode()
