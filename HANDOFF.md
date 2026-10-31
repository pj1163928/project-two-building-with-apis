# Handoff — Build the asset-search console script

**Date:** 2026-10-30
**Next session's focus:** build the console script designed in this session.
Nothing has been built yet. The repo has no `pyproject.toml`, no code, and no
commits from this session.

## Context

- **Assignment:** a console script that makes a real API request to
  ambientCG, Poly Haven and Openverse Audio. It must accept user input (a
  search phrase or item ID), make a meaningful request, use credentials only
  if a provider requires them, show selected results clearly, and handle
  failed requests and empty results with useful messages.
- **Where the repo is heading:** it will become a Django "game asset
  collection and management center" that uses **uv**. Use uv only; no
  pip, poetry or pipenv.
- **Provider research:** see
  [docs/research/game-asset-apis.md](docs/research/game-asset-apis.md).
  Don't redo it.
- **Session log:** [PROMPTS.md](PROMPTS.md). The newest entry records how
  each decision below was reached.
- **Tools on this machine:** uv 0.12.19 and Python 3.13.14 (Windows 11).
  `.gitignore` already covers `.venv` and `.env`.

## Agreed design (decided in a `/grill-me` session; don't re-ask)

1. **Shape:** a thin script plus a `providers/` package.
2. **uv setup:** run `uv init --app` at the repo root and pin Python 3.13.
   Lay out the files flat at the root, so `django-admin startproject config .`
   can land next to them later.
   ```
   asset_search.py
   providers/__init__.py, http.py, ambientcg.py, polyhaven.py, openverse.py
   ```
3. **HTTP client:** `requests` is the only runtime dependency
   (`uv add requests`).
   - DRF came up, and the user accepted that it builds APIs rather than
     calling them, so it won't be used to call these providers. Django and
     DRF are added later, not now.
4. **Input:** interactive `input()` prompts with a "Search again?" loop. No
   argparse.
5. **Flow:** a search list, then details for one result. Every provider
   module exposes `search(query, asset_type)` and `get_details(asset_id)`.
6. **Poly Haven search:** call `/search` (pass `q` trimmed and lower-cased,
   plus `t` and `limit`).
   - Treat **`keywordMatches == 0` as no results**. The semantic search
     never comes back empty: `zzqqxx` returned 814 hits.
   - `/search` returns only `slug` and `score`, so call `/info/{slug}` for
     each result shown. Call `/files/{slug}` only when showing details.
7. **Displayed fields:**
   - **List rows:** the same columns for every provider: `# | Name | Type |
     Info | License`.
   - **ambientCG details:** map types, `dimensions`, and each download with
     its `attributes`, `extension`, size and URL.
   - **Poly Haven details:** max resolution, physical size (`dimensions` is
     in mm), authors, tags and download count.
     - Summarize `/files` as **one line per resolution with the total size
       per format**, plus the `blend` and `gltf` bundles. Don't list every
       map file's URL.
   - **Openverse details:** creator, source, duration (in ms), bit rate,
     sample rate, `filetype`/`filesize`, `alt_files`, license and the
     `attribution` string.
   - **Formatting:** human-readable sizes (KB, MB, GB) and durations as
     `m:ss`.
8. **Errors:**
   - `providers/http.py` holds a `get_json(url, params)` helper. It sets the
     User-Agent `AssetLibrary-CIDM3312/0.1` (Poly Haven's terms require a
     User-Agent) and a 10 s timeout.
   - Every failure becomes a single `ProviderError` with a friendly message:
     connection error, timeout, 429 (the message should mention Openverse's
     anonymous 20/min and 200/day caps), 404, 5xx, and a body that isn't
     JSON.
   - The script catches `ProviderError`, prints it and goes back to the
     menu. No retries.
   - Empty results aren't an error: `search()` returns `[]` and the script
     prints a "no matches" message.
   - Bad menu input or a blank search re-prompts the user.
9. **Credentials:** none. All three providers are used anonymously. The
   README should say no provider requires a key, and that `.env` and secrets
   handling will arrive with Freesound later.
10. **Verification:** manual only. No pytest; the user overrode that
    recommendation. Run live checks and add "How to run" and "How to verify"
    sections to `README.md`, with example inputs and sample output.
11. **Search options:**
    - Show 5 results.
    - For Poly Haven and ambientCG, ask an optional type question: Any,
      Textures/materials, HDRIs or Models, with Enter meaning Any. Openverse
      skips it.
    - Map the types per provider: Poly Haven `t=textures|hdris|models`;
      ambientCG `type=material|hdri|3d-model`.

## Confirmed API facts (live, 2026-10-30)

- **ambientCG:**
  - `GET https://ambientcg.com/api/v3/assets?q=&type=&limit=5&include=title,url,tags,thumbnails,downloads,maps,dimensions`.
  - No matches returns `"totalResults": 0, "assets": []`.
  - Each `downloads` item has `attributes` (e.g. `2K-JPG`), `extension`,
    `url` and `size` (bytes).
- **Poly Haven:**
  - `/info/{slug}` returns `name`, `type` (0 = hdri, 1 = texture,
    2 = model), `categories`, `authors`, `dimensions`, `max_resolution`,
    `tags`, `description`, `download_count` and `thumbnail_url`.
  - `/info/bad_id` returns 404 with a plain-text body.
  - `/files/{slug}` returns map → resolution → format → `{size, url}`, and
    `blend`/`gltf` bundles that carry an `include` dict.
- **Openverse:**
  - `GET https://api.openverse.org/v1/audio/?q=&page_size=5` returns
    `result_count` and `results`.
  - A bad ID at `/v1/audio/{id}/` returns **500 with an HTML body**, so it
    must not crash on `.json()`.

## Suggested next steps

1. Scaffold with `uv init --app`, pin 3.13 and `uv add requests`. Remove or
   replace the generated `main.py`.
2. Build `providers/http.py`, then the three providers, then
   `asset_search.py`.
3. Run live checks for each provider:
   - a normal search, such as `brick` or `footsteps`
   - an empty search (`zzqqxx`)
   - a details view
   - a bad ID
   - invalid menu input
4. Update `README.md`. Show the output to the user. Commit only if the user
   asks.
5. Log the session in `PROMPTS.md` only when the user asks for it (see the
   rules at the top of that file).

## Suggested skills

- **`run`:** launch `uv run asset_search.py` and drive it to confirm the live
  checks above.
- **`simplify`** or **`code-review`:** do a quality or correctness pass on
  the new code before committing.
- **`implement`** (repo skill): only if the user wants to go through
  `/to-prd` → `/prd-to-plan` first. It expects `prd/<feature>.md` and
  `plans/<feature>.md`, and neither exists yet.
- **`tdd`:** not wanted for this step. The user chose manual verification.
