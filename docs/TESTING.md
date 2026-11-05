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
| `test_access_control.py` | The access rules, page by page: who gets 200, who is redirected to sign-in, POST-only sign-out, CSRF rejections, a visitor's status bar holding provider status only, saving (sign-in back to Discover, CSRF), the saved count counting only the member's own entries, a visitor's library view (and its fragment's `HX-Redirect`) going to sign-in and back, library parameters never showing another member's entries, and Remove (sign-in, another member's entry is a 404, CSRF) and tags never showing another member's entries or tags. The drawer: another member's entry is a 404 to view and to every update, a visitor is sent to sign in and back (an HTMX save gets a 401 that keeps the text), and updates need CSRF |
| `test_accounts.py` | Sign-up and sign-in flows and their validation errors |
| `test_shell.py` | Every page renders in the shell; the one-column sidebar (each icon beside its label, the strip when collapsed); branding, fonts and static files; no type colour in the chrome, and in content only on Discover's tiles; showcase vs work surfaces; boosted navigation, the hover gate and the font gate |
| `test_library_page.py` | The library's layout (the toolbar, the side-panel chips, disabled while empty) and its grid: newest first, each card's thumbnail, type, title, status and rating, provider URLs only, a member's own entries only, and rendering with every provider down. Browsing: the HTMX fragment versus the full page in the same state, boosted and history-restore requests, the pushed URL, the pager and both empty states. Tags, corner actions and Remove: the Tags chips with their counts, each card's corner actions, details and pickers, the stars clear of DaisyUI's `.rating`, and Remove (the asset stays, the same view comes back, a page that empties falls back) |
| `test_library_filter.py` | `filter_library()` called directly: never another member's entries, each search field, each filter, each sort (rating with unrated last), pages of 12, combinations, bad values falling back to the defaults, and the tidy URL. Tags: every chosen tag from any provider, tidied values, never another member's, `Tag.objects.in_library()` and the Tags chips |
| `test_library_drawer.py` | The drawer and the entry page: the fragment versus the full page, the details, license, source and files, the stored review, one field per form with no Save button, rendering with every provider down, saving only the posted field, the rating 1 to 5 or cleared, 400s that save nothing, the card out of band (status and rating from the library only), notes surviving a reload as typed, and Remove from the drawer or the page |
| `test_community_rating.py` | The community rating: every member's rating averaged, unrated entries skipped, one row per entry, the Discover lookup by ID, the `community` sort, and the cards, drawer and Discover results showing the average and count, never who rated or their notes |
| `test_library_save.py` | Saving: the shared Asset reused across members, one entry per member, nothing saved on a `ProviderError`, new entries To review, the model constraints, the save view's replies and 400s, and "In library" (a corner check, never the logo mark) on Discover's shelves |
| `test_tags.py` | `normalize_tag()`, rule by rule |
| `test_auth_pages.py` | Sign-in and sign-up: the layout, the top-bar actions, password toggles, the Forgot password link, focus and error styling |
| `test_theme.py` | `styles/source.css` holds only `axcenity` palette colours, and every block in it is closed once |
| `test_network_guard.py` | The guard blocks every kind of unmocked request |
| `test_console_regression.py` | The console script and each provider's `search()` / `get_details()` |
| `test_provider_records.py` | `search_records()` and `AssetRecord`: the PRD mapping and filters, every field filled, the 12 limit, Poly Haven's `/info` calls and their 12 h cache, paging for Load more, malformed answers, and safe messages with their details logged |
| `test_provider_fetch.py` | `fetch_record()` for each provider (`responses`): every field and variant, every file URL kept, Poly Haven's cached `/info`, and a safe message for an unknown ID, a malformed answer or an ID that isn't a slug |
| `test_provider_failures.py` | Story 83 at the HTTP level: a timeout, a connection error, a 429, Openverse's 500 with HTML, Poly Haven's 404 and `keywordMatches == 0`, each with its exact friendly message and no leaked text |
| `test_discover.py` | Discover: shelf URL validation, mixed shelves for every failure, the page's pending shelves, tiles, command bar and `/` shortcut, each shelf state, the search cache, credits, fallback icons, provider status, the random pick and Shuffle, Load more, sound previews, the hover details, the Details toggle, square texture thumbnails and the corner actions |

`tests/urls_with_password_reset.py` is a test-only URLconf: the real URLs plus a
stand-in `accounts:password_reset`. Use it with `@pytest.mark.urls(...)` to test
UI that appears only once a URL exists.

## Fixtures every test gets (autouse)

- **`_clear_cache`:** clears Django's cache before and after each test. The
  Toolbox installs that same cache into `providers.cache`, so Poly Haven's
  cached `/info` answers are cleared too.
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
| `provider_calls` (in `test_discover.py`) | Replaces every provider's `search_records` and records each call, to prove a request never reached a provider |
| `member_client` | The default `client`, signed in as `member`. It's the same object as `client`, so use `django.test.Client()` when you need a second, signed-out client in the same test |
| `make_asset` | A factory for stored `Asset`s with sensible defaults (`make_asset(external_id=..., kind=..., **fields)`) |

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
