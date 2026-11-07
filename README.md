# Axcenity Toolbox

CIDM 3312 Project 2, "Building With APIs".

A Django site, styled like the Axcenity editor, for finding free game assets,
saving them to a private library, and building packs the Axcenity engine can
import. It searches three free providers. None of them needs an API key.

| Provider | Assets | License |
|---|---|---|
| [ambientCG](https://docs.ambientcg.com/api/v3/) | PBR materials, HDRIs, 3D models | CC0 |
| [Poly Haven](https://api.polyhaven.com) | Textures, HDRIs, models | CC0 |
| [Openverse Audio](https://api.openverse.org/v1/) | Sound effects and music | Per item (CC0, CC BY, ...) |

- **Discover** searches every provider at once, with one shelf per
  provider. If one provider is down, its shelf shows an error and a Retry
  button, and the other shelves keep working.
- **Library** keeps each asset you save with your notes, a 1–5 rating, tags
  and a review status. You can search, filter, sort and page through it,
  and it works even when every provider is offline.
- **Packs** group saved assets for one project. Each item has a file
  variant and an import path. A pack is private, unlisted (shared by link)
  or public. It exports as a JSON manifest, or as a zip of its files.
- **Attribution** explains each license and builds the credits and the
  license notice for a pack.
- **The main page** shows a gallery of public packs.
- **The REST API** lets your own scripts work with your library and read
  packs. Your token is on the API token page, where you can also replace it.
- **Two console scripts.** `asset_search.py` (Project 1) still searches the
  providers directly. `library_client.py` calls the Toolbox's own API to
  list your library and change an entry.

The PRD is [prd/axcenity-toolbox.md](prd/axcenity-toolbox.md), and the build
plan is [plans/axcenity-toolbox.md](plans/axcenity-toolbox.md). How the code
fits together: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Contents

1. [Setup](#setup)
2. [Running the site](#running-the-site)
3. [Demo sign-in](#demo-sign-in)
4. [Using the site](#using-the-site)
5. [Testing](#testing)
6. [Using the API with a token](#using-the-api-with-a-token)
7. [The console scripts at a glance](#the-console-scripts-at-a-glance)
8. [The library client (`library_client.py`)](#the-library-client-library_clientpy)
9. [The console script (Project 1)](#the-console-script-project-1)
10. [Troubleshooting](#troubleshooting)
11. [Demo snapshot (maintainers only)](#demo-snapshot-maintainers-only)
12. [Layout](#layout)

## Setup

All you need is [uv](https://docs.astral.sh/uv/). You don't need pip or
Node. If Python 3.13 isn't installed, uv installs it, and SQLite comes with
Python.

```sh
git clone <this repository>
cd project-two-building-with-apis
uv sync                                   # install the dependencies
uv run python manage.py migrate           # create db.sqlite3
uv run python manage.py seed_demo         # load the demo members, libraries and packs
```

`seed_demo` works offline. It loads a saved snapshot of 43 real assets
(`packs/demo_assets.json`), so it never calls a provider. The first run
reports `Created 3 users, 43 assets, 53 library entries, 7 packs ...`. It's
safe to run again at any time:

- it adds only what's missing and never duplicates anything
- it resets the demo passwords
- it puts the demo packs back the way they were defined
- it leaves your own changes to library entries alone

To start over with an empty database, delete `db.sqlite3` and run `migrate`
and `seed_demo` again.

## Running the site

```sh
uv run python manage.py tailwind runserver
```

Then open <http://127.0.0.1:8000/>.

This command starts Django and the Tailwind watcher together. On the first
run it downloads Tailwind's standalone binary (with DaisyUI built in) into
`.django_tailwind_cli/` and builds `static/css/tailwind.css`. Git ignores
both. To build the CSS once without starting the server, run
`uv run python manage.py tailwind build`.

Discover needs the internet to search the providers. Everything else works
offline on the seeded data, including the library, packs, the gallery,
exports and the API.

## Demo sign-in

`seed_demo` creates three regular members (not staff). They all share the
same password, which is plainly a fake:

| Username | Password | What they have |
|---|---|---|
| `demo_mira` | `toolbox-demo` | Medieval Village and Golden Hour Skies (public), Castle Siege (private) |
| `demo_otto` | `toolbox-demo` | Sci-fi Corridor and Desert Outpost (public) |
| `demo_juno` | `toolbox-demo` | Forest Ambience and Bakery Props (public; the bakery's market sound is non-commercial) |

Every library has entries in each status (To review, Testing, Approved,
Rejected), a range of ratings, and some notes. Several members rated the
same few assets, so those assets show a community rating.

There's also a regular test account for trying the site by hand,
`test_user` with the password `5eMN9sKdr6cvJB`. `seed_demo` doesn't create
it. On a fresh clone, create it at `/accounts/signup/` with those details.
The automated tests never use it.

## Using the site

The left side panel holds each page's navigation and filters. The title bar
has the colour scheme switch (System, Light or Dark). Visitors can browse
the main page, Discover, public packs and the license guide. Saving
anything requires an account.

### A ten-minute tour

1. **Browse as a visitor.** Open <http://127.0.0.1:8000/>. The main page
   shows the public pack gallery. Search it, filter it by asset type, and
   sort it by newest or most items. Open **Medieval Village** to see a pack
   page.
2. **Sign in** as `demo_mira` / `toolbox-demo` (or sign up at
   `/accounts/signup/`).
3. **Discover** (`/discover/`). Pick a type tile (Textures, HDRIs, Models or
   Sounds) and search, for example `brick` or `footsteps`. Each provider
   gets its own shelf. Use **Load more** to page a shelf and **Shuffle** to
   get a random suggestion. Open a result with **Details**, or play a
   sound. The side panel filters results by license and commercial use.
4. **Save** a result. The corner check means it's in your library, and the
   saved count in the status bar goes up. **Add to pack** saves the asset
   first if you haven't already.
5. **Library** (`/library/`). Search, filter by type, provider, status,
   minimum rating or tag, sort, and page through 12 cards at a time. Open a card to change its status (with an optional reason), rating
   or notes. Each change saves by itself, so there's no Save button. The
   drawer also shows the asset's license, files, status history, similar
   entries, and public packs that use it. **Download bundle** zips the files
   you chose in Settings.
6. **Packs** (`/packs/`). Choose **New pack**, give it a title, then add
   items with **Add from my library** or from **Suggested for this pack**.
   In the builder, choose each item's file variant and import path, drag
   items to reorder them (or use an automatic sort), and set the pack to
   Private, Unlisted or Public. An unlisted pack gets a share link, and
   **New link** retires the old one.
7. **Pack page** (`/packs/<slug>/`). This is the read-only view everyone
   else sees. It has **Download manifest** (the
   `<slug>.axcenity-pack.json` the engine imports), **Download files** (a
   zip built in your browser that holds each file under its import path,
   plus `CREDITS.txt` and the manifest), and the pack's attribution. Other
   members can **Save** single items or **Copy pack** into their own
   account.
8. **Attribution** (`/attribution/`). A guide to every license the
   providers use: what you may do, what you must do and what you may not
   do, with a verdict for commercial, personal and internal use. Members
   also get attribution for their own packs and their saved assets. A pack
   with a non-commercial item gets a warning.
9. **Account**. **Profile**, **Settings** (colour scheme and the default
   download resolution, format and maps) and **API token** (see
   [Using the API with a token](#using-the-api-with-a-token)).

### Checking access by hand

These are quick checks you can run in a browser:

| Try | Expected |
|---|---|
| Sign out, then open `/library/` or `/packs/` | Redirected to sign in, then back to that page |
| As `demo_otto`, open Mira's private pack (`/packs/castle-siege-work-in-progress/`) | 404 page |
| As `demo_otto`, open `/library/<id>/` for an entry that isn't his | 404 page |
| Make a pack Unlisted and open its share link in a private window | The pack page opens; the slug URL is a 404 for anyone but you |
| Press **New link**, then reload the old link | 404 page |
| Open Juno's Bakery Props attribution | A warning that the pack isn't cleared for commercial use |

## Testing

The project has two kinds of tests: an automated pytest suite that covers
the site, the API, the providers and the console script, and a manual
checklist for the console script against the live APIs (see
[How to verify by hand](#how-to-verify-by-hand)).

### Running the suite

```sh
uv run pytest                         # the whole suite (about 1,300 tests, around 15 s)
uv run pytest -q                      # quieter output
uv run pytest -x --lf                 # stop at the first failure, rerun only last failures
uv run pytest -k "share_link"         # only tests whose names match
uv run pytest tests/test_api_packs.py # one file
uv run pytest --cov                   # with coverage
uv run ruff check .                   # lint
uv run ruff format --check .          # formatting (drop --check to apply it)
```

The suite must pass, and Ruff must be clean, before any commit.

### Rules the suite follows

- **No test reaches the network.** An autouse guard in `tests/conftest.py`
  blocks every socket connection and fails any test that tries one.
  Nothing can switch it off. So the suite runs offline and gives the same
  result every time.
- **Provider clients** (`providers/`) are tested against faked HTTP
  responses from the [`responses`](https://github.com/getsentry/responses)
  library. The site's views and services are tested by replacing provider
  functions with `monkeypatch`.
- **Every access rule is tested** on the website and the API: sign-in
  redirects, **404** for anything the caller doesn't own, **401** for a
  signed-out API call, and **403** for a write without a CSRF token.
- **All tests live in `tests/`**, one file per area, with one shared
  `conftest.py` for fixtures (`member`, `member_client`, `make_asset`,
  `mocked_responses` and more).

### What each file covers

| Area | Files |
|---|---|
| Access rules and CSRF, page by page | `test_access_control.py` |
| Accounts, sign-in pages, theme, API token page | `test_accounts.py`, `test_auth_pages.py`, `test_theme.py`, `test_theme_switch.py`, `test_token_page.py` |
| Providers | `test_provider_records.py`, `test_provider_fetch.py`, `test_provider_failures.py`, `test_network_guard.py` |
| Discover | `test_discover.py`, `test_discover_drawer.py`, `test_discover_licenses.py` |
| Library | `test_library_page.py`, `test_library_filter.py`, `test_library_drawer.py`, `test_library_save.py`, `test_status_history.py`, `test_community_rating.py`, `test_entry_related.py`, `test_tags.py`, `test_downloads.py`, `test_sound_playback.py` |
| Packs | `test_packs.py`, `test_pack_builder.py`, `test_pack_public.py`, `test_pack_share.py`, `test_pack_copy.py`, `test_pack_downloads.py`, `test_pack_suggestions.py`, `test_pack_layout.py` |
| Attribution and licenses | `test_attribution.py` |
| Main page and gallery | `test_home.py`, `test_home_hero.py`, `test_gallery.py` |
| REST API | `test_api_library.py`, `test_api_packs.py` |
| Demo data | `test_seed_demo.py` |
| Page shell, motion, scroll ruler | `test_shell.py`, `test_motion.py`, `test_scroll_ruler.py` |
| Console scripts | `test_console_regression.py` (Project 1), `test_library_client.py` (the library client) |

[docs/TESTING.md](docs/TESTING.md) covers the fixtures and when to use
each mocking tool, and [docs/testing/test-files.md](docs/testing/test-files.md)
describes what each file covers.

> `test_seed_demo.py` checks that this README lists the demo usernames and
> password in the table above. If you change them in `packs/demo.py`,
> update the table too.

## Using the API with a token

1. Sign in, then open **Account → API token** (`/accounts/token/`). The
   site creates your token the first time you open the page. **Copy
   token** puts it on your clipboard.
2. Send it in the `Authorization` header as `Token <key>`. Requests that
   use a token don't need a CSRF token.
3. Keep it private: anyone holding it can read and change your library.

### Replacing your token

If your token has leaked (pasted in a chat, committed to Git, shown on a
shared screen), or you just want a fresh one, press **New token** on the
API token page and confirm. Then:

- **The old token stops working at once.** Any request signed with it gets
  **401**, including from `library_client.py`.
- **The page shows the new token**, with "New token made. The old one no
  longer works, so update your scripts." That message shows once.
- **Nothing else changes.** Your library, packs, sign-in and other members'
  tokens are untouched.
- **Update anything that stores the old key**, such as a `TOKEN` or
  `TOOLBOX_TOKEN` variable, a `.env` file or a saved curl command.

The button posts to `/accounts/token/rotate/` (members only, POST only,
with CSRF). There's no API endpoint for it, so a stolen token can't be used
to replace itself and lock you out.

### Calling the API

```sh
TOKEN=<your key>
BASE=http://127.0.0.1:8000

# Your library: the same search, filters, sorts and pages of 12 as the website.
curl -H "Authorization: Token $TOKEN" "$BASE/api/library/?type=texture&sort=rating"

# Save an asset by provider and ID (the server fetches the rest).
curl -H "Authorization: Token $TOKEN" -H "Content-Type: application/json" \
     -d '{"provider": "polyhaven", "external_id": "red_bricks_02", "status": "testing"}' \
     "$BASE/api/library/"

# Read, update or delete one entry (deleting it also removes it from your packs).
curl -H "Authorization: Token $TOKEN" "$BASE/api/library/1/"
curl -X PATCH -H "Authorization: Token $TOKEN" -H "Content-Type: application/json" \
     -d '{"rating": 5, "notes": "Tiles well."}' "$BASE/api/library/1/"
curl -X DELETE -H "Authorization: Token $TOKEN" "$BASE/api/library/1/"

# Packs: public packs plus your own (?mine=1 for only yours), one pack, its manifest.
curl -H "Authorization: Token $TOKEN" "$BASE/api/packs/?mine=1"
curl "$BASE/api/packs/1/"
curl "$BASE/api/packs/1/export/"
```

On Windows PowerShell, use `curl.exe` (plain `curl` is an alias for
`Invoke-WebRequest`) and `$env:TOKEN` in place of `$TOKEN`. The API
answers in JSON only.

| Endpoint | Methods | Who |
|---|---|---|
| `/api/library/` | GET, POST | Signed in (401 otherwise) |
| `/api/library/<id>/` | GET, PATCH, PUT, DELETE | The entry's owner (404 for anyone else) |
| `/api/packs/` | GET | Anyone. `?mine=1` needs sign-in |
| `/api/packs/<id>/`, `/api/packs/<id>/export/` | GET | Anyone for a public pack, only the owner for a private or unlisted one (404 otherwise) |

Saving an asset that's already in your library returns **400** with
"Already in your library.". If the provider fails during a save, the API
returns **502** with a friendly `detail` message. Packs are read-only
through the API, so any write gets **405**.

## The console scripts at a glance

The project has two console scripts. Both run with `uv run` from the
project folder and need no extra install.

| | `asset_search.py` (Project 1) | `library_client.py` |
|---|---|---|
| Talks to | ambientCG, Poly Haven and Openverse directly | your running Toolbox site's API |
| Needs | the internet | the site running, and your API token |
| Does | searches providers, looks up one asset by ID, shows files and downloads | lists your library, changes one entry's status, rating or notes |
| Writes anything? | no | yes: one entry per run, through `PATCH /api/library/<id>/` |
| Run | `uv run asset_search.py` | `uv run library_client.py` |
| Tests | `tests/test_console_regression.py` | `tests/test_library_client.py` |

They work well together:

1. **Find** an asset with `asset_search.py`. Its details view shows the ID
   in brackets, for example `[red_bricks_02]`.
2. **Save** it to your library, either from Discover on the site or by ID
   through the API (no script needed):

   ```sh
   curl -H "Authorization: Token $TOKEN" -H "Content-Type: application/json" \
        -d '{"provider": "polyhaven", "external_id": "red_bricks_02"}' \
        http://127.0.0.1:8000/api/library/
   ```

   The provider keys are `ambientcg`, `polyhaven` and `openverse`.
3. **Review** it with `library_client.py`. Move it from To review to
   Testing, rate it, or add notes, from the console.

## The library client (`library_client.py`)

`library_client.py` is a console script that uses the Toolbox's own REST
API, the same one your own scripts can use. It:

1. lists every entry in your library (`GET /api/library/`, following each
   page of 12)
2. lets you pick one, and a new status, rating or notes for it
3. prints the entry before the change, sends `PATCH /api/library/<id>/`,
   and prints the entry the server sends back

It uses `requests`, which the project already installs, and signs each
request with `Authorization: Token <key>`.

### Before you run it

1. **Start the site** in another terminal:

   ```sh
   uv run python manage.py tailwind runserver   # or plain: uv run python manage.py runserver
   ```

2. **Have something in your library.** Sign in and save a few assets from
   Discover, or load the demo data with `uv run python manage.py seed_demo`
   and sign in as a demo member (see [Demo sign-in](#demo-sign-in)).
3. **Copy your token** from **Account → API token**
   (<http://127.0.0.1:8000/accounts/token/>).

### Running it

```sh
uv run library_client.py
```

It asks for:

1. **Server:** press Enter for `http://127.0.0.1:8000`, or type another
   address such as `127.0.0.1:8001` (`http://` is added if you leave it
   off).
2. **API token:** paste it. It isn't shown as you type.
3. **Entry:** the number of the entry to change, or Enter to quit without
   changing anything.
4. **Field:** `1` Status, `2` Rating or `3` Notes.
5. **New value:**
   - **Status:** `1` To review, `2` Testing, `3` Approved, `4` Rejected.
     The current one is marked. Then an optional **reason**, which the
     site records with the change and shows in the entry's status history.
   - **Rating:** `1` to `5`, or Enter to clear the rating.
   - **Notes:** the new notes, or Enter to clear them. The current notes
     are shown first. This replaces the notes; it doesn't add to them.

A number that's out of range gets "Please enter a number from 1 to N." and
the same prompt again. Ctrl+C at any prompt exits cleanly. Each run changes
one field of one entry; run it again for the next change.

### Skipping the prompts with environment variables

Set these and the script skips the matching prompt. That's handy when you
run it often, or when you'd rather not paste the token each time.

| Variable | Instead of | Example |
|---|---|---|
| `TOOLBOX_URL` | the Server prompt | `http://127.0.0.1:8001` |
| `TOOLBOX_TOKEN` | the API token prompt | your key from the token page |

macOS, Linux or Git Bash:

```sh
export TOOLBOX_TOKEN=<your key>
export TOOLBOX_URL=http://127.0.0.1:8000            # optional
uv run library_client.py

TOOLBOX_TOKEN=<your key> uv run library_client.py   # for one run only
unset TOOLBOX_TOKEN                                 # forget it
```

Windows PowerShell:

```powershell
$env:TOOLBOX_TOKEN = "<your key>"
$env:TOOLBOX_URL = "http://127.0.0.1:8000"   # optional
uv run library_client.py
Remove-Item Env:TOOLBOX_TOKEN                # forget it
```

A variable set this way lasts until you close the terminal. Don't commit a
token to the repo. If one ends up somewhere it shouldn't, replace it (see
[Replacing your token](#replacing-your-token)).

With both variables set, the only prompts left are the entry, field and
value, so you can pipe the answers in. This approves entry 2 with a
reason (macOS, Linux or Git Bash):

```sh
printf '2\n1\n3\nLooks right in engine\n' | uv run library_client.py
```

In PowerShell: `"2","1","3","Looks right in engine" | uv run library_client.py`.
The numbers follow the list's order, which is newest saved first, so check
the list before you script a change.

### Sample run

```
Axcenity Toolbox library client
Server [http://127.0.0.1:8000]:

Your library (3 entries):
    1) Red Bricks 02  [texture, polyhaven]  Approved, 5/5
    2) Rogland Sunset  [hdri, polyhaven]  Testing, 4/5
    3) Footsteps, Stones, A.wav  [sound, openverse]  To review, unrated
Choose an entry (blank to quit): 2

What do you want to change?
  1) Status
  2) Rating
  3) Notes
Field: 1
New status:
  1) To review
  2) Testing  (current)
  3) Approved
  4) Rejected
Status: 3
Reason (optional): Lights the courtyard scene well

Before:
  #7  Rogland Sunset (hdri, polyhaven)
  Status:  Testing
  Rating:  4/5
  Notes:   (none)

Sending PATCH /api/library/7/ {'status': 'approved', 'status_reason': 'Lights the courtyard scene well'}

After:
  #7  Rogland Sunset (hdri, polyhaven)
  Status:  Approved
           set by demo_member via api: Lights the courtyard scene well
  Rating:  4/5
  Notes:   (none)
```

Open the entry on the site's Library page afterwards: the change is
there, and its status history shows it came through the API.

### When something goes wrong

Every failure prints one `Error:` line and exits with code 1, so a script
that calls it can tell.

| You see | Why | Fix |
|---|---|---|
| `Can't reach the Toolbox at ... Is the server running?` | Nothing is listening at that address | Start the site, or check the port in `TOOLBOX_URL` |
| `The server didn't accept that token.` | The token is wrong, has a typo, or was replaced | Copy it again from the token page; update `TOOLBOX_TOKEN` |
| `Your library is empty.` | You haven't saved anything yet | Save assets from Discover, or run `seed_demo` and sign in as a demo member |
| `The server rejected the change:` and a field's reason | The value broke a rule, such as notes over 10,000 characters or a status reason over 300 | Shorten it and run again |
| `That entry isn't in your library any more.` | It was removed (on the site, or by another script) after the list loaded | Run again for a fresh list |
| `... didn't answer like the Toolbox API` | The address points at something else | Check the server address |
| `... took too long to answer.` | The server didn't reply within 10 s | Check the site's terminal for errors and try again |

### Its tests

```sh
uv run pytest tests/test_library_client.py -v
```

They run offline. Most answer the script's requests with canned
`responses`. Two hand each request to Django's test client, so the script
runs against the real API views: one saves a rating, and one checks that
a wrong token changes nothing.

## The console script (Project 1)

The original console script still works, unchanged. It searches the same
three providers and shows the results in the terminal:

```
asset_search.py          interactive console script (prompts, tables, details)
providers/
  http.py                get_json(): User-Agent, 10 s timeout, ProviderError
  formatting.py          human-readable sizes (KB/MB/GB) and m:ss durations
  ambientcg.py           search() and get_details() for ambientCG
  polyhaven.py           search() and get_details() for Poly Haven
  openverse.py           search() and get_details() for Openverse Audio
```

The website reuses these same provider modules. Its own functions
(`search_records()`, `fetch_record()`) sit next to the original `search()`
and `get_details()`, which never change.

Openverse limits anonymous clients to 20 requests per minute and 200 per
day.

### How to run

```
uv sync
uv run asset_search.py
```

The script asks:

1. **Provider:** `1` ambientCG, `2` Poly Haven, `3` Openverse Audio, `q` to quit.
2. **Search or ID lookup:** Enter (or `s`) to search, `i` to look up one asset by ID.
3. **Search phrase:** for example `brick`, `sunset`, `chair` or `footsteps`.
4. **Asset type** (ambientCG and Poly Haven only): Enter for Any, or
   `2` Textures/materials, `3` HDRIs, `4` Models.
5. **Details:** the number of a result to see its details, or Enter to skip.
6. **Search again?** Enter or `y` to go back to the provider menu, `n` to exit.

Ctrl+C at any prompt exits cleanly.

### Getting the most out of it

- **Look up by ID** (`i`) when you already know the asset. It skips the
  search and goes straight to the details: every map, bundle, resolution,
  format and download size, with direct URLs.
- **Use the type filter** on ambientCG and Poly Haven to cut the noise:
  `3` HDRIs for `sky` or `sunset`, `4` Models for `chair` or `barrel`.
- **Try more than one phrase.** Each provider names things its own way
  (`brick`, `bricks`, `wall`), and Poly Haven's search is semantic, so it
  returns its closest matches rather than nothing.
- **Copy an ID into the Toolbox.** The ID in brackets is the
  `external_id` the API's save takes (see
  [The console scripts at a glance](#the-console-scripts-at-a-glance)).
- **Pipe the answers in** to repeat a lookup without typing. The script
  stops cleanly when the input runs out:

  ```sh
  printf '2\ni\nrogland_sunset\nn\n' | uv run asset_search.py   # Poly Haven, ID lookup
  printf '1\n\nbrick\n\n1\nn\n' | uv run asset_search.py        # ambientCG, search, details of #1
  ```

  In PowerShell: `"2","i","rogland_sunset","n" | uv run asset_search.py`.
- **Save the output** to a file by adding `> results.txt` to any of those
  commands. The prompts go into the file too.
- **Mind Openverse's limits:** 20 requests a minute and 200 a day for
  anonymous clients. Each search is one request, and each details view is
  one more.

Asset IDs for the lookup look like `Bricks097` (ambientCG), `red_bricks_02`
(Poly Haven) and `a8783d20-f1af-4c4b-b9ec-a8c212f67fee` (Openverse). The
ID of every result is shown in brackets in its details view.

### Automated tests

`tests/test_console_regression.py` checks the script and its provider calls
against canned responses, so it runs offline:

```sh
uv run pytest tests/test_console_regression.py -v
```

It covers:

- **Each provider's `search()`:** the query and filters it sends, the rows
  it returns, and an empty result. This includes Poly Haven's rule that
  zero keyword matches means no results.
- **Each provider's `get_details()`:** the fields, files and downloads it
  summarizes, and Openverse's license labels.
- **Failures:** a timeout, a connection error, a 429 that mentions
  retrying later, a Poly Haven 404, an unknown ambientCG ID, and an
  Openverse 500 whose HTML body never reaches the user. Each one becomes a
  `ProviderError` with a friendly message.
- **The script end to end, with typed answers:** a search then details, a
  provider error that prints `Error:` and keeps the script running, and
  quitting straight away.

These tests are the guarantee that the website's changes to `providers/`
never broke Project 1.

### How to verify by hand

To check the script against the live APIs, run it and try each case below.
Live data changes over time, so names and counts may differ from the
samples.

| # | Provider | Input | Expected |
|---|---|---|---|
| 1 | ambientCG | search `brick`, type Enter, details `1` | 5-row table, then maps, dimensions and every download with size and URL |
| 2 | ambientCG | search `sky`, type `3` (HDRIs) | only `hdri` rows |
| 3 | Poly Haven | search `brick`, type `2`, details `3` | texture rows with max resolution and physical size, then sizes per resolution and bundles |
| 4 | Poly Haven | ID lookup `rogland_sunset` | HDRI details with `exr`/`hdr` sizes from 1k to 24k |
| 5 | Openverse | search `footsteps`, details `1` | audio rows with duration, then creator, bit rate, license and attribution |
| 6 | any | search `zzqqxx` | `No <provider> matches for 'zzqqxx'...`, then back to the menu |
| 7 | ambientCG | ID lookup `NotAnAsset999` | `Error: ambientCG has no asset with ID 'NotAnAsset999'.` |
| 8 | Poly Haven / Openverse | ID lookup `bad_id` | `Error: ... has nothing at that address (HTTP 404)...` |
| 9 | any | `9` at the provider menu, `x` at search/ID, blank phrase, `abc` at a number prompt | a "Please enter..." message and the same prompt again |
| 10 | any | unplug the network and search | `Error: Could not connect to ...` |

The script reports other failures the same way: one `Error:` line, then the
"Search again?" prompt. These failures are:

- a timeout after 10 s
- HTTP 429, with a note about Openverse's limits of 20 a minute and 200 a day
- any other HTTP 5xx
- a response that isn't JSON

#### Sample output

ambientCG search and details (case 1, downloads trimmed):

```
Searching ambientCG for 'brick'...

#  Name        Type      Info                  License
-  ----------  --------  --------------------  -------
1  Ground 111  material  5 maps, 8 downloads   CC0
2  Ground 107  material  5 maps, 8 downloads   CC0
3  Bricks 097  material  5 maps, 8 downloads   CC0
4  Bricks 060  material  5 maps, 8 downloads   CC0
5  Bricks 100  material  5 maps, 12 downloads  CC0

Show details for # (1-5) [Enter = skip]: 1

Fetching details for 'Ground111' from ambientCG...

Ground 111  [Ground111]
  Type:           material
  Maps:           color, displacement, normal, roughness, ambient-occlusion
  Dimensions:     280 x 280 x 0 (W x H x D)
  License:        CC0
  Page:           https://ambientcg.com/a/Ground111

  Downloads (8):
    1K-JPG           .zip       9.3 MB  https://ambientcg.com/get?file=Ground111_1K-JPG.zip
    2K-JPG           .zip      32.8 MB  https://ambientcg.com/get?file=Ground111_2K-JPG.zip
    ...
    8K-PNG           .zip      1.07 GB  https://ambientcg.com/get?file=Ground111_8K-PNG.zip
```

Poly Haven details (case 3):

```
Red Bricks 02  [red_bricks_02]
  Type:           texture
  Max resolution: 8192x8192
  Physical size:  2.5 x 2.5 m
  Authors:        Rob Tuytel (All)
  Downloads:      24,181
  License:        CC0
  Page:           https://polyhaven.com/a/red_bricks_02

  Map files, total size per format:
      8k  exr 594.1 MB, jpg 239.3 MB, png 1.93 GB
      4k  exr 147.3 MB, jpg 56.2 MB, png 481.9 MB
      2k  exr 36.9 MB, jpg 14.2 MB, png 124.4 MB
      1k  exr 9.7 MB, jpg 3.8 MB, png 31.9 MB

  Bundles (file plus included textures):
    blend  8k 238.2 MB, 4k 66.9 MB, 2k 17.9 MB, 1k 4.9 MB
    gltf   8k 90.3 MB, 4k 25.7 MB, 2k 8.4 MB, 1k 3.9 MB
    mtlx   8k 238.0 MB, 4k 66.7 MB, 2k 17.6 MB, 1k 4.6 MB
```

Openverse search and details (case 5):

```
#  Name                          Type   Info                        License
-  ----------------------------  -----  --------------------------  ---------
1  Footsteps, Stones, A.wav      audio  0:19, mp3, by InspectorJ    CC BY 4.0
2  Footsteps, Concrete, A.wav    audio  0:40, mp3, by InspectorJ    CC BY 4.0
3  footstep on wood foley.wav    audio  0:17, mp3, by martian       CC0 1.0
4  Footsteps on Tiles.wav        audio  0:24, mp3, by RutgerMuller  CC0 1.0
5  Footsteps, Dry Leaves, G.wav  audio  0:29, mp3, by InspectorJ    CC BY 4.0

Footsteps, Stones, A.wav  [a8783d20-f1af-4c4b-b9ec-a8c212f67fee]
  Creator:        InspectorJ
  Source:         freesound
  Duration:       0:19
  Bit rate:       128 kbps
  File:           mp3, 485.2 KB
  License:        CC BY 4.0  https://creativecommons.org/licenses/by/4.0/
  Attribution:    "Footsteps, Stones, A.wav" by InspectorJ is licensed under CC BY 4.0. ...

  Other formats:
    wav       3.2 MB  44,100 Hz  https://freesound.org/apiv2/sounds/345560/download/
```

Empty result and bad ID (cases 6 and 8):

```
Searching Poly Haven for 'zzqqxx'...
No Poly Haven matches for 'zzqqxx'. Try a different or broader phrase.

Fetching details for 'bad_id' from Poly Haven...

Error: Poly Haven has nothing at that address (HTTP 404). If you entered an asset ID, check it and try again.
```

Notes:

- Poly Haven's search is semantic, so it never returns an empty list. The
  script treats a search with zero keyword matches as "no results".
- ambientCG doesn't document the unit of `dimensions`, so the script shows
  the numbers exactly as the API returns them.
- Openverse can be slow. On 2026-10-30 some uncached searches took 30 to
  60 seconds, so the 10 s timeout fired and the script printed a timeout
  error. If that happens, try again later or try a different phrase.

## Troubleshooting

| Problem | Fix |
|---|---|
| Tailwind fails with **WinError 4551** on Windows | Windows Smart App Control is blocking the standalone binary in `.django_tailwind_cli/`; the code isn't the cause. Allow the binary, or turn Smart App Control off |
| The page has no styles | Run `uv run python manage.py tailwind build`, or start the site with `tailwind runserver` rather than plain `runserver` |
| Discover shows an error on one shelf | That provider is down, slow or rate-limited. Press Retry, or wait. Openverse allows 20 requests a minute and 200 a day |
| Port 8000 is in use | `uv run python manage.py tailwind runserver 8001` |
| The demo packs have changed | Run `uv run python manage.py seed_demo` again |
| A demo password doesn't work | Run `seed_demo` again. It resets the demo passwords |
| `library_client.py` can't reach the Toolbox | Start the site first. If it runs on another port, set `TOOLBOX_URL` or type the address at the prompt |
| `library_client.py` says the token wasn't accepted | Copy it again from the token page. If you pressed New token, the old one no longer works |
| A token may have leaked | Press **New token** on the API token page. The old one stops working at once |

## Demo snapshot (maintainers only)

`packs/demo.py` names each demo asset, pack and review. The snapshot was
captured once, online, with:

```sh
uv run python manage.py capture_demo_assets
```

It calls each provider's `fetch_record()` for every demo asset and rewrites
`packs/demo_assets.json`. If any asset fails to fetch, it writes nothing.
Graders don't need to run it.

## Layout

```
config/       settings, root URLs, the shell's context processor
providers/    API clients for ambientCG, Poly Haven and Openverse (plain Python)
catalog/      Discover, the library, saving, and the library API
packs/        packs, the builder, pack pages, export, the gallery, attribution,
              the pack API, demo data
accounts/     sign-up, sign-in, profile, settings and the API token page
templates/    the shared shell (base.html) and partials
static/       branding, fonts and scripts
styles/       source.css, Tailwind's source
tests/        every test, with one shared conftest
docs/         ARCHITECTURE.md, FRONTEND.md and TESTING.md (indexes), with
              one topic file per area in architecture/, frontend/ and testing/
asset_search.py   the Project 1 console script (calls the providers)
library_client.py the library client (calls the Toolbox's own API)
```
