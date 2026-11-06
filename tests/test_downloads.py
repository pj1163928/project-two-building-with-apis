"""Files told apart by resolution, format and map type, a member's download defaults,
and the bundle they pick (user request, 2026-11-05).

The bundle is only ever the provider's URLs: the browser fetches and zips them
(static/js/bundle-download.js), so no test here reaches a provider.
"""

import json
import re

import pytest
from django.test import Client
from django.urls import reverse

from catalog.files import (
    BUNDLE_MAX_BYTES,
    MAP_KEYS,
    describe_variant,
    file_filters,
    map_type,
    pick_bundle,
    safe_path,
)

pytestmark = pytest.mark.django_db

SLUG = "rusty_metal_02"


def _maps(resolution, ext, maps=("diff", "nor_gl", "nor_dx", "rough", "arm", "ao", "disp")):
    return {
        "label": f"{resolution} {ext.upper()}",
        "files": [
            {
                "url": f"https://dl.polyhaven.org/{SLUG}_{name}_{resolution.lower()}.{ext}",
                "filename": f"{SLUG}_{name}_{resolution.lower()}.{ext}",
                "size": 1_000_000,
            }
            for name in maps
        ],
    }


def _gltf(resolution):
    return {
        "label": f"{resolution} glTF",
        "files": [
            {
                "url": "https://dl.polyhaven.org/a.gltf",
                "filename": f"{SLUG}_{resolution}.gltf",
                "size": 10,
            },
            {"url": "https://dl.polyhaven.org/a.bin", "filename": f"{SLUG}.bin", "size": 10},
            {
                "url": "https://dl.polyhaven.org/d.jpg",
                "filename": f"textures/{SLUG}_diff_{resolution.lower()}.jpg",
                "size": 10,
            },
        ],
    }


POLY_HAVEN = [
    _maps("1K", "jpg"),
    _maps("1K", "exr"),
    _gltf("1K"),
    _maps("2K", "jpg"),
    _maps("2K", "png"),
]
POLY_HAVEN += [_gltf("2K"), _maps("4K", "jpg")]


class Prefs:
    """Stands in for accounts.models.DownloadPreferences."""

    def __init__(self, resolution="2K", fmt="jpg", maps=MAP_KEYS):
        self.resolution = resolution
        self.texture_format = self.hdri_format = self.model_format = self.sound_format = fmt
        self.maps = list(maps)

    def format_for(self, kind):
        return self.texture_format


# ---------------------------------------------------------------- telling files apart


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        (f"{SLUG}_diff_2k.jpg", "color"),
        (f"{SLUG}_nor_gl_2k.exr", "normal_gl"),
        (f"{SLUG}_nor_dx_2k.png", "normal_dx"),
        (f"{SLUG}_rough_2k.jpg", "rough"),
        (f"{SLUG}_arm_2k.jpg", "arm"),
        (f"{SLUG}_ao_2k.jpg", "ao"),
        (f"{SLUG}_disp_2k.png", "disp"),
        (f"textures/{SLUG}_diff_1k.jpg", "color"),  # inside a bundle
        (f"{SLUG}_2k.gltf", ""),  # a scene, not a map
        (f"{SLUG}.bin", ""),
        ("Metal063_2K-JPG.zip", ""),  # an ambientCG archive
    ],
)
def test_each_file_is_told_apart_by_the_map_it_holds(filename, expected):
    assert map_type(filename, SLUG) == expected


def test_the_assets_own_name_never_counts_as_its_map():
    # "rusty_metal_02" says "metal", but this file is the roughness map.
    assert map_type("rusty_metal_02_rough_2k.jpg", "rusty_metal_02") == "rough"
    assert map_type("rusty_metal_02_metal_2k.jpg", "rusty_metal_02") == "metal"


@pytest.mark.parametrize(
    ("variant", "resolution", "format_key", "format_label", "package"),
    [
        (_maps("2K", "jpg"), "2K", "jpg", "JPG", "maps"),
        (_gltf("1K"), "1K", "gltf", "glTF", "bundle"),
        (
            {"label": "1K MaterialX", "files": [{"filename": "a_1k.mtlx"}]},
            "1K",
            "mtlx",
            "MaterialX",
            "bundle",
        ),
        (
            {"label": "2K JPG", "files": [{"filename": "Metal063_2K-JPG.zip"}]},
            "2K",
            "jpg",
            "JPG",
            "archive",
        ),
        ({"label": "4K", "files": [{"filename": "Sky_4K.zip"}]}, "4K", "zip", "ZIP", "archive"),
        ({"label": "MP3", "files": [{"filename": "123.mp3"}]}, "", "mp3", "MP3", "audio"),
    ],
)
def test_each_variant_is_told_apart_by_resolution_format_and_package(
    variant, resolution, format_key, format_label, package
):
    info = describe_variant(variant, SLUG)
    assert (info.resolution, info.format_key, info.format_label, info.package) == (
        resolution,
        format_key,
        format_label,
        package,
    )


def test_file_roles_name_maps_and_everything_else():
    roles = [file.role for file in describe_variant(_gltf("1K"), SLUG).files]
    assert roles == ["Scene", "Data", "Color"]


def test_the_filters_offer_each_resolution_and_format_once():
    filters = file_filters([describe_variant(variant, SLUG) for variant in POLY_HAVEN])
    assert filters.resolutions == ["1K", "2K", "4K"]
    assert filters.formats == [("jpg", "JPG"), ("exr", "EXR"), ("gltf", "glTF"), ("png", "PNG")]


# ---------------------------------------------------------------- picking the bundle


def _variants(raw=POLY_HAVEN):
    return [describe_variant(variant, SLUG) for variant in raw]


def test_the_bundle_takes_the_members_resolution_and_format():
    bundle = pick_bundle("texture", _variants(), Prefs("2K", "png"))
    assert bundle.variant.label == "2K PNG" and len(bundle.files) == 7 and not bundle.notes


def test_a_missing_resolution_falls_back_to_the_nearest_below_then_above():
    below = pick_bundle("texture", _variants(), Prefs("8K", "jpg"))
    assert below.variant.label == "4K JPG"
    assert "No 8K here, so 4K, the nearest." in below.notes
    above = pick_bundle("texture", _variants(POLY_HAVEN[3:]), Prefs("1K", "jpg"))
    assert above.variant.label == "2K JPG"


def test_a_missing_format_falls_back_to_the_next_best_for_the_kind():
    bundle = pick_bundle("texture", _variants(), Prefs("4K", "exr"))
    # No 4K EXR: the format comes first, so 1K EXR, the only EXR, beats 4K JPG.
    assert bundle.variant.label == "1K EXR"
    model = pick_bundle("model", _variants(), Prefs("2K", "fbx"))
    assert model.variant.label == "2K glTF"  # glTF is the next best model format
    assert "No FBX here, so glTF." in model.notes


def test_loose_maps_keep_only_the_members_maps():
    bundle = pick_bundle(
        "texture", _variants(), Prefs("2K", "jpg", maps=["color", "normal_gl", "rough"])
    )
    assert [file.map_key for file in bundle.files] == ["color", "normal_gl", "rough"]
    assert "3 of 7 maps, as your defaults choose." in bundle.notes
    assert bundle.map_labels == ["Color", "Normal GL", "Roughness"]


def test_a_bundle_is_taken_whole_whatever_the_maps():
    bundle = pick_bundle("model", _variants(), Prefs("1K", "gltf", maps=["rough"]))
    assert bundle.variant.label == "1K glTF" and len(bundle.files) == 3


def test_an_asset_with_no_files_has_no_bundle():
    bundle = pick_bundle("texture", [], Prefs())
    assert bundle.variant is None and not bundle.files


def test_the_manifest_keeps_every_file_inside_one_folder():
    raw = {
        "label": "1K glTF",
        "files": [
            {"url": "https://x/a", "filename": "../../etc/passwd", "size": 1},
            {"url": "https://x/b", "filename": "textures\\a.jpg", "size": 1},
            {"url": "https://x/c", "filename": "textures/a.jpg", "size": 1},
            {"url": "https://x/d", "filename": "scene.gltf", "size": 1},
        ],
    }
    bundle = pick_bundle("model", [describe_variant(raw, SLUG)], Prefs("1K", "gltf"))
    paths = [entry["path"] for entry in bundle.manifest("../evil")]
    assert paths == [
        "evil/etc/passwd",
        "evil/textures/a.jpg",
        "evil/textures/a-2.jpg",
        "evil/scene.gltf",
    ]
    assert safe_path("a/./b/../c") == "a/b/c"
    assert bundle.zip_name(SLUG) == f"{SLUG}_1K_glTF.zip"


def test_a_bundle_over_the_limit_is_too_large():
    huge = {
        "label": "8K EXR",
        "files": [{"filename": f"{SLUG}_diff_8k.exr", "size": BUNDLE_MAX_BYTES + 1}],
    }
    assert pick_bundle("texture", _variants([huge]), Prefs("8K", "exr")).too_large


# ---------------------------------------------------------------- download defaults


def test_preferences_default_to_2k_jpg_and_every_map_without_writing(member):
    from accounts.models import DownloadPreferences

    prefs = DownloadPreferences.objects.for_user(member)
    assert prefs.pk is None
    assert (prefs.resolution, prefs.texture_format, prefs.model_format, prefs.sound_format) == (
        "2K",
        "jpg",
        "gltf",
        "mp3",
    )
    assert prefs.maps == list(MAP_KEYS) and prefs.summary == "2K · JPG · every map"
    assert not DownloadPreferences.objects.exists()


def test_the_settings_page_shows_each_default_checked(member_client):
    html = member_client.get(reverse("accounts:settings")).content.decode()
    assert "Download defaults" in html
    assert re.search(r'name="resolution" value="2K" checked', html)
    assert re.search(r'name="texture_format" value="jpg" checked', html)
    assert html.count('name="maps"') == len(MAP_KEYS)
    assert 'hx-post="/accounts/settings/downloads/"' in html
    # No Save button: each group saves on change (one appears only without JavaScript).
    panel = html.split('id="download-defaults"', 1)[1].split("</section>", 1)[0]
    assert "<button" not in re.sub(r"<noscript>.*?</noscript>", "", panel, flags=re.S)


def _save(client, data, htmx=True):
    headers = {"HTTP_HX_REQUEST": "true"} if htmx else {}
    return client.post(reverse("accounts:download_preferences"), data, **headers)


def test_each_group_saves_only_its_own_field(member_client, member):
    from accounts.models import DownloadPreferences

    response = _save(member_client, {"resolution": "4K"})
    assert response.status_code == 200 and "Saved" in response.content.decode()
    _save(member_client, {"texture_format": "exr"})
    prefs = DownloadPreferences.objects.get(user=member)
    assert (prefs.resolution, prefs.texture_format) == ("4K", "exr")


def test_maps_save_as_ticked_and_at_least_one_is_needed(member_client, member):
    from accounts.models import DownloadPreferences

    _save(member_client, {"maps_posted": "1", "maps": ["rough", "color"]})
    assert DownloadPreferences.objects.get(user=member).maps == ["color", "rough"]
    response = _save(member_client, {"maps_posted": "1"})
    assert response.status_code == 400
    assert "Choose at least one map type." in response.content.decode()
    assert DownloadPreferences.objects.get(user=member).maps == ["color", "rough"]


@pytest.mark.parametrize(
    "data",
    [{"resolution": "3K"}, {"texture_format": "gif"}, {"maps_posted": "1", "maps": ["nope"]}, {}],
)
def test_bad_defaults_are_a_400_that_saves_nothing(member_client, data):
    from accounts.models import DownloadPreferences

    response = _save(member_client, data)
    assert response.status_code == 400
    assert not DownloadPreferences.objects.exists()


def test_a_plain_post_goes_back_to_settings(member_client):
    response = _save(member_client, {"resolution": "1K"}, htmx=False)
    assert response.status_code == 302 and response["Location"] == reverse("accounts:settings")


def test_defaults_need_sign_in_and_csrf(member, password):
    from accounts.models import DownloadPreferences

    visitor = Client()
    response = _save(visitor, {"resolution": "1K"}, htmx=False)
    assert response.status_code == 302
    assert response["Location"] == reverse("accounts:login") + "?next=/accounts/settings/"
    assert visitor.get(reverse("accounts:download_preferences")).status_code in (302, 405)
    strict = Client(enforce_csrf_checks=True)
    strict.force_login(member)
    assert _save(strict, {"resolution": "1K"}).status_code == 403
    assert not DownloadPreferences.objects.exists()


def test_one_members_defaults_never_change_anothers(member_client, member, django_user_model):
    from accounts.models import DownloadPreferences

    other = django_user_model.objects.create_user("other_member")
    DownloadPreferences.objects.create(user=other, resolution="8K")
    _save(member_client, {"resolution": "1K"})
    assert DownloadPreferences.objects.get(user=other).resolution == "8K"
    assert DownloadPreferences.objects.get(user=member).resolution == "1K"


# ---------------------------------------------------------------- the drawer's bundle


@pytest.fixture
def poly_entry(member, make_asset):
    from catalog.models import SavedAsset

    asset = make_asset(external_id=SLUG, title="Rusty Metal 02", variants=POLY_HAVEN)
    return SavedAsset.objects.create(user=member, asset=asset)


def _bundle_data(html):
    raw = re.search(
        r'<script id="entry-bundle-data" type="application/json">(.*?)</script>', html, re.S
    )
    return json.loads(raw.group(1)) if raw else None


def test_the_drawer_offers_the_bundle_its_defaults_pick(member_client, member, poly_entry):
    from accounts.models import DownloadPreferences

    DownloadPreferences.objects.create(user=member, resolution="2K", maps=["color", "rough"])
    html = member_client.get(
        reverse("catalog:entry", args=[poly_entry.pk]), HTTP_HX_REQUEST="true"
    ).content.decode()
    data = _bundle_data(html)
    assert data["zip_name"] == f"{SLUG}_2K_JPG.zip" and data["provider"] == "Poly Haven"
    assert [file["path"] for file in data["files"]] == [
        f"{SLUG}/{SLUG}_diff_2k.jpg",
        f"{SLUG}/{SLUG}_rough_2k.jpg",
    ]
    # Only the provider's URLs: the Toolbox never serves the files itself.
    assert all(file["url"].startswith("https://dl.polyhaven.org/") for file in data["files"])
    assert "License: CC0" in data["credits"] and "Rusty Metal 02" in data["credits"]
    assert 'data-bundle-download="entry-bundle-data"' in html
    assert "Defaults: 2K · JPG · 2 maps" in html
    assert html.count("Your default") == 1


def test_one_file_is_a_plain_link_with_no_zip(member_client, member, make_asset):
    from catalog.models import SavedAsset

    asset = make_asset(
        provider="ambientcg",
        external_id="Metal063",
        variants=[
            {
                "label": "1K JPG",
                "files": [
                    {
                        "url": "https://ambientcg.com/get?file=Metal063_1K-JPG.zip",
                        "filename": "Metal063_1K-JPG.zip",
                        "size": 5,
                    }
                ],
            },
            {
                "label": "2K JPG",
                "files": [
                    {
                        "url": "https://ambientcg.com/get?file=Metal063_2K-JPG.zip",
                        "filename": "Metal063_2K-JPG.zip",
                        "size": 9,
                    }
                ],
            },
        ],
    )
    entry = SavedAsset.objects.create(user=member, asset=asset)
    html = member_client.get(reverse("catalog:entry", args=[entry.pk])).content.decode()
    assert 'href="https://ambientcg.com/get?file=Metal063_2K-JPG.zip"' in html
    assert "Download Metal063_2K-JPG.zip" in html
    assert _bundle_data(html) is None


def test_the_file_filters_list_each_resolution_and_format(member_client, poly_entry):
    html = member_client.get(reverse("catalog:entry", args=[poly_entry.pk])).content.decode()
    filters = html.split("data-file-filters", 1)[1].split("</div>", 1)[0]
    assert re.findall(r'name="file-resolution" value="(\w*)"', filters) == ["", "1K", "2K", "4K"]
    assert re.findall(r'name="file-format" value="(\w*)"', filters) == [
        "",
        "jpg",
        "exr",
        "gltf",
        "png",
    ]
    assert re.findall(r'<li data-resolution="(\w+)" data-format="(\w+)">', html)[:3] == [
        ("1K", "jpg"),
        ("1K", "exr"),
        ("1K", "gltf"),
    ]


def test_the_browser_zip_never_goes_through_the_toolbox():
    from django.conf import settings

    script = (settings.BASE_DIR / "static" / "js" / "bundle-download.js").read_text(
        encoding="utf-8"
    )
    assert 'fetch(url, { mode: "cors", credentials: "omit"' in script
    assert "CREDITS.txt" in script and "MISSING.txt" in script
    assert "0x04034b50" in script and "0x02014b50" in script and "0x06054b50" in script
