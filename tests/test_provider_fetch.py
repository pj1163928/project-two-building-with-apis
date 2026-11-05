"""fetch_record(): one asset's full details, with its download variants.

Provider client tests, so the HTTP is faked with `responses`. Each provider
fills every AssetRecord field (variants included), keeps the provider's file
URLs, and turns an unknown ID or a malformed answer into a safe ProviderError.
"""

import pytest
from responses import matchers

from providers import ProviderError, ambientcg, openverse, polyhaven
from providers.records import Variant, VariantFile

from .test_provider_records import CC0_URL, assert_every_field_filled

# ---------------------------------------------------------------- ambientCG

ACG_DETAIL = {
    "id": "Bricks097",
    "title": "Bricks 097",
    "type": "material",
    "url": "https://ambientcg.com/a/Bricks097",
    "tags": ["Brick", "Bricks", "brown"],
    "thumbnails": {"256-PNG": "https://acg-media.example/256-PNG/Bricks097.png"},
    "downloads": [
        {
            "attributes": "1K-JPG",
            "extension": "zip",
            "size": 5172084,
            "url": "https://ambientcg.com/get?file=Bricks097_1K-JPG.zip",
        },
        {
            "attributes": "2K-JPG",
            "extension": "zip",
            "size": 17000000,
            "url": "https://ambientcg.com/get?file=Bricks097_2K-JPG.zip",
        },
        {"attributes": "4K-PNG", "extension": "zip", "url": "https://ambientcg.com/get?x=1"},
        {"attributes": "8K-JPG", "size": 1},  # no URL: nothing to download, so skipped
        "not-a-download",
    ],
}


def test_ambientcg_fetch_record_asks_for_the_downloads(mocked_responses):
    mocked_responses.get(
        ambientcg.API_URL,
        match=[
            matchers.query_param_matcher(
                {"id": "Bricks097", "include": "title,url,tags,type,thumbnails,downloads"}
            )
        ],
        json={"assets": [ACG_DETAIL]},
    )
    record = ambientcg.fetch_record("  Bricks097 ")
    assert_every_field_filled(record, with_variants=True)
    assert (record.provider, record.external_id, record.kind) == (
        "ambientcg",
        "Bricks097",
        "texture",
    )
    assert record.title == "Bricks 097"
    assert record.license_url == CC0_URL
    assert record.tags == ("Brick", "Bricks", "brown")  # normalized later, by the Toolbox


def test_ambientcg_fetch_record_makes_one_variant_per_download(mocked_responses):
    mocked_responses.get(ambientcg.API_URL, json={"assets": [ACG_DETAIL]})
    record = ambientcg.fetch_record("Bricks097")
    assert record.variants == (
        Variant(
            "1K JPG",
            (
                VariantFile(
                    "https://ambientcg.com/get?file=Bricks097_1K-JPG.zip",
                    "Bricks097_1K-JPG.zip",
                    5172084,
                ),
            ),
        ),
        Variant(
            "2K JPG",
            (
                VariantFile(
                    "https://ambientcg.com/get?file=Bricks097_2K-JPG.zip",
                    "Bricks097_2K-JPG.zip",
                    17000000,
                ),
            ),
        ),
        # No file name in the URL and no size: the name is built, the size stays unknown.
        Variant(
            "4K PNG",
            (VariantFile("https://ambientcg.com/get?x=1", "Bricks097_4K-PNG.zip", None),),
        ),
    )
    assert record.variants[1].total_size == 17000000
    assert record.variants[2].total_size is None


@pytest.mark.parametrize(("acg_type", "kind"), [("hdri", "hdri"), ("3d-model", "model")])
def test_ambientcg_fetch_record_maps_the_type_to_a_kind(mocked_responses, acg_type, kind):
    mocked_responses.get(ambientcg.API_URL, json={"assets": [{**ACG_DETAIL, "type": acg_type}]})
    assert ambientcg.fetch_record("Bricks097").kind == kind


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ({"assets": []}, "ambientCG has no asset with that ID."),
        (
            {"assets": [{**ACG_DETAIL, "type": "decal"}]},
            "ambientCG sent back an asset the Toolbox can't save.",
        ),
        ({"assets": "nope"}, "ambientCG sent back results the Toolbox couldn't read."),
    ],
    ids=["unknown-id", "unsaveable-type", "malformed"],
)
def test_ambientcg_fetch_record_refuses_with_a_safe_message(mocked_responses, body, message):
    mocked_responses.get(ambientcg.API_URL, json=body)
    with pytest.raises(ProviderError) as caught:
        ambientcg.fetch_record("Bricks097")
    assert str(caught.value) == message


# ---------------------------------------------------------------- Poly Haven

PH_INFO = {
    "name": "Red Brick 03",
    "type": 1,
    "authors": {"Rob Tuytel": "All"},
    "tags": ["red", "Industrial"],
    "thumbnail_url": "https://cdn.polyhaven.com/asset_img/thumbs/red_brick_03.png",
}

PH_FILES = {
    "Diffuse": {
        "1k": {"jpg": {"size": 100, "url": "https://dl.polyhaven.org/d_1k.jpg"}},
        "2k": {
            "jpg": {"size": 400, "url": "https://dl.polyhaven.org/d_2k.jpg"},
            "png": {"size": 900, "url": "https://dl.polyhaven.org/d_2k.png"},
        },
    },
    "nor_gl": {"2k": {"jpg": {"size": 300, "url": "https://dl.polyhaven.org/n_2k.jpg"}}},
    "gltf": {
        "2k": {
            "gltf": {
                "size": 50,
                "url": "https://dl.polyhaven.org/red_brick_03_2k.gltf",
                "include": {
                    "textures/d_2k.jpg": {"size": 400, "url": "https://dl.polyhaven.org/d_2k.jpg"},
                    "textures/n_2k.jpg": {"size": 300, "url": "https://dl.polyhaven.org/n_2k.jpg"},
                },
            }
        }
    },
    "Rough": {"16k": {"jpg": {"size": 9000, "url": "https://dl.polyhaven.org/r_16k.jpg"}}},
    "thumbnail": "not-a-dict-entry",
    "Broken": {"2k": {"jpg": {"size": 5}}, "notes": {"jpg": {"url": "https://x/y.jpg"}}},
}


def mock_polyhaven(mocked_responses, info=PH_INFO, files=PH_FILES):
    mocked_responses.get(f"{polyhaven.API_URL}/info/red_brick_03", json=info)
    mocked_responses.get(f"{polyhaven.API_URL}/files/red_brick_03", json=files)


def test_polyhaven_fetch_record_fills_every_field(mocked_responses):
    mock_polyhaven(mocked_responses)
    record = polyhaven.fetch_record("red_brick_03")
    assert_every_field_filled(record, with_variants=True)
    assert (record.provider, record.external_id, record.kind) == (
        "polyhaven",
        "red_brick_03",
        "texture",
    )
    assert record.author == "Rob Tuytel"
    assert record.source_url == "https://polyhaven.com/a/red_brick_03"


def test_polyhaven_fetch_record_keeps_every_file_url(mocked_responses):
    """The console's get_details() only totals sizes; fetch_record() keeps the URLs."""
    mock_polyhaven(mocked_responses)
    record = polyhaven.fetch_record("red_brick_03")
    assert record.variants == (
        Variant("1K JPG", (VariantFile("https://dl.polyhaven.org/d_1k.jpg", "d_1k.jpg", 100),)),
        # Loose maps of one resolution and format share a variant...
        Variant(
            "2K JPG",
            (
                VariantFile("https://dl.polyhaven.org/d_2k.jpg", "d_2k.jpg", 400),
                VariantFile("https://dl.polyhaven.org/n_2k.jpg", "n_2k.jpg", 300),
            ),
        ),
        Variant("2K PNG", (VariantFile("https://dl.polyhaven.org/d_2k.png", "d_2k.png", 900),)),
        # ...a bundle is the bundle file plus everything it includes, by relative path...
        Variant(
            "2K glTF",
            (
                VariantFile(
                    "https://dl.polyhaven.org/red_brick_03_2k.gltf", "red_brick_03_2k.gltf", 50
                ),
                VariantFile("https://dl.polyhaven.org/d_2k.jpg", "textures/d_2k.jpg", 400),
                VariantFile("https://dl.polyhaven.org/n_2k.jpg", "textures/n_2k.jpg", 300),
            ),
        ),
        # ...and resolutions sort as numbers, so 16K comes after 2K.
        Variant("16K JPG", (VariantFile("https://dl.polyhaven.org/r_16k.jpg", "r_16k.jpg", 9000),)),
    )
    assert record.variants[1].total_size == 700
    assert record.variants[3].total_size == 750


def test_polyhaven_fetch_record_reuses_the_cached_info(mocked_responses):
    """/info is cached for 12 hours wherever it's fetched; /files is fetched each time."""
    mock_polyhaven(mocked_responses)
    mocked_responses.get(f"{polyhaven.API_URL}/files/red_brick_03", json=PH_FILES)
    polyhaven.fetch_record("red_brick_03")
    polyhaven.fetch_record("red_brick_03")
    urls = [call.request.url for call in mocked_responses.calls]
    assert urls.count(f"{polyhaven.API_URL}/info/red_brick_03") == 1
    assert urls.count(f"{polyhaven.API_URL}/files/red_brick_03") == 2


@pytest.mark.parametrize(("ph_type", "kind"), [(0, "hdri"), (2, "model")])
def test_polyhaven_fetch_record_maps_the_type_to_a_kind(mocked_responses, ph_type, kind):
    mock_polyhaven(mocked_responses, info={**PH_INFO, "type": ph_type})
    assert polyhaven.fetch_record("red_brick_03").kind == kind


def test_polyhaven_fetch_record_hdri_variants_use_hdr_and_exr(mocked_responses):
    files = {
        "hdri": {
            "1k": {
                "hdr": {"size": 1500, "url": "https://dl.polyhaven.org/sky_1k.hdr"},
                "exr": {"size": 2500, "url": "https://dl.polyhaven.org/sky_1k.exr"},
            }
        },
        "tonemapped": {"size": 10, "url": "https://dl.polyhaven.org/sky.jpg"},
    }
    mock_polyhaven(mocked_responses, info={**PH_INFO, "type": 0}, files=files)
    labels = [variant.label for variant in polyhaven.fetch_record("red_brick_03").variants]
    assert labels == ["1K EXR", "1K HDR"]


@pytest.mark.parametrize(
    ("info", "files"),
    [({**PH_INFO, "type": 7}, PH_FILES), (["not", "a", "dict"], PH_FILES), (PH_INFO, ["nope"])],
    ids=["unknown-type", "malformed-info", "malformed-files"],
)
def test_polyhaven_fetch_record_refuses_a_malformed_answer(mocked_responses, info, files):
    mock_polyhaven(mocked_responses, info=info, files=files)
    with pytest.raises(ProviderError) as caught:
        polyhaven.fetch_record("red_brick_03")
    assert str(caught.value) == "Poly Haven sent back results the Toolbox couldn't read."


def test_polyhaven_fetch_record_unknown_slug_is_a_friendly_404(mocked_responses):
    mocked_responses.get(
        f"{polyhaven.API_URL}/info/nope", status=404, body="<html>Not found</html>"
    )
    with pytest.raises(ProviderError) as caught:
        polyhaven.fetch_record("nope")
    assert "HTTP 404" in str(caught.value)
    assert "<html>" not in str(caught.value)


@pytest.mark.parametrize("bad_id", ["../files/x", "a b", "", "slug?x=1"])
def test_polyhaven_fetch_record_refuses_an_id_that_isnt_a_slug_without_a_request(
    mocked_responses, bad_id
):
    with pytest.raises(ProviderError) as caught:
        polyhaven.fetch_record(bad_id)
    assert str(caught.value) == "Poly Haven has no asset with that ID."
    assert not mocked_responses.calls


# ---------------------------------------------------------------- Openverse

OV_ID = "a8783d20-f1af-4c4b-b9ec-a8c212f67fee"
OV_DETAIL = {
    "id": OV_ID,
    "title": "Footsteps, Stones, A.wav",
    "creator": "InspectorJ",
    "license": "by",
    "license_version": "4.0",
    "license_url": "https://creativecommons.org/licenses/by/4.0/",
    "attribution": '"Footsteps, Stones, A.wav" by InspectorJ is licensed under CC BY 4.0.',
    "foreign_landing_url": "https://freesound.org/s/345560/",
    "thumbnail": f"https://api.openverse.org/v1/audio/{OV_ID}/thumb/",
    "url": "https://cdn.freesound.org/previews/345/345560_5121236-hq.mp3",
    "filetype": "mp3",
    "filesize": 300000,
    "tags": [{"name": "footsteps"}],
    "alt_files": [
        {
            "url": "https://freesound.org/apiv2/sounds/345560/download",
            "filetype": "wav",
            "filesize": None,
        },
        {"url": "https://cdn.freesound.org/other.mp3", "filetype": "mp3", "filesize": 1},
        {"filetype": "ogg"},
        "not-a-file",
    ],
}


def test_openverse_fetch_record_fills_every_field(mocked_responses):
    mocked_responses.get(f"{openverse.API_URL}{OV_ID}/", json=OV_DETAIL)
    record = openverse.fetch_record(OV_ID)
    assert_every_field_filled(record, with_variants=True)
    assert (record.provider, record.external_id, record.kind) == ("openverse", OV_ID, "sound")
    assert record.license == "CC BY 4.0"
    assert record.attribution == OV_DETAIL["attribution"]


def test_openverse_fetch_record_lists_the_main_file_then_each_other_type(mocked_responses):
    mocked_responses.get(f"{openverse.API_URL}{OV_ID}/", json=OV_DETAIL)
    record = openverse.fetch_record(OV_ID)
    assert record.variants == (
        Variant("MP3", (VariantFile(OV_DETAIL["url"], "345560_5121236-hq.mp3", 300000),)),
        # A URL with no file name is named from the ID and type, a missing size stays
        # unknown, and a second MP3 doesn't replace the main one.
        Variant(
            "WAV",
            (
                VariantFile(
                    "https://freesound.org/apiv2/sounds/345560/download", f"{OV_ID}.wav", None
                ),
            ),
        ),
    )


def test_openverse_fetch_record_unknown_id_is_a_friendly_404(mocked_responses):
    mocked_responses.get(f"{openverse.API_URL}{OV_ID}/", status=404, json={"detail": "Not found."})
    with pytest.raises(ProviderError) as caught:
        openverse.fetch_record(OV_ID)
    assert "HTTP 404" in str(caught.value)


@pytest.mark.parametrize("bad_id", ["../images", "a/b", ""])
def test_openverse_fetch_record_refuses_an_id_that_isnt_an_id_without_a_request(
    mocked_responses, bad_id
):
    with pytest.raises(ProviderError) as caught:
        openverse.fetch_record(bad_id)
    assert str(caught.value) == "Openverse Audio has no sound with that ID."
    assert not mocked_responses.calls
