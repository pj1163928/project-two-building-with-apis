"""Who set an entry's review status, when, where and why (user request, 2026-11-05).

Recorded the same way from the drawer and from the API (SavedAsset.save_review and
explain_status), and private like the rest of the review.
"""

import pytest
from django.test import Client
from django.urls import reverse

from providers import PROVIDERS

pytestmark = pytest.mark.django_db


@pytest.fixture
def entry(member, make_asset):
    from catalog.models import SavedAsset

    return SavedAsset.objects.create(user=member, asset=make_asset())


def _update(client, entry, data, **headers):
    headers.setdefault("HTTP_HX_REQUEST", "true")
    return client.post(reverse("catalog:update", args=[entry.pk]), data, **headers)


def test_saving_records_the_first_status_and_who_saved_it(member, make_asset, monkeypatch):
    from catalog.library import save_to_library
    from catalog.models import StatusChange

    make_asset(provider="polyhaven", external_id="red_brick_03")
    for provider in PROVIDERS:
        monkeypatch.setattr(provider, "fetch_record", lambda *a: pytest.fail("no fetch"))
    entry, created = save_to_library(member, "polyhaven", "red_brick_03")
    change = entry.status_changes.get()
    assert created and (change.status, change.changed_by, change.via) == (
        "to_review",
        member,
        "site",
    )
    # Saving it again records nothing new.
    save_to_library(member, "polyhaven", "red_brick_03")
    assert StatusChange.objects.count() == 1


def test_a_status_change_records_who_when_and_where(member_client, member, entry):
    response = _update(member_client, entry, {"status": "approved"})
    assert response.status_code == 200
    change = entry.status_changes.get()
    assert (change.status, change.changed_by, change.via, change.reason) == (
        "approved",
        member,
        "site",
        "",
    )
    html = response.content.decode()
    # The note and an empty reason box come back out of band.
    assert '<div id="entry-status-note" class="entry-status-note" hx-swap-oob="true">' in html
    assert "Approved" in html and "by you" in html
    assert 'id="entry-status-reason"' in html and 'placeholder="Why is it approved?' in html


def test_the_same_status_again_records_nothing(member_client, entry):
    _update(member_client, entry, {"status": "to_review"})
    _update(member_client, entry, {"rating": "4"})
    _update(member_client, entry, {"notes": "Tiles well."})
    assert not entry.status_changes.exists()


def test_a_reason_goes_on_the_latest_change(member_client, member, entry):
    _update(member_client, entry, {"status": "rejected"})
    response = _update(member_client, entry, {"status_reason": "  Seams   show at 4K.  "})
    assert response.status_code == 200
    change = entry.status_changes.get()
    assert change.reason == "Seams show at 4K."
    html = response.content.decode()
    assert "“Seams show at 4K.”" in html
    # Only the note comes back, so the box being typed in is left alone.
    assert 'id="entry-status-reason"' not in html
    # A new status starts without a reason, and the history keeps both.
    _update(member_client, entry, {"status": "testing"})
    assert list(entry.status_changes.values_list("status", "reason")) == [
        ("testing", ""),
        ("rejected", "Seams show at 4K."),
    ]


def test_a_reason_for_a_status_with_no_record_makes_one(member_client, member, entry):
    _update(member_client, entry, {"status_reason": "Waiting on the art lead."})
    change = entry.status_changes.get()
    assert (change.status, change.reason, change.changed_by) == (
        "to_review",
        "Waiting on the art lead.",
        member,
    )


def test_a_reason_over_the_limit_is_a_400_that_saves_nothing(member_client, entry):
    response = _update(member_client, entry, {"status_reason": "x" * 301})
    assert response.status_code == 400
    assert "A reason can be up to 300 characters." in response.content.decode()
    assert not entry.status_changes.exists()


def test_the_drawer_shows_who_set_it_why_and_the_history(member_client, entry):
    _update(member_client, entry, {"status": "testing"})
    _update(member_client, entry, {"status_reason": "Trying it in the dungeon level."})
    _update(member_client, entry, {"status": "approved"})
    html = member_client.get(reverse("catalog:entry", args=[entry.pk]), HTTP_HX_REQUEST="true")
    html = html.content.decode()
    note = html.split('id="entry-status-note"', 1)[1].split('id="entry-status-reason"', 1)[0]
    assert "Approved" in note and "by you" in note
    assert "History · 2 changes" in note
    assert "<q>Trying it in the dungeon level.</q>" in note


def test_an_entry_with_no_record_says_since_when(member_client, entry):
    html = member_client.get(reverse("catalog:entry", args=[entry.pk])).content.decode()
    assert "since you saved it on" in html and "History" not in html


def test_a_plain_reason_post_goes_back_to_the_entry(member_client, entry):
    response = member_client.post(
        reverse("catalog:update", args=[entry.pk]), {"status_reason": "ok"}
    )
    assert response.status_code == 302 and response["Location"] == reverse(
        "catalog:entry", args=[entry.pk]
    )


def test_another_members_entry_is_a_404_and_gains_no_reason(entry, django_user_model):
    other = Client()
    other.force_login(django_user_model.objects.create_user("other_member"))
    assert _update(other, entry, {"status_reason": "mine now"}).status_code == 404
    assert _update(other, entry, {"status": "approved"}).status_code == 404
    assert not entry.status_changes.exists()


def test_a_reason_needs_csrf(member, entry):
    strict = Client(enforce_csrf_checks=True)
    strict.force_login(member)
    assert _update(strict, entry, {"status_reason": "no token"}).status_code == 403
    assert not entry.status_changes.exists()


# ---------------------------------------------------------------- the API


def _api(client, entry, data):
    return client.patch(
        reverse("catalog:api_entry", args=[entry.pk]), data, content_type="application/json"
    )


def test_the_api_records_a_status_change_with_its_reason(member_client, member, entry):
    response = _api(member_client, entry, {"status": "approved", "status_reason": "Signed off."})
    assert response.status_code == 200
    change = entry.status_changes.get()
    assert (change.status, change.reason, change.via, change.changed_by) == (
        "approved",
        "Signed off.",
        "api",
        member,
    )
    body = response.json()
    assert body["status_change"]["by"] == member.username
    assert (
        body["status_change"]["reason"] == "Signed off." and body["status_change"]["via"] == "api"
    )
    assert "status_reason" not in body  # write-only


def test_the_api_can_explain_the_current_status_alone(member_client, entry):
    _api(member_client, entry, {"status": "rejected"})
    _api(member_client, entry, {"status_reason": "Wrong scale."})
    assert list(entry.status_changes.values_list("status", "reason")) == [
        ("rejected", "Wrong scale.")
    ]


def test_the_api_shows_no_status_change_before_one_is_recorded(member_client, entry):
    body = member_client.get(reverse("catalog:api_entry", args=[entry.pk])).json()
    assert body["status_change"] is None


def test_the_api_list_carries_each_status_change(member_client, entry):
    _api(member_client, entry, {"status": "testing"})
    results = member_client.get(reverse("catalog:api_library")).json()["results"]
    assert results[0]["status_change"]["status"] == "testing"


def test_the_drawer_says_when_the_api_set_it(member_client, entry):
    _api(member_client, entry, {"status": "approved"})
    html = member_client.get(reverse("catalog:entry", args=[entry.pk])).content.decode()
    assert "via the API" in html
