"""Public packs (Phase 8): who can see a pack, the manifest, the public page and
its download, and the sentinel that keeps a member's review out of every pack.

App tests, so provider functions are never reached.
"""

import json
import re
from datetime import UTC, datetime
from pathlib import Path

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import Client
from django.urls import reverse
from django.utils.html import escape
from rest_framework.authtoken.models import Token

from catalog.models import SavedAsset
from packs.manifest import build_manifest
from packs.models import Pack, PackItem
from packs.services import add_to_pack

pytestmark = pytest.mark.django_db

GOLDEN = Path(__file__).parent / "golden" / "pack_manifest.json"
FROZEN = datetime(2026, 11, 5, 12, 0, tzinfo=UTC)
SOURCE_URL = "http://testserver/packs/medieval-village/"
CC0_URL = "https://creativecommons.org/publicdomain/zero/1.0/"
BY_URL = "https://creativecommons.org/licenses/by/4.0/"
BIRDS = '"Forest Birds" by Jane Doe is licensed under CC BY 4.0.'
PH = "https://dl.polyhaven.org/file/ph-assets/Textures/jpg"


def _file(url, size):
    return {"url": url, "filename": url.rsplit("/", 1)[1], "size": size}


def _variant(label, *files):
    sizes = [file["size"] for file in files]
    return {
        "label": label,
        "files": list(files),
        "total_size": None if None in sizes else sum(sizes),
    }


@pytest.fixture
def other(django_user_model, password):
    return django_user_model.objects.create_user(username="other_member", password=password)


@pytest.fixture
def golden_pack(member, make_asset):
    """The golden file's pack: five items, added out of order and then arranged.

    A CC0 texture whose 2K JPG has two files and whose path is blank; two CC BY
    sounds sharing one attribution (credited once), one with its own path; a
    CC BY-SA sound with no attribution and only a WAV; a CC0 model with no files.
    """
    pack = Pack.objects.create_pack(
        member, "Medieval Village", "A market square at dusk.", "Wood, stones, medieval"
    )
    texture = make_asset(
        variants=[
            _variant("1K JPG", _file(f"{PH}/1k/red_brick_03/red_brick_03_diff_1k.jpg", 400000)),
            _variant(
                "2K JPG",
                _file(f"{PH}/2k/red_brick_03/red_brick_03_diff_2k.jpg", 1500000),
                _file(f"{PH}/2k/red_brick_03/red_brick_03_nor_gl_2k.jpg", 2500000),
            ),
        ]
    )
    birds = make_asset(
        provider="openverse",
        external_id="birds-001",
        kind="sound",
        title="Forest Birds",
        author="Jane Doe",
        license="CC BY 4.0",
        license_url=BY_URL,
        attribution=BIRDS,
        source_url="https://freesound.org/s/birds-001/",
        variants=[
            _variant("OGG", _file("https://cdn.freesound.org/previews/1/birds-001.ogg", 70000)),
            _variant("MP3", _file("https://cdn.freesound.org/previews/1/birds-001.mp3", None)),
        ],
    )
    loop = make_asset(
        provider="openverse",
        external_id="birds-002",
        kind="sound",
        title="Forest Birds (loop)",
        author="Jane Doe",
        license="CC BY 4.0",
        license_url=BY_URL,
        attribution=BIRDS,
        source_url="https://freesound.org/s/birds-002/",
        variants=[
            _variant("MP3", _file("https://cdn.freesound.org/previews/1/birds-002.mp3", 81920))
        ],
    )
    door = make_asset(
        provider="openverse",
        external_id="door-003",
        kind="sound",
        title="Creaking Door",
        author="Sam Roe",
        license="CC BY-SA 3.0",
        license_url="https://creativecommons.org/licenses/by-sa/3.0/",
        attribution="",
        source_url="https://freesound.org/s/door-003/",
        variants=[
            _variant("WAV", _file("https://cdn.freesound.org/sounds/3/door-003.wav", 512000))
        ],
    )
    crate = make_asset(
        provider="ambientcg",
        external_id="Crate001",
        kind="model",
        title="Market Crate",
        author="ambientCG",
        license="CC0",
        license_url=CC0_URL,
        attribution="Crate001 by ambientCG, CC0",
        source_url="https://ambientcg.com/view?id=Crate001",
        variants=[],
    )
    # Added in a different order from the one the owner then arranges.
    items = {}
    for asset in (door, texture, crate, birds, loop):
        entry = SavedAsset.objects.create(user=member, asset=asset)
        items[asset.external_id] = add_to_pack(pack, entry)[0]
    order = ["red_brick_03", "birds-001", "birds-002", "door-003", "Crate001"]
    for position, external_id in enumerate(order):
        PackItem.objects.filter(pk=items[external_id].pk).update(position=position)
    PackItem.objects.filter(pk=items["birds-001"].pk).update(import_path="audio/ambience/")
    pack.set_visibility("public")
    return pack


# ---------------------------------------------------------------- the manifest


def test_manifest_matches_the_golden_file_field_for_field(golden_pack):
    manifest = build_manifest(golden_pack, source_url=SOURCE_URL, exported_at=FROZEN)

    assert manifest == json.loads(GOLDEN.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- who can see a pack


def test_visible_to_is_public_packs_plus_the_callers_own(member, other):
    mine_private = Pack.objects.create_pack(member, "My Private Kit")
    mine_public = Pack.objects.create_pack(member, "My Public Kit")
    theirs_private = Pack.objects.create_pack(other, "Their Private Kit")
    theirs_public = Pack.objects.create_pack(other, "Their Public Kit")
    Pack.objects.filter(pk__in=[mine_public.pk, theirs_public.pk]).update(visibility="public")

    assert set(Pack.objects.visible_to(member)) == {mine_private, mine_public, theirs_public}
    assert set(Pack.objects.visible_to(other)) == {theirs_private, theirs_public, mine_public}
    assert set(Pack.objects.visible_to(AnonymousUser())) == {mine_public, theirs_public}


# ---------------------------------------------------------------- the sentinel

# Plain characters only, so HTML escaping can't hide it from the search below.
SENTINEL = "SENTINEL-7f3c-owner-private-note"
PRIVATE_KEYS = {"notes", "rating", "status", "status_change", "status_reason", "community"}


def _keys(data):
    """Every key anywhere in a decoded JSON document."""
    if isinstance(data, dict):
        return set(data) | {key for value in data.values() for key in _keys(value)}
    if isinstance(data, list):
        return {key for value in data for key in _keys(value)}
    return set()


def test_the_owners_review_never_shows_through_a_pack(member, other, golden_pack):
    """Known notes, a rating and a status on the owner's entry (and another
    member's rating of the same asset) never reach the pack page, the API
    detail, the API list or either export, whoever is reading."""
    entry = SavedAsset.objects.get(user=member, asset__external_id="red_brick_03")
    entry.notes, entry.rating, entry.status = SENTINEL, 4, SavedAsset.Status.REJECTED
    entry.save()
    SavedAsset.objects.create(user=other, asset=entry.asset, notes=SENTINEL, rating=2)

    visitor = Client()
    owner = Client()
    owner.force_login(member)
    reader = Client(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=other).key}")
    reader_session = Client()
    reader_session.force_login(other)

    pages = [reverse("packs:public", args=[golden_pack.slug])]
    documents = [
        reverse("packs:export", args=[golden_pack.slug]),
        reverse("packs:api_packs"),
        reverse("packs:api_pack", args=[golden_pack.pk]),
        reverse("packs:api_pack_export", args=[golden_pack.pk]),
    ]
    for who in (visitor, owner, reader, reader_session):
        for url in pages:
            response = who.get(url)
            assert response.status_code == 200, url
            html = response.content.decode()
            assert SENTINEL not in html and escape(SENTINEL) not in html, url
            content = html.split('id="content"', 1)[1].split('id="page-footer"', 1)[0]
            for private in ("Rejected", "rejected", "star-rating", "rate-star", "community"):
                assert private not in content, f"{url} shows {private!r}"
        for url in documents:
            response = who.get(url)
            assert response.status_code == 200, url
            body = response.content.decode()
            assert SENTINEL not in body, url
            assert "rejected" not in body.lower(), url
            assert not _keys(json.loads(body)) & PRIVATE_KEYS, url


# ---------------------------------------------------------------- the pack page


def _content(response):
    html = response.content.decode()
    return html.split('id="content"', 1)[1].split('id="page-footer"', 1)[0]


def _text(html):
    return " ".join(re.sub(r"<[^>]+>", " ", html).split())


@pytest.mark.parametrize("who", ["visitor", "other"])
def test_a_non_owner_sees_the_pack_read_only(golden_pack, other, who):
    client = Client()
    if who == "other":
        client.force_login(other)

    content = _content(client.get(reverse("packs:public", args=[golden_pack.slug])))

    assert "Edit in builder" not in content
    assert reverse("packs:builder", args=[golden_pack.pk]) not in content
    _assert_no_edit_controls(content, golden_pack)


def _assert_no_edit_controls(content, pack):
    """Read-only: no field to change, and the only forms are Phase 11's Save to
    library and Copy pack (and the copy dialog's Cancel), never a pack write."""
    assert "<select" not in content and "<textarea" not in content
    for tag in re.findall(r"<input[^>]*>", content):
        assert 'type="hidden" name="csrfmiddlewaretoken"' in tag, tag
    allowed = {reverse("packs:copy", args=[pack.slug])} | {
        reverse("packs:save_item", args=[pack.slug, item.pk]) for item in pack.items.all()
    }
    for form in re.findall(r"<form[^>]*>", content):
        if 'method="dialog"' in form:
            continue
        action = re.search(r'action="([^"]+)"', form).group(1)
        assert action in allowed, form
    assert set(re.findall(r'hx-post="([^"]+)"', content)) <= allowed


def test_the_owner_gets_a_way_into_the_builder(member_client, golden_pack):
    content = _content(member_client.get(reverse("packs:public", args=[golden_pack.slug])))

    assert f'href="{reverse("packs:builder", args=[golden_pack.pk])}"' in content
    assert "Edit in builder" in content
    # Still read-only here: every change happens in the builder.
    _assert_no_edit_controls(content, golden_pack)


def test_the_owner_sees_their_private_pack_marked_private(member_client, member):
    pack = Pack.objects.create_pack(member, "Work In Progress")

    text = _text(_content(member_client.get(reverse("packs:public", args=[pack.slug]))))

    assert "Private pack" in text
    assert "Private · only you" in text


def test_the_page_lists_items_in_order_with_licenses_and_credit(golden_pack):
    content = _content(Client().get(reverse("packs:public", args=[golden_pack.slug])))
    text = _text(content)

    titles = re.findall(r'<p class="pack-item-title">([^<]+)</p>', content)
    assert titles == [
        "Red Brick 03",
        "Forest Birds",
        "Forest Birds (loop)",
        "Creaking Door",
        "Market Crate",
    ]
    assert "Public pack" in text and "By demo_member · 5 items" in text
    assert "A market square at dusk." in text
    for tag in ("medieval", "stone", "wood"):
        assert f"<span>{tag}</span>" in content
    # CC0 items need no credit; the others show theirs (or one built for them).
    assert text.count("no credit needed") == 2
    assert 'href="https://creativecommons.org/licenses/by/4.0/"' in content
    assert "&quot;Forest Birds&quot; by Jane Doe is licensed under CC BY 4.0." in content
    assert "&quot;Creaking Door&quot; by Sam Roe, CC BY-SA 3.0" in content
    assert "3 items need credit in your game." in text
    # The chosen variant, its files and the import path the export will use.
    assert '<span class="file-badge">2K JPG</span>' in content
    assert "2 files · 3.8 MB" in text
    assert "textures/red_brick_03/" in text and "audio/ambience/" in text
    assert "No files listed" in text
    assert 'href="https://polyhaven.com/a/red_brick_03"' in content


def test_download_manifest_is_a_plain_download_not_a_boosted_swap(golden_pack):
    content = _content(Client().get(reverse("packs:public", args=[golden_pack.slug])))

    link = re.search(r'<a href="/packs/medieval-village/export/"[^>]*>', content).group(0)
    assert 'hx-boost="false"' in link
    assert 'download="medieval-village.axcenity-pack.json"' in link


def test_a_visitor_gets_a_sign_up_prompt_in_the_side_panel(golden_pack):
    html = Client().get(reverse("packs:public", args=[golden_pack.slug])).content.decode()

    panel = html.split('id="side-panel"', 1)[1].split("</aside>", 1)[0]
    assert 'id="pack-visitor-panel"' in panel
    assert f"{reverse('accounts:signup')}?next=/packs/medieval-village/" in panel


def test_an_empty_pack_says_so(member_client, member):
    pack = Pack.objects.create_pack(member, "Nothing Yet")

    text = _text(_content(member_client.get(reverse("packs:public", args=[pack.slug]))))

    assert "This pack is empty." in text
    assert "Every item is CC0, so nothing needs credit." in text


# ---------------------------------------------------------------- slugs and links


@pytest.mark.parametrize("title, slug", [("New", "new-2"), ("Picker", "picker-2")])
def test_a_pack_never_takes_a_slug_that_is_a_page(member, title, slug):
    assert Pack.objects.create_pack(member, title).slug == slug


def test_the_builder_and_the_pack_list_link_to_the_pack_page(member_client, golden_pack):
    page_url = reverse("packs:public", args=[golden_pack.slug])

    builder = _content(member_client.get(reverse("packs:builder", args=[golden_pack.pk])))
    assert re.search(rf'<a id="pack-page-link" href="{page_url}"', builder)
    packs = _content(member_client.get(reverse("packs:list")))
    assert f'href="{page_url}" class="pack-card-page' in packs


def test_featured_in_public_packs_links_each_pack_to_its_page(golden_pack, other):
    # Another member saves the golden pack's texture and opens it in their library.
    texture = golden_pack.ordered_items()[0].asset
    entry = SavedAsset.objects.create(user=other, asset=texture)
    client = Client()
    client.force_login(other)

    content = _content(client.get(reverse("catalog:entry", args=[entry.pk])))

    featured = content.split('id="entry-featured"', 1)[1].split("</ul>", 1)[0]
    assert f'href="{golden_pack.get_public_url()}"' in featured


# ---------------------------------------------------------------- the manifest's edges


def test_a_variant_the_asset_no_longer_lists_falls_back_to_the_default(golden_pack):
    item = golden_pack.ordered_items()[0]
    PackItem.objects.filter(pk=item.pk).update(preferred_variant="16K EXR")

    manifest = build_manifest(golden_pack, source_url=SOURCE_URL, exported_at=FROZEN)

    assert manifest["items"][0]["variant"] == "2K JPG"


def test_the_manifest_is_dated_now_in_utc_to_the_second(golden_pack):
    manifest = build_manifest(golden_pack, source_url=SOURCE_URL)

    stamp = datetime.fromisoformat(manifest["exported_at"])
    assert stamp.utcoffset().total_seconds() == 0 and stamp.microsecond == 0
