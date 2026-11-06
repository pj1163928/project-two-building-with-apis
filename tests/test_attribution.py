"""Licenses, a pack's credits and the Attribution center (user request, 2026-11-05).

catalog.licenses reads each license as the providers write it; packs.credits
groups a pack's items by license, with the lines to paste; the pack page shows
a summary; the Attribution center's pages are the guide (everyone), each pack's
attribution (the pack page's reader rule) and a member's own packs and assets,
filtered by license type and credit rule. App tests: no provider is ever called.
"""

import re
from html import unescape

import pytest
from django.conf import settings
from django.test import Client
from django.urls import reverse

from catalog.licenses import LICENSE_ORDER, LICENSES, license_info, license_key
from catalog.models import SavedAsset
from packs.credits import pack_credits, pack_notice
from packs.manifest import build_manifest
from packs.models import Pack
from packs.services import add_to_pack
from tests import test_pack_public

pytestmark = pytest.mark.django_db

# The golden pack and a second member, shared with test_pack_public.py.
golden_pack = test_pack_public.golden_pack
other = test_pack_public.other

HTMX = {"HX-Request": "true"}


def _text(html):
    return " ".join(re.sub(r"<[^>]+>", " ", html).split())


# ---------------------------------------------------------------- reading a license


@pytest.mark.parametrize(
    ("written", "key"),
    [
        ("CC0 1.0", "cc0"),
        ("CC0", "cc0"),
        ("cc0 1.0", "cc0"),
        ("Public Domain Mark", "pdm"),
        ("CC BY 4.0", "by"),
        ("CC BY-SA 3.0", "by-sa"),
        ("CC BY-ND 4.0", "by-nd"),
        ("CC BY-NC 3.0", "by-nc"),
        ("CC BY-NC-SA 4.0", "by-nc-sa"),
        ("CC BY-NC-ND 2.5", "by-nc-nd"),
        ("CC SAMPLING+ 1.0", "sampling+"),
        ("CC NC-SAMPLING+ 1.0", "nc-sampling+"),
        ("cc-by-4.0", "by"),
        ("  CC   BY  ", "by"),
        ("unknown", "unknown"),
        ("", "unknown"),
        ("Some Store License", "unknown"),
    ],
)
def test_license_key_reads_each_license_as_providers_write_it(written, key):
    assert license_key(written) == key
    assert license_info(written) is LICENSES[key]


def test_each_license_says_what_it_allows_and_asks():
    assert set(LICENSE_ORDER) == set(LICENSES)
    for info in LICENSES.values():
        assert info.summary and info.steps and info.credit_label
        assert info.anchor.startswith("license-") and "+" not in info.anchor
    assert not LICENSES["cc0"].needs_credit and LICENSES["cc0"].commercial
    assert LICENSES["by"].needs_credit and LICENSES["by"].commercial and LICENSES["by"].changes
    assert LICENSES["by-nc"].commercial is False
    assert LICENSES["by-nd"].changes is False
    assert LICENSES["by-sa"].share_alike and LICENSES["by-nc-sa"].share_alike
    assert LICENSES["sampling+"].commercial is None


# ---------------------------------------------------------------- a pack's credits


def test_pack_credits_group_items_by_license_and_match_the_manifest(golden_pack):
    items = list(golden_pack.ordered_items())
    credits = pack_credits(items)
    # Those needing credit first, each license in the order it first appears.
    assert [group.label for group in credits.groups] == ["CC BY 4.0", "CC BY-SA 3.0", "CC0"]
    assert [len(group.items) for group in credits.groups] == [2, 1, 2]
    assert credits.needing_credit == 3
    # The required lines are exactly the manifest's credits.
    manifest = build_manifest(golden_pack, source_url="http://testserver/")
    assert credits.required == manifest["credits"]
    # Optional thank-yous for the CC0 items, which owe nothing.
    assert credits.optional == [
        '"Red Brick 03" by Rob Tuytel, from polyhaven.com (CC0)',
        '"Market Crate" by ambientCG, from ambientcg.com (CC0)',
    ]
    assert credits.warnings == [
        "1 item is share-alike (SA): a changed version must be shared under the same license."
    ]


def test_pack_credits_warn_about_noncommercial_no_changes_and_unknown(member, make_asset):
    pack = Pack.objects.create_pack(member, "Careful")
    for index, license in enumerate(["CC BY-NC-ND 4.0", "CC BY-NC 4.0", "unknown"]):
        asset = make_asset(external_id=f"a{index}", license=license, attribution="")
        add_to_pack(pack, SavedAsset.objects.create(user=member, asset=asset))
    warnings = pack_credits(list(pack.ordered_items())).warnings
    assert warnings[0].startswith("1 item has no known license.")
    assert warnings[1].startswith("2 items are non-commercial (NC)")
    assert warnings[2].startswith("1 item must be used unchanged (ND)")


def test_each_license_states_what_anyone_may_must_and_may_not_do():
    by, nc, nd, cc0 = (LICENSES[key] for key in ("by", "by-nc", "by-nd", "cc0"))
    assert any("commercially" in term for term in by.permits)
    assert any("credit" in term for term in by.requires)
    assert not any("commercially" in term for term in by.prohibits)
    assert any(term.startswith("Use it commercially") for term in nc.prohibits)
    assert any(term.startswith("Share an adapted version") for term in nd.prohibits)
    assert not any("changed" in term for term in nd.requires)  # nothing to state
    assert cc0.requires == () and len(cc0.prohibits) == 1  # only endorsement
    assert LICENSES["unknown"].permits == ()
    for info in LICENSES.values():
        assert info.prohibits, info.key


def _notice(pack):
    credits = pack_credits(list(pack.ordered_items()))
    return credits, pack_notice(pack, credits, "http://testserver/packs/medieval-village/")


def test_the_notice_is_formal_and_complete(golden_pack):
    credits, text = _notice(golden_pack)
    assert text.startswith("ATTRIBUTION AND LICENSE NOTICE\n")
    assert 'Covers:       the pack "Medieval Village"' in text
    assert "Compiled by:  demo_member, with Axcenity Toolbox" in text
    assert "Source:       http://testserver/packs/medieval-village/" in text
    assert "They are not owned by" in text
    sections = [
        "1. REQUIRED ATTRIBUTION",
        "2. LICENSE TERMS",
        "3. PERMITTED USES",
        "4. RESTRICTIONS IN FORCE",
        "5. OPTIONAL ACKNOWLEDGEMENTS",
        "6. DISCLAIMER",
    ]
    places = [text.index(section) for section in sections]
    assert places == sorted(places)
    # Every required credit sits in section 1, exactly the manifest's.
    for line in credits.required:
        assert places[0] < text.index(line) < places[1]
    # Each license: what it covers, then you may, you must, you may not.
    terms = text[places[1] : places[2]]
    assert "2.1 CC BY 4.0 (Attribution)" in terms
    assert 'Applies to: "Forest Birds"; "Forest Birds (loop)"' in terms
    assert "2.3 CC0 (Public domain dedication)" in terms
    block = terms.split("2.1 ", 1)[1].split("2.2 ", 1)[0]
    assert block.index("You may:") < block.index("You must:") < block.index("You may not:")
    assert "not legal advice" in text and '"as is"' in text
    assert all(len(line) <= 78 for line in text.splitlines())


def test_an_all_cc0_notice_says_no_attribution_is_required(member, make_asset):
    pack = Pack.objects.create_pack(member, "Free")
    add_to_pack(pack, SavedAsset.objects.create(user=member, asset=make_asset()))
    credits = pack_credits(list(pack.ordered_items()))
    assert credits.required == [] and credits.warnings == [] and credits.needing_credit == 0
    text = pack_notice(pack, credits)
    assert "1. REQUIRED ATTRIBUTION\n   None." in text and "RESTRICTIONS IN FORCE" not in text
    assert credits.credit_lines().startswith("No credit is required")


def test_the_credit_lines_are_the_required_then_the_optional(golden_pack):
    credits = pack_credits(list(golden_pack.ordered_items()))
    lines = credits.credit_lines().splitlines()
    assert (
        lines[0] == "Required credits:" and lines[1 : 1 + len(credits.required)] == credits.required
    )
    assert "Optional acknowledgements:" in lines and lines[-1] == credits.optional[-1]


# ---------------------------------------------------------------- the pack page's summary


def test_the_pack_page_summarises_the_licenses_and_links_to_the_full_attribution(
    client, golden_pack
):
    html = client.get(reverse("packs:public", args=[golden_pack.slug])).content.decode()
    credits = html.split('id="pack-page-credits"', 1)[1].split("</section>", 1)[0]
    text = _text(credits)
    assert "Credits and licenses" in text and "3 items need credit in your game." in text
    assert "Credit required" in text and "Credit optional" in text and "share-alike (SA)" in text
    full = reverse("packs:attribution_pack", args=[golden_pack.slug])
    assert f'href="{full}"' in credits and "Full attribution and license notice" in text
    guide = reverse("packs:attribution")
    assert f'href="{guide}#license-by"' in html and f'href="{guide}#license-cc0"' in html
    assert 'id="import-path-help"' in html and "What's an import path?" in html


# ---------------------------------------------------------------- the guide


def test_a_visitor_reads_the_guide_and_is_asked_to_sign_in(client):
    response = client.get(reverse("packs:attribution"))
    assert response.status_code == 200
    html = response.content.decode()
    for info in LICENSES.values():
        assert f'id="{info.anchor}"' in html
    text = _text(html)
    assert "You may" in text and "You must" in text and "You may not" in text
    assert "to see the licenses in your packs" in text
    # Only the guide in the side panel: the other pages are a member's.
    assert reverse("packs:attribution_packs") not in html
    assert reverse("packs:attribution_assets") not in html
    assert re.search(r'aria-label="Attribution" class="act act-row"\s*aria-current="page"', html)


def test_the_guide_links_a_member_to_their_pack_and_asset_pages(member_client):
    html = member_client.get(reverse("packs:attribution")).content.decode()
    assert f'href="{reverse("packs:attribution_packs")}"' in html
    assert f'href="{reverse("packs:attribution_assets")}"' in html
    assert re.search(r'class="panel-row" href="/attribution/" aria-current="page"', html)


# ---------------------------------------------------------------- pack attribution


def test_pack_attribution_lists_only_the_members_own_packs(
    member_client, golden_pack, other, make_asset
):
    theirs = Pack.objects.create_pack(other, "Their Secret Pack")
    asset = make_asset(external_id="theirs", license="CC BY-NC 4.0", title="Secret Thing")
    add_to_pack(theirs, SavedAsset.objects.create(user=other, asset=asset))
    html = member_client.get(reverse("packs:attribution_packs")).content.decode()
    packs = html.split('id="attribution-packs"', 1)[1].split("</ul>\n    {% else", 1)[0]
    assert "Medieval Village" in packs and "Their Secret Pack" not in html
    assert "Secret Thing" not in html
    assert "CC BY 4.0" in packs and "×2" in packs and "3 items need credit" in _text(packs)
    assert reverse("packs:attribution_pack", args=[golden_pack.slug]) in packs


def test_a_packs_attribution_sets_out_terms_credits_and_the_notice(client, golden_pack):
    url = reverse("packs:attribution_pack", args=[golden_pack.slug])
    html = client.get(url).content.decode()
    text = unescape(_text(html))
    assert "Compiled by demo_member · 5 items · 3 licenses" in text
    assert "Restrictions in force" in text and "share-alike (SA)" in text
    assert html.count('data-terms="prohibits"') == 3  # one block per license
    assert '"Creaking Door" by Sam Roe, CC BY-SA 3.0' in text
    assert "Optional acknowledgements" in text
    # The notice to copy is the CREDITS.txt of Download files, and read-only.
    notice = html.split('id="notice-full"', 1)[1].split("</pre>", 1)[0]
    assert "ATTRIBUTION AND LICENSE NOTICE" in notice and "6. DISCLAIMER" in notice
    assert 'data-copy="notice-full"' in html and 'data-copy="notice-lines"' in html
    content = html.split('id="content"', 1)[1]
    assert "<form" not in content and "<textarea" not in content and "hx-post" not in content
    # A visitor gets no way into the builder, nor to the owner's asset pages.
    assert reverse("packs:builder", args=[golden_pack.pk]) not in html
    assert "/attribution/assets/" not in html


def test_the_owner_gets_the_builder_and_each_assets_attribution(member_client, golden_pack):
    html = member_client.get(
        reverse("packs:attribution_pack", args=[golden_pack.slug])
    ).content.decode()
    assert reverse("packs:builder", args=[golden_pack.pk]) in html
    for item in golden_pack.items.all():
        assert reverse("packs:attribution_asset", args=[item.saved_asset_id]) in html


def test_a_private_packs_attribution_is_a_404_to_anyone_but_the_owner(golden_pack, member, other):
    golden_pack.set_visibility("private")
    url = reverse("packs:attribution_pack", args=[golden_pack.slug])
    assert Client().get(url).status_code == 404
    signed_in = Client()
    signed_in.force_login(other)
    assert signed_in.get(url).status_code == 404
    owner = Client()
    owner.force_login(member)
    assert owner.get(url).status_code == 200


def test_an_unlisted_packs_attribution_comes_only_through_its_share_link(golden_pack, other):
    golden_pack.set_visibility("unlisted")
    signed_in = Client()
    signed_in.force_login(other)
    assert (
        signed_in.get(reverse("packs:attribution_pack", args=[golden_pack.slug])).status_code == 404
    )
    link = reverse("packs:shared_attribution", args=[golden_pack.share_token])
    response = Client().get(link)
    assert response.status_code == 200 and response["X-Robots-Tag"] == "noindex, nofollow"
    # The share page's credits link to the shared attribution, not the slug one.
    page = Client().get(golden_pack.get_share_url()).content.decode()
    assert f'href="{link}"' in page
    golden_pack.set_visibility("public")
    assert Client().get(link).url == reverse("packs:attribution_pack", args=[golden_pack.slug])
    golden_pack.set_visibility("private")
    assert Client().get(link).status_code == 404


def test_a_packs_attribution_never_shows_the_owners_review(client, golden_pack):
    entry = golden_pack.items.first().saved_asset
    entry.notes, entry.rating = "SENTINEL-NOTE never share this", 2
    entry.save()
    html = client.get(reverse("packs:attribution_pack", args=[golden_pack.slug])).content.decode()
    assert "SENTINEL-NOTE" not in html and "star-rating" not in html


# ---------------------------------------------------------------- asset attribution


@pytest.fixture
def mixed_library(member, make_asset):
    """Five of the member's entries across four licenses and every credit rule."""
    licenses = {
        "brick": "CC0 1.0",
        "moss": "CC0",
        "birds": "CC BY 4.0",
        "drums": "CC BY-NC 3.0",
        "chant": "Public Domain Mark",
    }
    return {
        name: SavedAsset.objects.create(
            user=member,
            asset=make_asset(external_id=name, title=name.title(), license=license),
        )
        for name, license in licenses.items()
    }


def _titles(html):
    return re.findall(r'class="lookup-title">([^<]+)<', html)


def test_asset_attribution_filters_by_license_type(member_client, mixed_library):
    url = reverse("packs:attribution_assets")
    assert sorted(_titles(member_client.get(url).content.decode())) == [
        "Birds", "Brick", "Chant", "Drums", "Moss",
    ]  # fmt: skip
    html = member_client.get(url, {"license": "cc0"}, headers=HTMX).content.decode()
    # "CC0 1.0" and "CC0" are one license type.
    assert sorted(_titles(html)) == ["Brick", "Moss"]
    html = member_client.get(url, {"license": ["by", "by-nc"]}, headers=HTMX).content.decode()
    assert sorted(_titles(html)) == ["Birds", "Drums"]


def test_asset_attribution_filters_by_credit_rule(member_client, mixed_library):
    url = reverse("packs:attribution_assets")
    get = lambda **params: _titles(member_client.get(url, params, headers=HTMX).content.decode())  # noqa: E731
    assert sorted(get(credit="required")) == ["Birds", "Drums"]
    assert sorted(get(credit="listed")) == ["Chant"]
    assert sorted(get(credit="optional")) == ["Brick", "Moss"]
    # A type and a rule must both match; with the search too.
    assert get(license="by", credit="optional") == []
    assert get(credit="required", q="drum") == ["Drums"]
    # Unknown values are ignored, so the filter falls back to everything.
    assert len(get(license="nonsense", credit="maybe")) == 5


def test_the_filter_chips_show_counts_and_keep_the_choices(member_client, mixed_library):
    url = reverse("packs:attribution_assets")
    html = member_client.get(url, {"license": "cc0", "credit": "optional"}).content.decode()
    chips = _text(html.split('id="attribution-filters"', 1)[1].split("</form>", 1)[0])
    assert "CC0 2" in chips and "CC BY 1" in chips and "CC BY-NC 1" in chips
    assert "Public Domain Mark 1" in chips and "CC BY-SA" not in chips  # only what's there
    assert "Credit required 2" in chips and "Credit recommended 1" in chips
    assert 'name="license" value="cc0" checked' in html
    assert 'name="credit" value="optional" checked' in html
    assert "2 assets match" in _text(html) and "Clear filters" in html
    assert 'hx-push-url="true"' in html


def test_asset_attribution_pages_keep_the_filters(member_client, member, make_asset):
    for n in range(14):
        SavedAsset.objects.create(
            user=member, asset=make_asset(external_id=f"s{n:02}", license="CC BY 4.0")
        )
    url = reverse("packs:attribution_assets")
    html = member_client.get(url, {"license": "by"}, headers=HTMX).content.decode()
    assert html.count('class="lookup-item"') == 12 and "Page 1 of 2" in html
    assert f'href="{url}?license=by&amp;page=2"' in html


def test_asset_attribution_never_shows_another_members_entries(
    member_client, mixed_library, other, make_asset
):
    SavedAsset.objects.create(
        user=other, asset=make_asset(external_id="x", title="Their Find", license="CC BY-SA 4.0")
    )
    url = reverse("packs:attribution_assets")
    html = member_client.get(url).content.decode()
    assert "Their Find" not in html and "CC BY-SA" not in html
    html = member_client.get(url, {"license": "by-sa"}, headers=HTMX).content.decode()
    assert _titles(html) == []


def test_an_assets_attribution_page_is_the_owners_alone(
    member_client, mixed_library, golden_pack, other, client
):
    entry = mixed_library["drums"]
    url = reverse("packs:attribution_asset", args=[entry.pk])
    html = member_client.get(url).content.decode()
    text = _text(html)
    assert "Drums" in text and "Credit required" in text and "You may not" in text
    assert "Use it commercially" in text  # NC: in the may-not list
    notice = unescape(html.split('id="notice-full"', 1)[1].split("</pre>", 1)[0])
    assert 'Covers:       "Drums"' in notice and "1. REQUIRED ATTRIBUTION" in notice
    assert "It isn't in any of your packs yet." in text
    # Another member's entry is a 404; a visitor is sent to sign in.
    other_client = Client()
    other_client.force_login(other)
    assert other_client.get(url).status_code == 404
    assert Client().get(url).url.startswith(reverse("accounts:login"))


def test_an_assets_attribution_lists_the_members_packs_holding_it(member_client, golden_pack):
    entry = golden_pack.items.first().saved_asset
    html = member_client.get(reverse("packs:attribution_asset", args=[entry.pk])).content.decode()
    assert reverse("packs:attribution_pack", args=[golden_pack.slug]) in html


def test_the_members_pages_send_a_visitor_to_sign_in(client):
    for name in ("packs:attribution_packs", "packs:attribution_assets"):
        url = reverse(name)
        assert client.get(url).url == f"{reverse('accounts:login')}?next={url}"
        assert client.get(url, headers=HTMX)["HX-Redirect"].startswith(reverse("accounts:login"))


def test_an_entrys_license_links_to_its_card_in_the_guide(member_client, member, make_asset):
    entry = SavedAsset.objects.create(
        user=member, asset=make_asset(external_id="birds", license="CC BY-NC 4.0")
    )
    html = member_client.get(reverse("catalog:entry", args=[entry.pk])).content.decode()
    assert f'href="{reverse("packs:attribution")}#license-by-nc"' in html
    assert "Credit required" in html


# ---------------------------------------------------------------- uses and compatibility
# User request, 2026-11-05: can a pack be used commercially, personally or internally,
# and a warning when it can't; license symbols and one license per row.


@pytest.mark.parametrize(
    ("key", "commercial", "personal", "internal"),
    [
        ("cc0", "ok", "ok", "ok"),
        ("pdm", "ok", "ok", "ok"),
        ("by", "ok", "ok", "ok"),
        ("by-sa", "caution", "caution", "ok"),
        ("by-nd", "caution", "caution", "ok"),
        ("by-nc", "blocked", "ok", "caution"),
        ("by-nc-sa", "blocked", "caution", "caution"),
        ("by-nc-nd", "blocked", "caution", "caution"),
        ("sampling+", "caution", "ok", "ok"),
        ("nc-sampling+", "blocked", "ok", "caution"),
        ("unknown", "blocked", "blocked", "caution"),
    ],
)
def test_each_license_says_which_uses_it_allows(key, commercial, personal, internal):
    verdicts = {verdict.use: verdict for verdict in LICENSES[key].uses}
    assert [verdicts[use].status for use in ("commercial", "personal", "internal")] == [
        commercial,
        personal,
        internal,
    ]
    assert all(verdict.note for verdict in verdicts.values())


def test_each_license_has_its_symbols():
    names = lambda key: [name for _, name, _ in LICENSES[key].symbols]  # noqa: E731
    assert names("by-nc-sa") == ["Attribution", "NonCommercial", "ShareAlike"]
    assert names("cc0") == ["Public domain dedication"]
    assert names("unknown") == ["Unknown license"]


def _pack_of(member, make_asset, *licenses):
    pack = Pack.objects.create_pack(member, "Mixed Bag")
    for index, license in enumerate(licenses):
        asset = make_asset(external_id=f"m{index}", title=f"Thing {index}", license=license)
        add_to_pack(pack, SavedAsset.objects.create(user=member, asset=asset))
    return pack


def test_a_noncommercial_item_rules_the_pack_out_of_commercial_use(member, make_asset):
    pack = _pack_of(member, make_asset, "CC0", "CC BY-NC 4.0", "CC BY-NC 4.0")
    credits = pack_credits(list(pack.ordered_items()))
    checks = {check.use: check for check in credits.compatibility}
    assert checks["commercial"].status == "blocked"
    assert checks["commercial"].reasons == [
        '"Thing 1" and "Thing 2" (CC BY-NC 4.0): Non-commercial only.'
    ]
    assert checks["personal"].status == "ok" and checks["personal"].reasons == []
    assert checks["internal"].status == "caution"
    assert [check.use for check in credits.blocked_uses] == ["commercial"]


def test_blocking_reasons_come_before_conditions(member, make_asset):
    pack = _pack_of(member, make_asset, "CC BY-SA 4.0", "unknown")
    checks = {check.use: check for check in pack_credits(list(pack.ordered_items())).compatibility}
    assert checks["commercial"].reasons[0].startswith('"Thing 1" (unknown)')
    assert checks["commercial"].reasons[1].startswith('"Thing 0" (CC BY-SA 4.0)')
    assert [check.use for check in pack_credits(list(pack.ordered_items())).blocked_uses] == [
        "commercial",
        "personal",
    ]


def test_an_all_cc0_pack_is_usable_every_way(member, make_asset):
    pack = _pack_of(member, make_asset, "CC0", "CC0 1.0")
    credits = pack_credits(list(pack.ordered_items()))
    assert {check.status for check in credits.compatibility} == {"ok"}
    assert credits.blocked_uses == [] and not credits.has_conditions


def test_the_notice_states_the_permitted_uses(member, make_asset):
    pack = _pack_of(member, make_asset, "CC0", "CC BY-NC 4.0")
    text = pack_notice(pack, pack_credits(list(pack.ordered_items())))
    uses = text.split("3. PERMITTED USES", 1)[1].split("4. ", 1)[0]
    assert "Commercial (sold, ad-supported, or made for a business): NOT USABLE." in uses
    assert '- "Thing 1" (CC BY-NC 4.0): Non-commercial only.' in uses
    assert "Personal (free, non-commercial projects you share or publish): USABLE." in uses
    flat = " ".join(uses.split())
    assert "may not be usable together for commercial use" in flat
    assert "contact the person who compiled them" in flat


def test_a_reader_is_warned_and_told_to_contact_the_owner(client, member, make_asset):
    pack = _pack_of(member, make_asset, "CC0", "CC BY-NC 4.0")
    pack.set_visibility("public")
    for url in (pack.get_public_url(), reverse("packs:attribution_pack", args=[pack.slug])):
        html = client.get(url).content.decode()
        text = unescape(_text(html))
        assert 'id="pack-compatibility"' in html
        assert "This pack may not be usable for commercial use." in text
        assert '"Thing 1" (CC BY-NC 4.0): Non-commercial only.' in text
        assert "contact the owner, demo_member" in text
        assert "edit the pack" not in text  # that's for the owner
        compat = html.split('id="pack-compatibility"', 1)[1].split("</section>", 1)[0]
        assert compat.count('class="use-cell"') == 3


def test_the_owner_is_told_to_edit_the_pack(member_client, member, make_asset):
    pack = _pack_of(member, make_asset, "CC BY-NC 4.0")
    for url in (pack.get_public_url(), reverse("packs:builder", args=[pack.pk])):
        html = member_client.get(url).content.decode()
        assert "This pack may not be usable for commercial use." in unescape(_text(html))
        assert (
            f'<a href="{reverse("packs:builder", args=[pack.pk])}" class="entry-link">edit the pack</a>'
            in html
        )


def test_the_builder_rechecks_compatibility_on_every_change(member_client, member, make_asset):
    pack = _pack_of(member, make_asset, "CC0", "CC BY-NC 4.0")
    noncommercial = pack.items.get(saved_asset__asset__license="CC BY-NC 4.0")
    url = reverse("packs:item_remove", args=[pack.pk, noncommercial.pk])
    html = member_client.post(url, headers=HTMX).content.decode()
    assert 'id="pack-compatibility"' in html and "may not be usable" not in html
    assert "Every item's license allows commercial, personal and internal use." in html


def test_a_pack_with_no_problems_says_so(client, golden_pack):
    html = client.get(golden_pack.get_public_url()).content.decode()
    text = unescape(_text(html))
    assert "may not be usable" not in text
    # CC BY-SA: no use is ruled out, but some come with conditions.
    assert "No license here rules out a use, but some come with conditions" in text


def test_pack_attribution_marks_each_packs_uses(member_client, member, make_asset):
    _pack_of(member, make_asset, "CC BY-NC 4.0")
    html = member_client.get(reverse("packs:attribution_packs")).content.decode()
    assert '<li class="use-chip" data-status="blocked">' in html
    assert "Commercial: not usable" in html
    assert "This pack may not be usable for commercial use." in unescape(_text(html))


def test_the_guide_shows_symbols_uses_and_one_license_per_row(client):
    html = client.get(reverse("packs:attribution")).content.decode()
    assert 'id="attribution-symbols"' in html and html.count('class="symbol-legend"') == 2
    for name in ("Attribution", "NonCommercial", "NoDerivatives", "ShareAlike"):
        assert f"<strong>{name}</strong>" in html
    # The table: a verdict for each use, for each license.
    table = html.split('class="attribution-table"', 1)[1].split("</table>", 1)[0]
    assert table.count('class="use-td"') == 3 * len(LICENSES)
    # Every card has its symbols and its three uses.
    assert html.count('class="license-symbols is-large"') == len(LICENSES)
    assert html.count('aria-label="Can I use it?"') == len(LICENSES)
    css = (settings.BASE_DIR / "styles" / "source.css").read_text(encoding="utf-8")
    assert ".license-cards { display: grid; gap: 0.6rem; }" in css.replace(
        ".credits-groups, .license-cards", ".license-cards"
    )
    assert (
        "repeat(2, minmax(0, 1fr)); } }" not in css.split(".license-cards", 1)[1].split("\n", 1)[0]
    )


def test_the_attribution_pages_are_centred(member_client, golden_pack):
    css = (settings.BASE_DIR / "styles" / "source.css").read_text(encoding="utf-8")
    assert ".attribution { width: 100%; max-width: 64rem; margin-inline: auto; }" in css
    for url in (
        reverse("packs:attribution"),
        reverse("packs:attribution_packs"),
        reverse("packs:attribution_pack", args=[golden_pack.slug]),
        reverse("packs:attribution_assets"),
    ):
        assert '<section class="attribution ' in member_client.get(url).content.decode()


def test_the_verdict_key_keeps_each_icon_beside_its_word(client):
    """ "Not usable" was the last span in the key, so the legend's stacked layout
    caught it and put its icon above the word (user report, 2026-11-06)."""
    css = (settings.BASE_DIR / "styles" / "source.css").read_text(encoding="utf-8")
    assert ".symbol-legend li:not(.symbol-legend-key) > span:last-child { display: grid;" in css
    assert ".symbol-legend li > span:last-child" not in css
    html = client.get(reverse("packs:attribution")).content.decode()
    key = re.search(r'<li class="symbol-legend-key">(.*?)</li>', html, re.S).group(1)
    assert key.count('<span class="use-key">') == 3


def test_on_this_page_folds_the_licenses_away(client):
    html = client.get(reverse("packs:attribution")).content.decode()
    toc = html.split('id="attribution-toc"', 1)[1].split("</nav>", 1)[0]
    fold = re.search(r'<details id="attribution-toc-licenses"[^>]*>', toc).group(0)
    assert "data-remember" in fold and " open" not in fold  # closed until opened
    licenses = toc.split(fold, 1)[1].split("</details>", 1)[0]
    assert licenses.count('class="panel-row" href="#license-') == 11
    # Outside the fold: Symbols, At a glance, How to credit, Optional credits.
    outside = toc.replace(licenses, "")
    assert outside.count('class="panel-row" href="#attribution-') == 4
