"""Sounds play outside Discover too (user request, 2026-11-06): on library cards,
in the library drawer, and on pack items in the builder and on a pack's page.

The audio is the sound's first stored file (Asset.preview_url), the provider's
URL, streamed by static/js/sound-preview.js and never copied.
"""

import re

import pytest
from django.conf import settings
from django.urls import reverse

from catalog.models import SavedAsset
from packs.models import Pack
from packs.services import add_to_pack

pytestmark = pytest.mark.django_db

AUDIO = "https://cdn.freesound.org/previews/rain.mp3"
SOUND_VARIANTS = [
    {"label": "MP3", "files": [{"url": AUDIO, "filename": "rain.mp3", "size": 1000}]},
    {
        "label": "WAV",
        "files": [{"url": "https://cdn.example/rain.wav", "filename": "rain.wav", "size": 9}],
    },
]


@pytest.fixture
def sound(make_asset):
    return make_asset(
        provider="openverse",
        external_id="rain-1",
        kind="sound",
        title="Rain",
        variants=SOUND_VARIANTS,
    )


@pytest.fixture
def pack(member, sound):
    pack = Pack.objects.create_pack(member, "Weather Kit")
    add_to_pack(pack, SavedAsset.objects.create(user=member, asset=sound))
    return pack


def test_a_sounds_preview_is_its_first_stored_file(sound, make_asset):
    assert sound.preview_url == AUDIO
    assert make_asset(external_id="brick", variants=SOUND_VARIANTS).preview_url == ""  # a texture
    assert make_asset(provider="openverse", external_id="x", kind="sound").preview_url == ""


def play_button(html):
    return re.search(r'<button type="button" class="sound-play[^"]*"[^>]*>', html).group(0)


def test_a_library_card_plays_its_sound(member_client, pack):
    html = member_client.get(reverse("catalog:library")).content.decode()
    card = re.search(
        r'<li class="result-card library-card"[^>]*data-sound-card.*?</li>', html, re.S
    )
    assert card, "the sound's card takes the playing state"
    button = play_button(card.group(0))
    assert f'data-sound-preview="{AUDIO}"' in button
    assert 'aria-label="Play a preview of Rain"' in button


def test_the_library_drawer_plays_its_sound(member_client, member, pack):
    entry = SavedAsset.objects.get(user=member)
    html = member_client.get(
        reverse("catalog:entry", args=[entry.pk]), headers={"HX-Request": "true"}
    ).content.decode()
    assert re.search(r'<article class="entry" data-kind="sound" data-sound-card', html)
    assert f'data-sound-preview="{AUDIO}"' in html


def test_the_builder_and_the_pack_page_play_each_sound(member_client, pack):
    for url in (reverse("packs:builder", args=[pack.pk]), pack.reader_url):
        html = member_client.get(url).content.decode()
        item = re.search(r'<li class="pack-item[^"]*" [^>]*data-sound-card.*?</li>', html, re.S)
        assert item, url
        button = play_button(item.group(0))
        assert "sound-play is-small" in button and f'data-sound-preview="{AUDIO}"' in button


def test_items_without_audio_get_no_button(member_client, member, make_asset):
    pack = Pack.objects.create_pack(member, "Bricks")
    add_to_pack(pack, SavedAsset.objects.create(user=member, asset=make_asset()))
    html = member_client.get(pack.reader_url).content.decode()
    assert "data-sound-preview" not in html and "data-sound-card" not in html


def test_the_player_follows_any_sound_card():
    script = (settings.BASE_DIR / "static" / "js" / "sound-preview.js").read_text(encoding="utf-8")
    assert 'button.closest("[data-sound-card]")' in script
    # A drawer that closes stops its sound.
    assert 'document.addEventListener("close"' in script
    css = (settings.BASE_DIR / "styles" / "source.css").read_text(encoding="utf-8")
    assert '[data-sound-card][data-sound="playing"] .when-playing' in css
    assert ".result-card[data-sound=" not in css
