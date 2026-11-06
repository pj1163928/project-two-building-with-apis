"""Download files for a pack and for one item (user request, 2026-11-05).

The Toolbox only lists the providers' URLs, each with its path in the zip
(packs.downloads); the browser fetches and zips them. These tests check that
list, where it puts each file, what goes beside the files, and who may read
it (the pack page's reader rule). App tests: no provider is ever called.
"""

import json

import pytest
from django.test import Client
from django.urls import reverse

from catalog.files import BUNDLE_MAX_BYTES
from catalog.models import SavedAsset
from packs.downloads import NO_FILES, TOO_LARGE
from packs.models import Pack
from packs.services import add_to_pack
from tests import test_pack_public
from tests.test_pack_public import _file, _variant

pytestmark = pytest.mark.django_db

# The golden pack and a second member, shared with test_pack_public.py.
golden_pack = test_pack_public.golden_pack
other = test_pack_public.other


def _files(client, pack, **params):
    response = client.get(reverse("packs:files", args=[pack.slug]), params)
    assert response.status_code == 200
    return response.json()


def _items(pack):
    return {item.asset.external_id: item for item in pack.ordered_items()}


# ---------------------------------------------------------------- the whole pack


def test_every_file_sits_under_its_items_import_path(client, golden_pack):
    data = _files(client, golden_pack)
    assert data["zip"] is True and data["zip_name"] == "medieval-village.zip"
    assert [(file["path"], file["size"]) for file in data["files"]] == [
        # A blank import path is the default, textures/<id>/.
        ("textures/red_brick_03/red_brick_03_diff_2k.jpg", 1500000),
        ("textures/red_brick_03/red_brick_03_nor_gl_2k.jpg", 2500000),
        # The owner's own path (a sound starts on its MP3, whose size is unknown).
        ("audio/ambience/birds-001.mp3", None),
        ("sounds/birds-002/birds-002.mp3", 81920),
        ("sounds/door-003/door-003.wav", 512000),
    ]
    # Only the providers' URLs: the Toolbox never serves a file itself.
    assert all(file["url"].startswith("https://") for file in data["files"])
    assert all("testserver" not in file["url"] for file in data["files"])


def test_the_zip_holds_the_credits_and_the_manifest_at_the_top(client, golden_pack):
    data = _files(client, golden_pack)
    extras = {extra["path"]: extra["text"] for extra in data["extras"]}
    assert set(extras) == {"CREDITS.txt", "medieval-village.axcenity-pack.json"}
    credits = extras["CREDITS.txt"]
    assert credits.startswith("ATTRIBUTION AND LICENSE NOTICE")
    assert "1. REQUIRED ATTRIBUTION" in credits and '"Forest Birds" by Jane Doe' in credits
    assert '"Creaking Door" by Sam Roe, CC BY-SA 3.0' in credits
    assert "OPTIONAL ACKNOWLEDGEMENTS" in credits and '"Market Crate" by ambientCG' in credits
    # The manifest in the zip is the download's, but for its export time.
    inside = json.loads(extras["medieval-village.axcenity-pack.json"])
    download = client.get(reverse("packs:export", args=[golden_pack.slug])).json()
    inside.pop("exported_at"), download.pop("exported_at")
    assert inside == download


def test_two_files_with_one_name_in_one_folder_both_arrive(client, member, make_asset):
    pack = Pack.objects.create_pack(member, "Twins")
    for external_id in ("a", "b"):
        asset = make_asset(
            external_id=external_id,
            variants=[
                _variant("2K JPG", _file(f"https://dl.polyhaven.org/{external_id}/x.jpg", 1))
            ],
        )
        item = add_to_pack(pack, SavedAsset.objects.create(user=member, asset=asset))[0]
        item.import_path = "textures/shared/"
        item.save()
    client.force_login(member)
    paths = [file["path"] for file in _files(client, pack)["files"]]
    assert paths == ["textures/shared/x.jpg", "textures/shared/x-2.jpg"]


def test_a_pack_with_no_files_or_over_2_gb_says_so(client, member, make_asset):
    pack = Pack.objects.create_pack(member, "Nothing Here")
    client.force_login(member)
    assert _files(client, pack) == {"error": NO_FILES}
    huge = make_asset(
        external_id="huge",
        variants=[
            _variant("8K EXR", _file("https://dl.polyhaven.org/huge.exr", BUNDLE_MAX_BYTES + 1))
        ],
    )
    add_to_pack(pack, SavedAsset.objects.create(user=member, asset=huge))
    assert _files(client, pack) == {"error": TOO_LARGE}


# ---------------------------------------------------------------- one item


def test_one_item_with_several_files_is_zipped_in_its_import_path(client, golden_pack):
    brick = _items(golden_pack)["red_brick_03"]
    data = _files(client, golden_pack, item=brick.pk)
    assert data["zip"] is True and data["zip_name"] == "red_brick_03_2K-JPG.zip"
    assert [file["path"] for file in data["files"]] == [
        "textures/red_brick_03/red_brick_03_diff_2k.jpg",
        "textures/red_brick_03/red_brick_03_nor_gl_2k.jpg",
    ]
    assert [extra["path"] for extra in data["extras"]] == ["textures/red_brick_03/CREDITS.txt"]
    assert data["provider"] == "Poly Haven"


def test_one_item_with_one_file_is_saved_as_it_is(client, golden_pack):
    door = _items(golden_pack)["door-003"]
    data = _files(client, golden_pack, item=door.pk)
    assert data["zip"] is False
    assert [file["path"] for file in data["files"]] == ["sounds/door-003/door-003.wav"]
    # Its own credit only, never the rest of the pack's.
    credits = data["extras"][0]["text"]
    assert "Creaking Door" in credits and "Forest Birds" not in credits


def test_an_item_from_another_pack_or_no_item_is_a_404(client, golden_pack, member, make_asset):
    elsewhere = Pack.objects.create_pack(member, "Elsewhere")
    stray = add_to_pack(
        elsewhere, SavedAsset.objects.create(user=member, asset=make_asset(external_id="stray"))
    )[0]
    url = reverse("packs:files", args=[golden_pack.slug])
    assert client.get(url, {"item": stray.pk}).status_code == 404
    assert client.get(url, {"item": "nope"}).status_code == 404
    assert client.get(url, {"item": "999999"}).status_code == 404


# ---------------------------------------------------------------- who may read it


def test_a_private_packs_files_are_a_404_to_anyone_but_the_owner(golden_pack, member, other):
    golden_pack.set_visibility("private")
    url = reverse("packs:files", args=[golden_pack.slug])
    assert Client().get(url).status_code == 404
    signed_in = Client()
    signed_in.force_login(other)
    assert signed_in.get(url).status_code == 404
    item = golden_pack.items.first()
    assert signed_in.get(url, {"item": item.pk}).status_code == 404
    owner = Client()
    owner.force_login(member)
    assert owner.get(url).status_code == 200


def test_an_unlisted_packs_files_come_only_through_its_share_link(golden_pack, other):
    golden_pack.set_visibility("unlisted")
    signed_in = Client()
    signed_in.force_login(other)
    assert signed_in.get(reverse("packs:files", args=[golden_pack.slug])).status_code == 404
    link = reverse("packs:shared_files", args=[golden_pack.share_token])
    for client in (Client(), signed_in):
        response = client.get(link)
        assert response.status_code == 200 and response.json()["files"]
        assert response["X-Robots-Tag"] == "noindex, nofollow"
    golden_pack.rotate_share_token()
    assert Client().get(link).status_code == 404


def test_the_files_never_carry_the_owners_review(client, golden_pack):
    entry = golden_pack.items.first().saved_asset
    entry.notes = "SENTINEL-NOTE never share this"
    entry.rating, entry.status = 2, SavedAsset.Status.REJECTED
    entry.save()
    body = client.get(reverse("packs:files", args=[golden_pack.slug])).content.decode()
    assert "SENTINEL-NOTE" not in body and "rejected" not in body.lower()
    assert '"rating"' not in body


def test_the_files_url_is_get_only(golden_pack, member):
    owner = Client()
    owner.force_login(member)
    url = reverse("packs:files", args=[golden_pack.slug])
    for method in (owner.post, owner.put, owner.patch, owner.delete):
        assert method(url).status_code == 405


# ---------------------------------------------------------------- the buttons


def test_the_pack_page_offers_both_downloads_and_one_per_item(client, golden_pack):
    html = client.get(reverse("packs:public", args=[golden_pack.slug])).content.decode()
    files_url = reverse("packs:files", args=[golden_pack.slug])
    assert f'data-bundle-url="{files_url}"' in html and "Download files" in html
    assert "Download manifest" in html
    brick = _items(golden_pack)["red_brick_03"]
    # Several files: the browser zips them. One file: a plain link to the provider.
    assert f'data-bundle-url="{files_url}?item={brick.pk}"' in html
    assert 'href="https://cdn.freesound.org/sounds/3/door-003.wav"' in html
    assert "Download door-003.wav" in html


def test_the_builder_offers_downloads_for_the_pack_and_each_item(member_client, golden_pack):
    html = member_client.get(reverse("packs:builder", args=[golden_pack.pk])).content.decode()
    files_url = reverse("packs:files", args=[golden_pack.slug])
    assert f'data-bundle-url="{files_url}"' in html
    assert reverse("packs:export", args=[golden_pack.slug]) in html
    for item in golden_pack.items.exclude(saved_asset__asset__variants=[]):
        assert f'data-bundle-url="{files_url}?item={item.pk}"' in html
