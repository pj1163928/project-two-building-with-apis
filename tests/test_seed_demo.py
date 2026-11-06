"""Demo data (Phase 9): seed_demo loads the committed snapshot offline, makes the
demo members, their libraries and packs, and is safe to run again.

The network guard is on, as in every test, and every provider function is
also replaced with one that fails, so the seed provably never asks a provider.
"""

from io import StringIO

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client
from django.urls import reverse

from providers import PROVIDERS

pytestmark = pytest.mark.django_db

SEEDED_APPS = ("auth", "authtoken", "accounts", "catalog", "packs")


@pytest.fixture(autouse=True)
def providers_down(monkeypatch):
    """Every provider call fails the test: the seed must use the snapshot only."""

    def refuse(*args, **kwargs):
        raise AssertionError("seed_demo asked a provider")

    for provider in PROVIDERS:
        for name in ("search", "get_details", "search_records", "fetch_record"):
            monkeypatch.setattr(provider, name, refuse)


def _row_counts():
    """Rows in every table the seed can touch, many-to-many tables included."""
    return {
        model._meta.db_table: model.objects.count()
        for model in apps.get_models(include_auto_created=True)
        if model._meta.app_label in SEEDED_APPS
    }


# ------------------------------------------------------------------ TDD: safe to run again


def test_running_seed_demo_twice_leaves_the_same_row_counts_as_once():
    """The second run adds nothing, under the network guard with every provider down."""
    from catalog.models import Asset, SavedAsset
    from packs.models import Pack, PackItem

    call_command("seed_demo", stdout=StringIO())
    once = _row_counts()
    assert get_user_model().objects.filter(username__startswith="demo_").count() == 3
    assert Asset.objects.count() == 43
    assert SavedAsset.objects.count() == 53
    assert Pack.objects.public().count() == 6
    assert PackItem.objects.count() > 40

    call_command("seed_demo", stdout=StringIO())
    assert _row_counts() == once


# ------------------------------------------------------------------ what it makes


@pytest.fixture
def seeded():
    call_command("seed_demo", stdout=StringIO())


def test_the_demo_members_sign_in_with_the_demo_password(seeded, client):
    from packs.demo import DEMO_PASSWORD, DEMO_USERS

    assert DEMO_USERS == ("demo_mira", "demo_otto", "demo_juno")
    assert DEMO_PASSWORD == "toolbox-demo"  # obviously a demo value
    for username in DEMO_USERS:
        assert client.login(username=username, password=DEMO_PASSWORD), username


def test_the_readme_lists_the_same_demo_credentials():
    from packs.demo import DEMO_PASSWORD, DEMO_USERS

    with open("README.md", encoding="utf-8") as handle:
        readme = handle.read()
    assert "uv run python manage.py seed_demo" in readme
    for username in DEMO_USERS:
        assert f"| `{username}` | `{DEMO_PASSWORD}` |" in readme


def test_the_seed_reports_what_it_made_and_then_nothing(capsys):
    first, second = StringIO(), StringIO()
    call_command("seed_demo", stdout=first)
    call_command("seed_demo", stdout=second)
    assert "Created 3 users, 43 assets, 53 library entries, 7 packs" in first.getvalue()
    assert "Created 0 users, 0 assets, 0 library entries, 0 packs and 0 pack items" in (
        second.getvalue()
    )
    assert "toolbox-demo" in second.getvalue()


def test_libraries_hold_every_status_and_a_range_of_ratings(seeded):
    from catalog.models import SavedAsset

    entries = SavedAsset.objects.filter(user__username__startswith="demo_")
    assert set(entries.values_list("status", flat=True)) == set(SavedAsset.Status.values)
    ratings = set(entries.values_list("rating", flat=True))
    assert None in ratings and {2, 3, 4, 5} <= ratings
    assert entries.exclude(notes="").count() >= 5
    # Several members rated the same asset, so community ratings show.
    shared = entries.filter(asset__external_id="cobblestone_floor_03")
    assert shared.exclude(rating=None).count() == 3
    # Each entry's first status is recorded, as a save on the website would.
    assert all(entry.status_changes.count() == 1 for entry in entries)


def test_the_packs_cover_every_type_and_license_need(seeded):
    from packs.models import Pack

    public = Pack.objects.public()
    assert sorted(public.values_list("title", flat=True)) == [
        "Bakery Props",
        "Desert Outpost",
        "Forest Ambience",
        "Golden Hour Skies",
        "Medieval Village",
        "Sci-fi Corridor",
    ]
    assert set(public.values_list("owner__username", flat=True)) == {
        "demo_mira",
        "demo_otto",
        "demo_juno",
    }
    private = Pack.objects.exclude(visibility="public")
    assert list(private.values_list("title", "visibility")) == [
        ("Castle Siege (work in progress)", "private")
    ]
    kinds = set(
        public.values_list("items__saved_asset__asset__kind", flat=True).exclude(
            items__saved_asset__asset__kind=None
        )
    )
    assert kinds == {"texture", "hdri", "model", "sound"}
    licenses = set(public.values_list("items__saved_asset__asset__license", flat=True))
    assert {"CC0", "CC BY 4.0", "CC BY-NC 4.0"} <= licenses


def test_each_pack_item_belongs_to_its_owners_library(seeded):
    from packs.models import PackItem

    for item in PackItem.objects.select_related("pack", "saved_asset"):
        assert item.saved_asset.user_id == item.pack.owner_id


def test_a_second_run_puts_a_changed_demo_pack_back(seeded):
    from packs.models import Pack

    pack = Pack.objects.get(title="Medieval Village")
    first = list(pack.ordered_items().values_list("saved_asset__asset__external_id", "import_path"))
    pack.set_visibility(Pack.Visibility.PRIVATE)
    pack.tags.clear()
    removed = pack.ordered_items().first()
    removed.delete()
    pack.ordered_items().update(import_path="elsewhere/")

    call_command("seed_demo", stdout=StringIO())

    pack.refresh_from_db()
    assert pack.is_public
    assert set(pack.tags.values_list("name", flat=True)) == {"medieval", "village", "stone", "wood"}
    assert (
        list(pack.ordered_items().values_list("saved_asset__asset__external_id", "import_path"))
        == first
    )


def test_a_member_s_own_changes_to_an_entry_are_kept(seeded):
    from catalog.models import SavedAsset

    entry = SavedAsset.objects.get(
        user__username="demo_otto", asset__external_id="forest_ground_04"
    )
    entry.notes = "my own note"
    entry.save()
    call_command("seed_demo", stdout=StringIO())
    entry.refresh_from_db()
    assert entry.notes == "my own note"


def test_a_snapshot_missing_an_asset_writes_nothing():
    from packs.demo import load_snapshot, seed_demo

    snapshot = load_snapshot()
    snapshot.pop(("polyhaven", "goegap"))
    before = _row_counts()
    with pytest.raises(ValueError, match="polyhaven goegap.*capture_demo_assets"):
        seed_demo(snapshot)
    assert _row_counts() == before


def test_the_snapshot_holds_about_forty_real_assets_of_every_type():
    from packs.demo import demo_asset_refs, load_snapshot

    snapshot = load_snapshot()
    assert set(snapshot) == set(demo_asset_refs())
    assert 36 <= len(snapshot) <= 48
    assert {record.kind for record in snapshot.values()} == {"texture", "hdri", "model", "sound"}
    for record in snapshot.values():
        assert record.source_url.startswith("https://")
        assert record.variants, f"{record.external_id} has no files"


# ------------------------------------------------------------------ the capture script


def test_capture_writes_every_demo_asset_and_nothing_on_a_failure(monkeypatch, tmp_path):
    """Run with fake providers: it writes the snapshot only when every fetch worked."""
    from packs import demo
    from packs.management.commands import capture_demo_assets
    from providers import ProviderError

    snapshot = demo.load_snapshot()
    target = tmp_path / "snapshot.json"
    monkeypatch.setattr(capture_demo_assets, "PAUSE_SECONDS", {})
    monkeypatch.setattr(
        capture_demo_assets,
        "write_snapshot",
        lambda records: demo.write_snapshot(records, target),
    )
    for provider in PROVIDERS:
        monkeypatch.setattr(
            provider,
            "fetch_record",
            lambda external_id, key=provider.KEY: snapshot[(key, external_id)],
        )
    call_command("capture_demo_assets", stdout=StringIO())
    assert demo.load_snapshot(target) == snapshot

    target.unlink()

    def fail(external_id):
        raise ProviderError("Poly Haven is down.")

    monkeypatch.setattr(PROVIDERS[1], "fetch_record", fail)
    from django.core.management.base import CommandError

    with pytest.raises(CommandError, match="Nothing written"):
        call_command("capture_demo_assets", stdout=StringIO())
    assert not target.exists()


# ------------------------------------------------------------------ Tier 1, offline


@pytest.fixture
def providers_failing(monkeypatch):
    """Every provider down with the friendly error a real outage gives."""
    from providers import ProviderError

    def down(*args, **kwargs):
        raise ProviderError("The provider is unavailable right now. Try again later.")

    for provider in PROVIDERS:
        for name in ("search_records", "fetch_record"):
            monkeypatch.setattr(provider, name, down)


def test_every_tier_1_feature_works_on_the_seeded_data_offline(seeded, providers_failing, client):
    """With every provider down, only Discover's shelves show their error alerts."""
    from rest_framework.authtoken.models import Token

    from catalog.models import SavedAsset
    from packs.demo import DEMO_PASSWORD
    from packs.models import Pack

    mira_entry = SavedAsset.objects.filter(user__username="demo_mira").first()
    medieval = Pack.objects.get(title="Medieval Village")
    private = Pack.objects.get(title="Castle Siege (work in progress)")

    # Visitors: the main page with the gallery, a public pack page, its export.
    home = client.get("/").content.decode()
    assert home.count('class="gallery-card"') == 6
    assert client.get(medieval.get_public_url()).status_code == 200
    assert client.get(reverse("packs:export", args=[medieval.slug])).status_code == 200
    assert client.get(private.get_public_url()).status_code == 404

    # Discover renders; each shelf shows its alert and Retry, never a crash.
    assert client.get(reverse("catalog:discover"), {"q": "brick"}).status_code == 200
    shelf = client.get(
        reverse("catalog:discover_shelf", args=["texture", "polyhaven"]),
        {"q": "brick"},
        headers={"HX-Request": "true"},
    ).content.decode()
    assert "alert" in shelf and "Retry" in shelf

    # Members: the library, filters, an entry, its update, packs, the builder.
    assert client.login(username="demo_mira", password=DEMO_PASSWORD)
    library = client.get(reverse("catalog:library"), {"status": "approved", "sort": "rating"})
    assert library.status_code == 200 and "result-card library-card" in library.content.decode()
    assert client.get(reverse("catalog:entry", args=[mira_entry.pk])).status_code == 200
    update = client.post(reverse("catalog:update", args=[mira_entry.pk]), {"rating": "4"})
    assert update.status_code in (200, 302)
    assert client.get(reverse("packs:list")).status_code == 200
    assert client.get(reverse("packs:builder", args=[medieval.pk])).status_code == 200
    assert client.get(private.get_public_url()).status_code == 200  # the owner's own
    assert client.get(reverse("accounts:token")).status_code == 200

    # The API, signed with the token page's token.
    token = Token.objects.get(user__username="demo_mira").key
    api = Client(headers={"Authorization": f"Token {token}"})
    listing = api.get(reverse("catalog:api_library"), {"type": "sound"}).json()
    assert listing["count"] > 0
    assert api.get(reverse("catalog:api_entry", args=[mira_entry.pk])).status_code == 200
    assert api.get(reverse("packs:api_packs")).json()["count"] == 7  # 6 public + her private
    assert api.get(reverse("packs:api_pack_export", args=[medieval.pk])).status_code == 200

    # Another member never sees Mira's private pack or her entries.
    assert client.login(username="demo_otto", password=DEMO_PASSWORD)
    assert client.get(private.get_public_url()).status_code == 404
    assert client.get(reverse("catalog:entry", args=[mira_entry.pk])).status_code == 404
