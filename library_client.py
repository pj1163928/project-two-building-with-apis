"""Change one entry in your Axcenity Toolbox library through the site's own API.

Lists your library (GET /api/library/), lets you pick an entry and a new
status, rating or notes, then sends PATCH /api/library/<id>/ and shows the
entry before and after.

Run the site first (uv run python manage.py runserver), then:

    uv run library_client.py

Your token is on the site at Account -> API token (/accounts/token/). Set
TOOLBOX_TOKEN and TOOLBOX_URL to skip the prompts.
"""

import getpass
import os
import sys

import requests

DEFAULT_SERVER = "http://127.0.0.1:8000"
TIMEOUT = 10
USER_AGENT = "AxcenityToolbox-LibraryClient/0.1"

STATUSES = [
    ("to_review", "To review"),
    ("testing", "Testing"),
    ("approved", "Approved"),
    ("rejected", "Rejected"),
]
STATUS_LABELS = dict(STATUSES)
FIELDS = [("status", "Status"), ("rating", "Rating"), ("notes", "Notes")]


class ClientError(Exception):
    """A failure talking to the Toolbox, with a message that's safe to print."""


# ---------------------------------------------------------------- API


class LibraryClient:
    """The two library API calls this script needs, signed in with a token."""

    def __init__(self, server: str, token: str):
        self.server = server.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Token {token}", "User-Agent": USER_AGENT})

    def entries(self) -> list[dict]:
        """Every entry in your library, following the API's pages of 12."""
        url = f"{self.server}/api/library/"
        found = []
        while url:
            page = self._send("get", url)
            found.extend(page.get("results", []))
            url = page.get("next")
        return found

    def update(self, entry_id: int, changes: dict) -> dict:
        """PATCH one entry with `changes` and return the entry the server sends back."""
        return self._send("patch", f"{self.server}/api/library/{entry_id}/", json=changes)

    def _send(self, method: str, url: str, **kwargs) -> dict:
        try:
            response = self.session.request(method, url, timeout=TIMEOUT, **kwargs)
        except requests.ConnectionError:
            raise ClientError(
                f"Can't reach the Toolbox at {self.server}. Is the server running?\n"
                "  Start it with: uv run python manage.py runserver"
            ) from None
        except requests.Timeout:
            raise ClientError(f"The Toolbox at {self.server} took too long to answer.") from None
        except requests.RequestException as error:
            raise ClientError(f"The request failed: {error.__class__.__name__}.") from None

        if response.status_code == 401:
            raise ClientError(
                "The server didn't accept that token. Copy it again from "
                f"{self.server}/accounts/token/"
            )
        if response.status_code == 404:
            raise ClientError("That entry isn't in your library any more.")
        try:
            body = response.json()
        except ValueError:
            raise ClientError(
                f"{self.server} didn't answer like the Toolbox API "
                f"(HTTP {response.status_code}). Check the server address."
            ) from None
        if response.status_code == 400:
            raise ClientError("The server rejected the change:\n" + describe_errors(body))
        if not response.ok:
            detail = body.get("detail") if isinstance(body, dict) else None
            raise ClientError(f"The server answered HTTP {response.status_code}. {detail or ''}")
        return body


def describe_errors(body) -> str:
    """DRF's validation errors ({"field": ["message", ...]}) as indented lines."""
    if not isinstance(body, dict):
        return f"  {body}"
    lines = []
    for field, messages in body.items():
        if not isinstance(messages, list):
            messages = [messages]
        lines.extend(f"  {field}: {message}" for message in messages)
    return "\n".join(lines)


# ---------------------------------------------------------------- prompts


def ask(prompt: str) -> str:
    """input() that treats Ctrl+C / Ctrl+Z as a request to quit."""
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        raise SystemExit(0) from None


def ask_number(prompt: str, count: int, allow_blank: bool = False) -> int | None:
    """Ask for a number from 1 to count. Returns None on a blank answer if allowed."""
    while True:
        answer = ask(prompt)
        if not answer and allow_blank:
            return None
        if answer.isdecimal() and 1 <= int(answer) <= count:
            return int(answer)
        print(f"  Please enter a number from 1 to {count}.")


def ask_token() -> str:
    """The API token from TOOLBOX_TOKEN, or typed in without echoing it."""
    if token := os.environ.get("TOOLBOX_TOKEN", "").strip():
        return token
    while True:
        try:
            token = getpass.getpass("API token (from Account -> API token): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            raise SystemExit(0) from None
        if token:
            return token
        print("  Please paste your token.")


def ask_server() -> str:
    """The server address from TOOLBOX_URL, or typed in, defaulting to the dev server."""
    if server := os.environ.get("TOOLBOX_URL", "").strip():
        return server
    answer = ask(f"Server [{DEFAULT_SERVER}]: ")
    if answer and not answer.startswith(("http://", "https://")):
        answer = f"http://{answer}"
    return answer or DEFAULT_SERVER


def choose_entry(entries: list[dict]) -> dict | None:
    print(f"\nYour library ({len(entries)} entries):")
    for number, entry in enumerate(entries, start=1):
        asset = entry["asset"]
        print(
            f"  {number:>3}) {asset['title']}  [{asset['kind']}, {asset['provider']}]"
            f"  {STATUS_LABELS.get(entry['status'], entry['status'])}, {stars(entry['rating'])}"
        )
    number = ask_number("Choose an entry (blank to quit): ", len(entries), allow_blank=True)
    return None if number is None else entries[number - 1]


def choose_change(entry: dict) -> dict:
    """Ask which field to change and its new value; returns the PATCH body."""
    print("\nWhat do you want to change?")
    for number, (_, label) in enumerate(FIELDS, start=1):
        print(f"  {number}) {label}")
    field = FIELDS[ask_number("Field: ", len(FIELDS)) - 1][0]

    if field == "status":
        print("New status:")
        for number, (_, label) in enumerate(STATUSES, start=1):
            current = "  (current)" if STATUSES[number - 1][0] == entry["status"] else ""
            print(f"  {number}) {label}{current}")
        status = STATUSES[ask_number("Status: ", len(STATUSES)) - 1][0]
        changes = {"status": status}
        if reason := ask("Reason (optional): "):
            changes["status_reason"] = reason
        return changes

    if field == "rating":
        rating = ask_number("New rating, 1 to 5 (blank to clear it): ", 5, allow_blank=True)
        return {"rating": rating}

    print(f"Current notes: {entry['notes'] or '(none)'}")
    return {"notes": ask("New notes (blank to clear them): ")}


# ---------------------------------------------------------------- output


def stars(rating: int | None) -> str:
    return f"{rating}/5" if rating else "unrated"


def show_entry(heading: str, entry: dict) -> None:
    asset = entry["asset"]
    print(f"\n{heading}")
    print(f"  #{entry['id']}  {asset['title']} ({asset['kind']}, {asset['provider']})")
    print(f"  Status:  {STATUS_LABELS.get(entry['status'], entry['status'])}")
    change = entry.get("status_change")
    if change:
        why = f": {change['reason']}" if change.get("reason") else ""
        print(f"           set by {change['by'] or 'unknown'} via {change['via']}{why}")
    print(f"  Rating:  {stars(entry['rating'])}")
    print(f"  Notes:   {entry['notes'] or '(none)'}")


# ---------------------------------------------------------------- main


def main() -> None:
    # Titles and notes can hold characters a Windows code page can't print.
    sys.stdout.reconfigure(errors="replace")
    print("Axcenity Toolbox library client")
    server = ask_server()
    client = LibraryClient(server, ask_token())
    try:
        entries = client.entries()
        if not entries:
            print(
                "\nYour library is empty. Save some assets on the Discover page "
                f"({client.server}/discover/) first."
            )
            return
        entry = choose_entry(entries)
        if entry is None:
            print("Goodbye.")
            return
        changes = choose_change(entry)
        show_entry("Before:", entry)
        print(f"\nSending PATCH /api/library/{entry['id']}/ {changes}")
        updated = client.update(entry["id"], changes)
        show_entry("After:", updated)
    except ClientError as error:
        print(f"\nError: {error}")
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
