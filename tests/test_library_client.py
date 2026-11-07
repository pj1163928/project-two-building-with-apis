"""The library_client.py console script, which calls the Toolbox's own API.

Most tests answer its HTTP with canned `responses` mocks. The end-to-end
test hands each request the script sends to Django's test client instead,
so the script runs against the real /api/library/ views without a server
or the network.
"""

import json
import re

import pytest
import requests
from responses import matchers
from rest_framework.authtoken.models import Token

import library_client
from catalog.models import SavedAsset

SERVER = "http://127.0.0.1:8000"
LIST_URL = f"{SERVER}/api/library/"


def entry(entry_id=1, title="Red Brick 03", status="to_review", rating=None, notes=""):
    return {
        "id": entry_id,
        "asset": {"title": title, "kind": "texture", "provider": "polyhaven"},
        "notes": notes,
        "rating": rating,
        "status": status,
        "status_change": None,
    }


def page(*entries, next_url=None):
    return {"count": len(entries), "next": next_url, "results": list(entries)}


@pytest.fixture
def run(monkeypatch, capsys):
    """Run main() with these typed answers and token; returns what it printed."""
    monkeypatch.delenv("TOOLBOX_URL", raising=False)
    monkeypatch.delenv("TOOLBOX_TOKEN", raising=False)

    def run_with(answers, token="test-token"):
        typed = iter(answers)
        monkeypatch.setattr("builtins.input", lambda prompt="": next(typed))
        monkeypatch.setattr(library_client.getpass, "getpass", lambda prompt="": token)
        try:
            library_client.main()
        except SystemExit as exit_:
            assert exit_.code in (0, 1, None)
        return capsys.readouterr().out

    return run_with


# ---------------------------------------------------------------- happy paths


def test_changes_status_and_shows_before_and_after(mocked_responses, run):
    mocked_responses.get(LIST_URL, json=page(entry(7, "Red Brick 03"), entry(8, "Forest HDRI")))
    patch = mocked_responses.patch(
        f"{SERVER}/api/library/8/",
        json=entry(8, "Forest HDRI", status="approved"),
    )

    # default server, entry 2, field 1 (status), status 3 (approved), reason
    out = run(["", "2", "1", "3", "Looks great"])

    assert json.loads(patch.calls[0].request.body) == {
        "status": "approved",
        "status_reason": "Looks great",
    }
    assert patch.calls[0].request.headers["Authorization"] == "Token test-token"
    assert "1) Red Brick 03" in out and "2) Forest HDRI" in out
    before, after = out.split("Before:")[1].split("After:")
    assert "Status:  To review" in before
    assert "Status:  Approved" in after


def test_rating_can_be_set_and_cleared(mocked_responses, run):
    mocked_responses.get(LIST_URL, json=page(entry(3, rating=4)))
    patch = mocked_responses.patch(f"{SERVER}/api/library/3/", json=entry(3, rating=None))

    out = run(["", "1", "2", ""])  # rating, blank clears it

    assert json.loads(patch.calls[0].request.body) == {"rating": None}
    assert "Rating:  4/5" in out.split("After:")[0]
    assert "Rating:  unrated" in out.split("After:")[1]


def test_follows_every_page_of_the_library(mocked_responses, run):
    mocked_responses.get(
        LIST_URL,
        json=page(entry(1, "First"), next_url=f"{LIST_URL}?page=2"),
        match=[matchers.query_string_matcher("")],
    )
    mocked_responses.get(
        f"{LIST_URL}?page=2",
        json=page(entry(2, "Second")),
        match=[matchers.query_string_matcher("page=2")],
    )

    out = run(["", ""])  # blank entry choice quits

    assert "1) First" in out and "2) Second" in out
    assert "Goodbye." in out


# ---------------------------------------------------------------- failures


def test_server_not_running(mocked_responses, run):
    mocked_responses.get(LIST_URL, body=requests.ConnectionError())

    out = run([""])

    assert "Can't reach the Toolbox at http://127.0.0.1:8000" in out
    assert "manage.py runserver" in out


def test_wrong_token(mocked_responses, run):
    mocked_responses.get(LIST_URL, status=401, json={"detail": "Invalid token."})

    out = run([""], token="wrong")

    assert "didn't accept that token" in out
    assert "/accounts/token/" in out


def test_empty_library(mocked_responses, run):
    mocked_responses.get(LIST_URL, json=page())

    out = run([""])

    assert "Your library is empty" in out


def test_rejected_update_shows_the_servers_reasons(mocked_responses, run):
    mocked_responses.get(LIST_URL, json=page(entry(5)))
    mocked_responses.patch(
        f"{SERVER}/api/library/5/",
        status=400,
        json={"notes": ["Ensure this field has no more than 10000 characters."]},
    )

    out = run(["", "1", "3", "x"])

    assert "rejected the change" in out
    assert "notes: Ensure this field has no more than 10000 characters." in out
    assert "After:" not in out


def test_address_that_isnt_the_toolbox(mocked_responses, run):
    mocked_responses.get(LIST_URL, status=200, body="<html>not an API</html>")

    out = run([""])

    assert "didn't answer like the Toolbox API" in out


def test_server_and_token_can_come_from_the_environment(mocked_responses, run, monkeypatch):
    mocked_responses.get("http://example.test:9000/api/library/", json=page())

    typed = iter([])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(typed))
    monkeypatch.setenv("TOOLBOX_URL", "http://example.test:9000/")
    monkeypatch.setenv("TOOLBOX_TOKEN", "env-token")
    library_client.main()

    assert mocked_responses.calls[0].request.headers["Authorization"] == "Token env-token"


# ---------------------------------------------------------------- end to end


@pytest.fixture
def toolbox(mocked_responses, client):
    """Route every request to SERVER into Django's test client: the real API, no network."""
    mocked_responses.assert_all_requests_are_fired = False

    def forward(request):
        path = request.url.removeprefix(SERVER)
        response = client.generic(
            request.method,
            path,
            data=request.body or "",
            content_type="application/json",
            HTTP_AUTHORIZATION=request.headers.get("Authorization", ""),
        )
        return response.status_code, {"Content-Type": "application/json"}, response.content

    pattern = re.compile(re.escape(SERVER) + r"/api/.*")
    for method in ("GET", "PATCH"):
        mocked_responses.add_callback(method, pattern, callback=forward)
    return mocked_responses


@pytest.mark.django_db
def test_end_to_end_against_the_real_api(toolbox, run, member, make_asset):
    saved = SavedAsset.objects.create(user=member, asset=make_asset(), rating=2)
    token = Token.objects.create(user=member)

    out = run(["", "1", "2", "5"], token=token.key)  # rating -> 5

    saved.refresh_from_db()
    assert saved.rating == 5
    assert "Rating:  2/5" in out.split("After:")[0]
    assert "Rating:  5/5" in out.split("After:")[1]


@pytest.mark.django_db
def test_end_to_end_wrong_token_changes_nothing(toolbox, run, member, make_asset):
    saved = SavedAsset.objects.create(user=member, asset=make_asset(), rating=2)

    out = run([""], token="not-a-real-token")

    saved.refresh_from_db()
    assert saved.rating == 2
    assert "didn't accept that token" in out
