"""Your packs as a grid or a list (user request, 2026-11-06)."""

import re

import pytest
from django.urls import reverse

from packs.models import Pack

pytestmark = pytest.mark.django_db


@pytest.fixture
def packs(member):
    return [
        Pack.objects.create_pack(member, "Forest Kit", "Trees and moss.", "nature, green"),
        Pack.objects.create_pack(member, "City Kit"),
    ]


def page(client, **params):
    return client.get(reverse("packs:list"), params).content.decode()


def test_packs_start_as_a_grid_with_the_switch(member_client, packs):
    html = page(member_client)
    assert '<ul id="pack-list" class="pack-grid" data-layout="grid"' in html
    switch = html.split('id="pack-layout"', 1)[1].split("</nav>", 1)[0]
    assert re.search(
        r'href="/packs/\?layout=grid" class="layout-option" aria-current="true"', switch
    )
    assert 'href="/packs/?layout=list" class="layout-option">' in switch


def test_the_list_shows_one_row_per_pack_with_the_same_facts(member_client, packs):
    html = page(member_client, layout="list")
    assert '<ul id="pack-list" class="pack-rows" data-layout="list"' in html
    rows = re.findall(r'<li class="pack-row">.*?</li>', html, re.S)
    assert len(rows) == 2
    forest = next(row for row in rows if "Forest Kit" in row)
    assert f'href="{reverse("packs:builder", args=[packs[0].pk])}" class="pack-card-link"' in forest
    assert "Trees and moss." in forest and "<span>nature</span>" in forest
    assert "0 items" in forest and "View page" in forest and "Private" in forest


def test_the_choice_is_remembered_and_bad_values_are_ignored(member_client, packs):
    page(member_client, layout="list")
    assert 'class="pack-rows"' in page(member_client)
    assert 'class="pack-rows"' in page(member_client, layout="tiles")
    page(member_client, layout="grid")
    assert 'class="pack-grid"' in page(member_client)


def test_item_thumbnails_sit_in_the_middle_of_their_rows():
    """Thumbnails (and the grip beside them) are centred in their rows, as in every
    other list with thumbnails (user reports, 2026-11-06)."""
    from django.conf import settings

    css = (settings.BASE_DIR / "styles" / "source.css").read_text(encoding="utf-8")
    assert ".pack-item-thumb, .pack-item-grip { align-self: center; }" in css
    assert ".lookup-item { align-items: center; }" in css
    assert ".pack-pick { display: flex; align-items: center;" in css
    assert ".pack-item .library-type { line-height: 1;" in css
    assert ".pack-item-actions { align-self: start; }" in css
    assert '.pack-item-status[data-save-status="idle"] { display: none; }' in css
    # The frame is drawn above the image, which used to cover it.
    assert ".pack-item-thumb::after, .lookup-thumb::after {" in css
    assert ".lookup-license { display: block; }" in css
