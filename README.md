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

- **Discover** searches the providers side by side, one shelf per provider.
  A provider that's down shows its own error and a Retry button, and the
  other shelves keep working.
- **Library** keeps each saved asset with your notes, a 1–5 rating and a
  status. You can search, filter, sort and page through it, and it works
  with every provider offline.
- **Packs** group saved assets for one project. Each item has a file
  variant and an import path. A pack is private, unlisted or public, and
  exports as a JSON manifest.
- **The main page** has a gallery of public packs.
- **The REST API** lets your own scripts work with your library and read
  packs.

The PRD is [prd/axcenity-toolbox.md](prd/axcenity-toolbox.md), and the build
plan is [plans/axcenity-toolbox.md](plans/axcenity-toolbox.md). How the code
fits together: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Setup

You need [uv](https://docs.astral.sh/uv/) and nothing else: no pip, no Node.
uv installs Python 3.13 if you don't have it, and SQLite comes with Python.

```sh
git clone <this repository>
cd project-two-building-with-apis
uv sync                                   # install the dependencies
uv run python manage.py migrate           # create db.sqlite3
uv run python manage.py seed_demo         # load the demo members, libraries and packs
```

`seed_demo` works offline. It loads a committed snapshot of 43 real assets
(`packs/demo_assets.json`), so it never calls a provider. You can run it
again at any time:

- it adds only what's missing and never duplicates anything
- it resets the demo passwords
- it puts the demo packs back as they were defined
- it leaves your own changes to library entries alone

## Running the site

```sh
uv run python manage.py tailwind runserver
```

Then open <http://127.0.0.1:8000/>.

This runs Django and the Tailwind watcher together. The first run downloads
Tailwind's standalone binary (with DaisyUI built in) into
`.django_tailwind_cli/` and builds `static/css/tailwind.css`. Both are
git-ignored. For a one-off build without the server, run
`uv run python manage.py tailwind build`.

> On Windows, if Tailwind fails with **WinError 4551**, Smart App Control is
> blocking the standalone binary. The code isn't the cause. Allow the binary,
> or turn Smart App Control off.

Discover needs the internet to search the providers. Everything else, the
library, packs, the gallery, exports and the API included, works offline on
the seeded data.

## Demo sign-in

`seed_demo` creates three regular members (not staff). They all share an
obviously fake password:

| Username | Password | What they have |
|---|---|---|
| `demo_mira` | `toolbox-demo` | Medieval Village and Golden Hour Skies (public), Castle Siege (private) |
| `demo_otto` | `toolbox-demo` | Sci-fi Corridor and Desert Outpost (public) |
| `demo_juno` | `toolbox-demo` | Forest Ambience and Bakery Props (public; the bakery's market sound is non-commercial) |

Each library holds entries with every status (To review, Testing, Approved,
Rejected), a range of ratings and some notes. A few assets are rated by
several members, so community ratings show. Sign in as `demo_otto` to check
that Mira's private pack is a 404 for other members.

There's also a regular test account for trying the site by hand,
`test_user` with the password `5eMN9sKdr6cvJB`. It isn't seeded. On a
fresh clone, create it at `/accounts/signup/` with those details. The
automated tests never use it.

## Tests and linting

```sh
uv run pytest                         # the whole suite; must pass before any commit
uv run pytest --cov                   # with coverage
uv run ruff check .                   # lint
uv run ruff format --check .          # formatting (drop --check to apply it)
```

No test reaches the network. An autouse guard in `tests/conftest.py` fails
any test that tries, and provider code is tested against faked responses.
See [docs/TESTING.md](docs/TESTING.md).

## Using the API with a token

1. Sign in, then open **Account → API token** (`/accounts/token/`). Your
   token is created on your first visit.
2. Send it in the `Authorization` header as `Token <key>`. Requests signed
   with a token need no CSRF token.

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

| Endpoint | Methods | Who |
|---|---|---|
| `/api/library/` | GET, POST | Signed in (401 otherwise) |
| `/api/library/<id>/` | GET, PATCH, PUT, DELETE | The entry's owner (404 for anyone else) |
| `/api/packs/` | GET | Anyone. `?mine=1` needs sign-in |
| `/api/packs/<id>/`, `/api/packs/<id>/export/` | GET | Anyone for a public pack, only the owner for a private or unlisted one (404 otherwise) |

Saving an asset you already have is a **400** with "Already in your
library.". A provider failure during a save is a **502** with a friendly
`detail`. Packs are read-only through the API (**405** for writes).

## Demo snapshot (maintainers only)

`packs/demo.py` names each demo asset, pack and review. The snapshot was
captured once, online, with:

```sh
uv run python manage.py capture_demo_assets
```

It calls each provider's `fetch_record()` for every demo asset and rewrites
`packs/demo_assets.json`. It writes nothing unless every asset was fetched.
Graders don't need to run it.

## Layout

```
config/       settings, root URLs, the shell's context processor
providers/    API clients for ambientCG, Poly Haven and Openverse (plain Python)
catalog/      Discover, the library, saving, and the library API
packs/        packs, the builder, pack pages, export, the gallery, the pack API, demo data
accounts/     sign-up, sign-in, profile, settings and the API token page
templates/    the shared shell (base.html) and partials
static/       branding, fonts and scripts; styles/source.css is Tailwind's source
tests/        every test, with one shared conftest
asset_search.py   the Project 1 console script (below)
```

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

Openverse caps anonymous clients at 20 requests per minute and 200 per day.

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

Asset IDs for the lookup look like `Bricks097` (ambientCG), `red_bricks_02`
(Poly Haven) and `a8783d20-f1af-4c4b-b9ec-a8c212f67fee` (Openverse). The
ID of every result is shown in brackets in its details view.

### How to verify

Verification is manual: run the script and try each case below. Live
data changes over time, so names and counts may differ from the samples.

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

Other failures are reported the same way, as one `Error:` line followed
by the "Search again?" prompt. These are a timeout after 10 s, HTTP 429
(with a note about Openverse's 20/min and 200/day caps), other HTTP 5xx,
and a response that isn't JSON.

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

- Poly Haven's search is semantic and never returns an empty list. The
  script treats a search with zero keyword matches as "no results".
- ambientCG doesn't document the unit of `dimensions`, so the numbers are
  shown exactly as the API returns them.
- Openverse can be slow. On 2026-10-30 some uncached searches took 30 to
  60 seconds, so the 10 s timeout fired and the script printed a timeout
  error. Try again later or try a different phrase.
