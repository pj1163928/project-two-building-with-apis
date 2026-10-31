# PROMPTS.md — AI Usage Log

This file is the record of AI use on this codebase. At the end of every
agent session, direct the agent to write the session log with this prompt:

> Append a session log to PROMPTS.md at the repo root, under today's date,
> newest entry at the top. Record every prompt I gave you this session, in
> order, including any corrections. End the entry with a short summary:
> the outcome, any places where I deviated from a recommended answer or
> asked follow-up questions, and anything that went sideways.

Two rules:

- Entries are added only by that prompt, never unprompted.
- New entries go at the top. Never rewrite or delete an old entry — the
  log is part of your work, and an honest log of a session that went
  sideways is worth more than a tidy one.

Each entry has this shape:

    ## YYYY-MM-DD — <one-line summary>

    ### Prompts
    1. ...

    ### Summary
    - **Outcome:** what was built and what was kept
    - **Deviations:** recommendations overridden, follow-up questions asked
    - **Sideways:** failures, wrong turns, and how they were caught

## 2026-10-30 — Built the ambientCG / Poly Haven / Openverse console script

### Prompts
1. `@HANDOFF.md` Setup the script, append any messages to PROMPTS.md
   according to source formatting
2. Ok how do I run the code and test the apis
3. Alright they all seem to be working well including openverse. I would
   like you to walk me throuh the code and tell me how the api request are
   being made, retreived and displayed back to me in the console.
4. Alright looks good can you include this in the docs folder as a md file
   and ensure that all prompts are being recorded in PROMPTS.md

### Summary
- **Outcome:** Built the console script from the design in `HANDOFF.md`.
  - **Scaffold:** `uv init --app --no-package` with Python 3.13 pinned and
    `requests` as the only dependency (`pyproject.toml`, `uv.lock`,
    `.python-version`). The generated `main.py` was removed.
  - **Code:** `asset_search.py` plus `providers/` (`http`, `ambientcg`,
    `polyhaven`, `openverse` and a small `formatting` helper).
  - **Live checks:** each provider was run live for a normal search, an
    empty search (`zzqqxx`), a details view, a bad ID and invalid menu
    input. All passed.
  - **README:** `README.md` now has "How to run" and "How to verify"
    sections, a table of test cases and sample output.
  - **Manual testing:** the user ran the script and confirmed that all
    three providers work, including Openverse.
  - **Walkthrough:** the agent explained how requests are built, sent,
    parsed and printed, following one Poly Haven search from start to
    finish. That explanation was saved as `docs/code-walkthrough.md`.
  - Nothing was committed.
- **Deviations:** The user overrode no recommendations. Prompts 2 and 3
  were follow-up questions about running the script and how the code
  works. The agent made these changes to the handoff design:
  - **New module:** added `providers/formatting.py` (sizes and `m:ss`
    durations), which the handoff's file list didn't include. Both the
    providers and the script use it, and putting it in
    `providers/__init__.py` would have caused a circular import.
  - **ID lookup:** added an "ID lookup (i)" choice next to search. The
    assignment allows "a search phrase or item ID" as input, and the
    planned bad-ID check needs a way to type an ID.
  - **Bundles:** Poly Haven details list every bundle the API returns
    (`blend`, `gltf`, `fbx`, `usd`, `mtlx`), not only `blend` and `gltf`.
  - **ambientCG type:** the agent found that `include=type` returns the
    asset type, which fills the Type column.
- **Sideways:**
  - **Wrong scaffold:** `uv init --app` (uv 0.12.19) produced a packaged
    `src/` layout with a build system, not the flat layout the design
    requires. The agent deleted those generated files and re-ran it with
    `--no-package`.
  - **Encoding crash:** the first Poly Haven HDRI details run crashed with
    `UnicodeEncodeError`. A description contained U+2011, which the cp1252
    code page Windows uses for piped output can't encode. Fixed with
    `sys.stdout.reconfigure(errors="replace")`.
  - **Menu input:** `str.isdigit()` accepts characters such as `²` that
    `int()` rejects, so the agent switched the menu checks to `isdecimal()`
    and tested `²` input.
  - **Openverse slowness:** Openverse was degraded during testing.
    Uncached searches took 30–60 s, and some returned HTTP 500. The 10 s
    timeout fired and showed its error message. That checked the timeout
    path but blocked the normal check. To verify the list and details
    display, the agent did one run with the timeout raised to 90 s through
    a one-off override. The code still uses 10 s, and the README notes the
    slowness.
  - **Bad-ID response changed:** an Openverse bad ID now returns 404 (JSON
    for a well-formed UUID, HTML otherwise), not the 500 HTML page recorded
    in the handoff. Both cases end in the same friendly error.

## 2026-10-30 — Designed the ambientCG / Poly Haven / Openverse console script

### Prompts
1. `/grill-me` I would like for you to setup a short console script that
   makes a real API request to these providers, ambientCG, Poly Haven and
   Openverse Audio. This must be verifiable in a Python script and must:
   Accept user input, such as a search phrase or item identifier. Make a
   meaningful request to the external API. Use your own credentials if the
   provider requires them. Display selected results clearly in the console.
   Handle unsuccessful requests and empty results with useful messages.
   This folder/repository does not have an environment yet and will soon
   belong a django project that will us uv, you should setup this project
   with uv in mind do not set it up with another package manager. Since this
   is for a game asset collection and management center some useful
   information my be texture information, names size file format or
   anything you deem as useful.
2. C *(one script plus a `providers/` package)*
3. A *(`uv init --app` at the repo root, flat layout)*
4. Just use Django REST Framework (DRF) *(answering which HTTP library to
   use)*
5. A *(`requests` now; Django and DRF later)*
6. A *(interactive `input()` prompts)*
7. B *(search list, then a details view for one result)*
8. A *(Poly Haven `/search` + `/info`; `keywordMatches == 0` means empty)*
9. A *(same list columns for every provider; Poly Haven files summarized
   per resolution)*
10. A *(shared `get_json()` helper that raises one `ProviderError`)*
11. A *(anonymous access, no credentials)*
12. A *(manual verification only)*
13. B *(5 results plus an optional asset-type filter)*
14. `/handoff` We will continue to build the script in the next session,
    please append this current conversation to PROMPTS.md according to
    source formatting.

### Summary
- **Outcome:** A `/grill-me` interview settled 11 design decisions for the
  console script. The full agreed design and the API facts confirmed live
  are recorded in `HANDOFF.md`. In short:
  - The layout is `asset_search.py` plus `providers/` (`http`, `ambientcg`,
    `polyhaven`, `openverse`), set up with `uv init --app`, Python 3.13 and
    `requests`.
  - The script uses interactive prompts and shows a list, then details for
    one result.
  - Errors go through a single `ProviderError`, and all three providers are
    used anonymously.
  - No code was written and nothing was committed. Building the script is
    the next session's work.
- **Deviations:**
  - **HTTP library:** asked which library to use, the user answered "just
    use DRF". The agent explained that DRF builds APIs rather than calling
    them, and the user then chose `requests`, with Django and DRF to be
    added later.
  - **Verification:** the agent recommended a pytest suite with faked
    responses. The user chose manual verification instead.
  - **Unanswered sub-questions:** the user didn't answer whether to pin
    Python 3.13 or whether to loop after each search. The agent took the
    recommended default (yes) for both.
- **Sideways:** Partway through the interview, the agent made live
  read-only requests to check its assumptions and found two surprises:
  - Poly Haven's semantic `/search` never comes back empty (`zzqqxx`
    returned 814 hits) and returns only slugs, without names. That led to an
    extra question on how to detect empty results.
  - Openverse returns a 500 HTML page, not a 404, for a bad audio ID, so the
    error handling must cope with a body that isn't JSON.

  Sample responses were saved to the session scratchpad, not to the repo.

## 2026-10-30 — Researched free CC0/CC-BY game-asset APIs for the Django app

### Prompts
1. `/research` I would like you to research and find free APIs for a Django
   application that I am building. This application features a common
   library for game assets that are considered publicly usable such as CCO
   or Attribution related assets. The assets should contain items such as
   textures, sounds, 3D models, HDRIs etc. Compare these providers and use
   multiple if neccesary using official documentation, including available
   data, usage limitations and signup requirements.
2. Go ahead and append the prompt history to PROMPTS.md according to source
   formatting

### Summary
- **Outcome:** A background research agent compared 15 providers against
  their official docs and made live, keyless requests to 13 of them. The
  report is saved at `docs/research/game-asset-apis.md`, with a comparison
  table, a section per provider, a recommended combination and an open
  questions list. Recommendation: start with no signup by using Poly Haven
  and ambientCG (CC0 textures, HDRIs and models) and Openverse (CC audio with
  per-asset attribution), then add Freesound, Sketchfab and Wikimedia Commons
  later. OpenGameArt and Kenney have no API, Pixabay's license isn't
  Creative Commons, and Jamendo's API is non-commercial only. Nothing has
  been committed yet.
- **Deviations:** None. No recommendations were overridden and no follow-up
  questions were asked. The repo had no notes folder, so the agent chose
  `docs/research/` as the location.
- **Sideways:** The agent briefly wrote scratch files to the repo root while
  working and deleted them before finishing; `git status` showed only
  `docs/` afterward. Several primary sources couldn't be reached, so their
  claims are marked unverified in the report: Sketchfab's API agreement
  pages loaded empty, Smithsonian's open-access and terms pages returned
  403, and Internet Archive's search endpoint returned a backend error.