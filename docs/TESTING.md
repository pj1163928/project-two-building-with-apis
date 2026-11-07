# Testing

```sh
uv run pytest                 # whole suite
uv run pytest tests/test_access_control.py -q
uv run pytest --cov           # with coverage
```

All tests live in `tests/` and share one `tests/conftest.py`. pytest-django
reads `DJANGO_SETTINGS_MODULE` from `pyproject.toml`. Files are named by
area. **Which file covers what:** [testing/test-files.md](testing/test-files.md).
Open it to find where a new test belongs, and add a row when you create a file.

## Fixtures every test gets (autouse)

- **`_clear_cache`:** clears Django's cache before and after each test. The
  Toolbox installs that cache into `providers.cache`, so Poly Haven's
  cached `/info` answers are cleared too.
- **`_network_guard`:** replaces `socket.getaddrinfo`,
  `socket.socket.connect` and `connect_ex` with a function raising
  `NetworkBlockedError`, a `RuntimeError` (not an `OSError` or a requests
  exception), so `get_json()` can't turn it into a `ProviderError`. It
  always fails the test. There's no opt-out marker, and none may be added.
- **`_fast_password_hashing`:** MD5 hashing in tests, for speed only.

## Other fixtures

| Fixture | Gives |
|---|---|
| `mocked_responses` | A `responses.RequestsMock` that also fails if a registered URL goes unused |
| `password` | The test password (an obvious demo value) |
| `member` | A user named `demo_member` |
| `member_client` | The default `client`, signed in as `member`. It's the same object as `client`, so use `django.test.Client()` for a second, signed-out client |
| `make_asset` | A factory for stored `Asset`s (`make_asset(external_id=..., kind=..., **fields)`) |
| `provider_calls` (in `test_discover.py`) | Replaces every provider's `search_records` and records each call, to prove a request never reached a provider |

## Which mocking tool

- **Provider client tests** (code in `providers/`): use `responses`. Fake
  the HTTP and assert on the parsed result or the `ProviderError` message.
- **App tests** (views, services, the API): replace provider functions with
  `monkeypatch.setattr(...)`, so tests never depend on response JSON shapes.
  To prove a path never calls a provider, make every provider function fail
  the test if called.
- Never call a live API. The guard will fail the test.

## Access and CSRF tests

- Every access rule a phase touches gets a test. Test the website and the
  API wherever both exist.
- Members-only pages: check `302` to `reverse("accounts:login") + "?next=<path>"`,
  and that signing in with that `next` comes back to the page.
- Objects the caller doesn't own: check **404**, and that nothing was written.
- CSRF: use `Client(enforce_csrf_checks=True)` and check that a POST
  without a token gets **403**. The normal test client skips CSRF checks.
- API: a session write without CSRF is refused (**403**), and the same
  request with `Authorization: Token <key>` succeeds (both with
  `enforce_csrf_checks=True`). A session write sending the `csrftoken`
  cookie's value as `X-CSRFToken` succeeds too.
- API: a signed-out request is a **401** (`WWW-Authenticate: Token`).
- Privacy sentinels: plant the owner's notes, rating and status (and
  another member's rating) and assert none appears in any public page,
  export or API reply.

## Manual testing accounts

`uv run python manage.py seed_demo` creates three demo members with
libraries and packs: `demo_mira`, `demo_otto` and `demo_juno`, password
`toolbox-demo` (see the README). Mira owns the one private pack.

This account is for trying the site in a browser too. It's a regular
member, not staff and not a superuser.

| Username | Password |
|---|---|
| `test_user` | `5eMN9sKdr6cvJB` |

- It's stored in the local `db.sqlite3`, which is git-ignored. On a fresh
  clone, sign up at `/accounts/signup/` with the same details.
- The automated tests never use it; they create users through the fixtures.
- The README lists the same details, so update both if it changes.

## Before finishing a phase

`uv run pytest` is green, and `uv run ruff check .` and
`uv run ruff format --check .` are clean. Ruff skips Markdown files, so
code samples in docs keep their hand wrapping.
