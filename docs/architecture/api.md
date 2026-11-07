# APIs and authentication

`catalog/api.py` + `catalog/serializers.py` (library),
`packs/api.py` + `packs/serializers.py` (packs), `accounts/` (sign-in,
token page, `accounts/tokens.py`). The views are thin: they call the same
functions as the pages. The console client for this API is
`library_client.py` (see the README).

## Authentication

- Django's `LoginView` and `LogoutView` (POST only; GET is 405).
  `accounts.views.SignUpView` (on `UserCreationForm`) signs the new member
  in and honours a same-site `next`.
- `LOGIN_URL = "accounts:login"`; `LOGIN_REDIRECT_URL` and
  `LOGOUT_REDIRECT_URL` are `packs:home`.
- The API tries DRF's `TokenAuthentication` (`Authorization: Token <key>`,
  no CSRF) first, then `SessionAuthentication` (writes must pass CSRF). So
  a signed-out API request is a **401** with `WWW-Authenticate: Token`.
  Every API view needs sign-in (`IsAuthenticated`) unless it says
  otherwise. Replies are JSON only: DRF's browsable API is off (its
  Bootstrap colours sit outside the `axcenity` palette).
- **Token page** (`TokenView`, `/accounts/token/`):
  `Token.objects.get_or_create()` on each visit, `Cache-Control: no-store`
  (`never_cache`). **New token** posts to `accounts:rotate_token`, which
  calls `rotate_token(user)`: one transaction, delete then create (DRF's key
  is the primary key), so the old key stops at once. The one-time message
  comes from `django.contrib.messages`.

## Library API

- **List** (`GET /api/library/`): `filter_library(request.user,
  request.query_params)`, so parameters, fallbacks and order are exactly
  the library page's. Reply: `{count, page, num_pages, next, previous,
  results}`; `next` / `previous` are absolute URLs from
  `LibraryParams.query_string()`. A page past the end is the last.
- **Create** (`POST /api/library/`): `NewLibraryEntrySerializer` checks
  `provider`, `external_id` (1 to 200) and optional `notes`, `rating`,
  `status`, `status_reason` before any provider call (**400** with the
  field's error). Then `save_to_library()`:
  - already in the library: **400** `{"detail": "Already in your library."}`, untouched
  - a `ProviderError`: **502** `{"detail": <its message>}`, nothing stored
  - otherwise **201** with the new entry
- **One entry** (`/api/library/<id>/`): the queryset is `for_user()`, so
  another member's entry is a **404** for every method. PATCH and PUT change
  only `notes`, `rating`, `status` (and `status_reason`), writing just the
  fields sent, so a script and the drawer's autosave never overwrite each
  other. Anything else in the body is ignored. DELETE is **204**; the
  entry's PackItems cascade, the Asset stays (the view's docstring says so,
  served as the `OPTIONS` description).
- **`LibraryEntrySerializer`:** `id`, nested read-only `asset`
  (`AssetSerializer`: Asset fields only, tags as names), `notes`, `rating`,
  `status`, `saved_at`, `community` (`{average, count}` or null),
  `status_change` (`{status, by, via, reason, changed_at}` or null), and
  write-only `status_reason`. A status change records the caller with
  `via: "api"`. Rules match `ReviewForm`.

## Pack API

Read-only: each view defines only GET, so writes are **405** (packs are
changed on the website only). Each sets `permission_classes = [AllowAny]`
and reads through `visible_to()`.

- **List** (`GET /api/packs/`): public plus the caller's own, newest change
  first, 12 a page, in the library API's shape (a bad page is the first,
  past the end the last). `?mine=1` (or `true`, `yes`) lists only the
  caller's and stays in the page links; signed out it's a **401**.
- **Detail** (`/api/packs/<id>/`): the list's fields plus `items`.
- **Export** (`/api/packs/<id>/export/`): the manifest (`manifest_for()`),
  identical to the website download.
- **Serializers:** `PackSerializer` (`id`, `slug`, `title`, `author`,
  `description`, `tags`, `visibility`, `item_count`, `created_at`,
  `updated_at`, absolute `url`, `export_url`, `page_url`).
  `PackDetailSerializer` adds `items` (`PackItemSerializer`: `id`,
  `position`, `preferred_variant`, `import_path`, `default_import_path`,
  nested `asset`). Only Pack, PackItem and Asset fields: nothing from a
  library entry, no community rating.
