# Testing

```sh
uv run pytest                 # whole suite
uv run pytest tests/test_access_control.py -q
uv run pytest --cov           # with coverage
```

## Layout

All tests live in `tests/` and share one `tests/conftest.py`. pytest-django
reads `DJANGO_SETTINGS_MODULE` from `pyproject.toml`. Name files by area:

| File | Covers |
|---|---|
| `test_access_control.py` | The access rules, page by page: who gets 200, who is redirected to sign-in, POST-only sign-out, CSRF rejections |
| `test_accounts.py` | Sign-up and sign-in flows and their validation errors |
| `test_shell.py` | Every page renders in the shell; branding, fonts and static files; no type colour in the chrome; showcase vs work surfaces; boosted navigation, the hover gate and the font gate |
| `test_library_page.py` | The library's layout: the toolbar, the side-panel filters and the empty state |
| `test_auth_pages.py` | Sign-in and sign-up: the layout, the top-bar actions, password toggles, the Forgot password link, focus and error styling |
| `test_theme.py` | `styles/source.css` holds only `axcenity` palette colours |
| `test_network_guard.py` | The guard blocks every kind of unmocked request |
| `test_console_regression.py` | The console script and each provider's `search()` / `get_details()` |

`tests/urls_with_password_reset.py` is a test-only URLconf: the real URLs plus a
stand-in `accounts:password_reset`. Use it with `@pytest.mark.urls(...)` to test
UI that appears only once a URL exists.

## Fixtures every test gets (autouse)

- **`_clear_cache`:** clears Django's cache before and after each test.
- **`_network_guard`:** replaces `socket.getaddrinfo`, `socket.socket.connect`
  and `connect_ex` with a function that raises `NetworkBlockedError`. That
  error is a `RuntimeError`, not an `OSError` or a requests exception, so
  `get_json()` can't turn it into a `ProviderError`. It always fails the
  test. There's no opt-out marker, and none may be added.
- **`_fast_password_hashing`:** uses MD5 hashing in tests, for speed only.

## Other fixtures

| Fixture | Gives |
|---|---|
| `mocked_responses` | A `responses.RequestsMock` that also fails if a registered URL goes unused |
| `password` | The test password (an obvious demo value) |
| `member` | A user named `demo_member` |
| `member_client` | The default `client`, signed in as `member`. It's the same object as `client`, so use `django.test.Client()` when you need a second, signed-out client in the same test |

## Which mocking tool

- **Provider client tests** (code in `providers/`): use `responses`. Fake
  the HTTP and assert on the parsed result or the `ProviderError` message.
- **App tests** (views, services, the API): replace provider functions with
  `monkeypatch.setattr(...)`, so tests never depend on response JSON
  shapes.
- Never call a live API. The guard will fail the test.

## Access and CSRF tests

- Every access rule a phase touches gets a test. Test the website and the
  API wherever both exist.
- Members-only pages: check `302` to `reverse("accounts:login") + "?next=<path>"`.
  Also check that signing in with that `next` comes back to the page.
- Objects the caller doesn't own: check **404**.
- CSRF: use `Client(enforce_csrf_checks=True)` and check that a POST
  without a token gets **403**. The normal test client skips CSRF checks.
- *(planned)* API: a session write without CSRF is refused, and the same
  request with `Authorization: Token <key>` succeeds.

## Manual testing account

Use this account to try the site in a browser. It's a regular member, not
staff and not a superuser.

| Username | Password |
|---|---|
| `test_user` | `5eMN9sKdr6cvJB` |

- It's stored in the local `db.sqlite3`, which is git-ignored. On a fresh
  clone, create it by signing up at `/accounts/signup/` with the same
  details.
- The automated tests never use it. They create their own users through
  the fixtures above.
- The README lists the same details, so update both if it changes.

## Before finishing a phase

`uv run pytest` is green, and `uv run ruff check .` and
`uv run ruff format --check .` are clean. Ruff skips Markdown files, so
code samples in docs keep their hand wrapping.
