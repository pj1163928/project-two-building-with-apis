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

## 2026-10-30 — Picked TDD candidates for each Axcenity Toolbox phase

### Prompts
1. `@plans/axcenity-toolbox.md` `@prd/axcenity-toolbox.md` `/tdd` Look
   through the plan and determine which phase would be good candidates for
   TDD, keep in mind all phases will likely not need TDD and should only
   be applied if necessary. Also append this conversation including this
   one and further messages to PROMPTS.md according to source formatting.
2. Ok I want to make 2 additional adjustments - HTMX integration test to
   phase 5 this verifies that if one provider shelf fails the other
   providers shelf still renders successfully.
   Do not make the test require a particular order between ranking assets
   with equal counts instead just test the ranking groups and establish a
   tie-breaking rule for whatever you feel is appropriate.

### Summary
- **Outcome:** The agent ran the selection step of the `tdd` skill
  against every phase of `plans/axcenity-toolbox.md`. It proposed at most
  three behaviors in each of ten phases (2a, 2b, 3, 4, 6, 7, 8, 9, 10,
  11). Phases 1, 5, 12 and 13 got none, because they're configuration,
  framework wiring, UI or motion, or a rule the access gate already tests.
  After the user's two changes:
  - Phase 2a gained a second candidate: the HTMX mixed-shelf test, where
    one provider's shelf fails and the other's still renders its results.
  - The Phase 10 ranking test now checks the groups of equal shared-tag
    count in order, not the order inside a group. The agent chose the
    tie-break (title A–Z, then id) and added it to Phase 10's acceptance
    criteria in the plan.

  The candidates are waiting for the user's approval. No app code was
  written and nothing was committed.
- **Deviations:**
  - The skill picks behaviors for one phase at a time. The user asked
    about the whole plan, so the agent made the selection for every phase
    at once. The red-green cycles still run phase by phase as each one is
    built.
  - The user asked for the shelf test in "phase 5". The plan's Phase 5 is
    the library drawer, which has no shelves. Step 5 of the PRD's build
    order is "Discover: provider shelves and error handling", which is the
    plan's Phase 2a, so the agent put the test there and said so.
- **Sideways:** None.

## 2026-10-30 — Planned the Axcenity Toolbox build from the PRD

### Prompts
1. `/prd-to-plan` `@prd/axcenity-toolbox.md` append this sessions
   conversations to PROMPTS.md according to source formatting.
2. Ok I would split phase 2 into two phases 2a provider search, shelves,
   HTMX loading and error handling 2b caching, provider credits fallback
   icons status bar and failure tests
   Merge phase 9 and 10
   Keep 5 and 6 seperate as well as 7 and 8 keeping tier 2 seperate as
   well
   Also add completion gates for every phase making sure that every
   relevant automated test passes no live provider API occurs during a
   test existing functionality remains operations and access control
   rules are tested whenever possible making sure that ruff passes.
   Also for the PRD since I did not mention this early please update the
   build order:
   Split Discover into two milestones prover shelves and error handling
   then caching and status reporting
   combine the main-page gallery and demo data into one final tier 1
   milestone
   Kep tier 2 ordering unchanged
   Clarify the existing phase 2 requirements. for story 83 which involves
   failure tests make sure that the provider client tests using responses
   application level tests using mocked provider functions
   HTMX shelf behavior when one provider fails and another succeeds.
   Also add one clarification to the data model, as of now the Asset model
   is shared accross users while SavedAsset is user-specific.
   Asset records are resused globally
   SavedAsset records are unique per user and asset
   Deleting a SavedAsset must never delete the shared Asset
   A PackItem can only reference a SavedAsset belonging to its pack owner.
   Clarify API authentication:
   Websites forms use Django CSRF protection
   Session-authenticated API write requests require CSRF validation.
   Token-authenticated API requests use the token instead

### Summary
- **Outcome:** The agent ran the `prd-to-plan` skill on
  `prd/axcenity-toolbox.md` and wrote `plans/axcenity-toolbox.md`.
  - **Phases:** 14 vertical slices. Tier 1 is Phases 1, 2a, 2b and 3–9,
    and Tier 2 is Phases 10–13.
  - **Header:** the durable decisions (apps, URLs, models, the
    shared/per-user record rules, access, authentication and CSRF,
    providers and caching, frontend, testing).
  - **Completion gate:** a standard gate that every phase repeats: all
    tests pass, no live provider calls, existing features still work, the
    access rules are tested, and Ruff passes. Each phase also lists its
    own access-rule checks.

  The PRD got four updates:
  - the shared/per-user record rules in the data model
  - the CSRF rules under Authentication
  - the three test levels for story 83
  - the Tier 1 build order: Discover is split into two milestones, and the
    gallery and demo data are merged into the final one

  No app code was written and nothing was committed.
- **Deviations:**
  - **User changes to the breakdown:** the user split Discover into 2a
    and 2b, merged the gallery phase with the demo-data phase, kept
    Phases 5/6 and 7/8 separate, kept Tier 2 as proposed, and asked for a
    completion gate on every phase.
  - **Stories moved by the agent:** the agent moved a few stories from
    where the PRD's build order puts them, so that each phase can be
    demoed on its own:
    - Delete-with-pack-list (story 31) and the drawer's list of packs
      (part of story 25) go in the pack builder phase, because packs
      don't exist before it.
    - The status bar (story 73) is split. Provider status comes with
      Discover, and the saved count comes with saving.
    - The token page (story 6) goes with the library API, not with
      accounts.
  - **"Phase 2":** "Clarify the existing phase 2 requirements" could mean
    the plan's Discover phase or the PRD's build-order step 2 (provider
    error tests). The agent applied the three test levels to both: Phases
    2a and 2b in the plan, and the PRD's Testing section.
  - **Decisions the PRD left open:**
    - Pack slugs are unique across the whole site.
    - Adding the same SavedAsset twice to one pack leaves a single item.
    - `?mine=1` on the pack API needs sign-in.
    - The status bar's provider status comes from the latest shelf
      outcome, with no extra health checks.
    - A network guard fixture fails any unmocked request.
    - Phase 1 adds regression tests for the console script, so the
      "existing features still work" gate can actually be checked.
- **Sideways:** In one Phase 1 criterion, the agent described a console
  menu exit choice without checking that it exists. The agent removed it
  before finishing.

## 2026-10-30 — Wrote the Axcenity Toolbox PRD

### Prompts
1. `@HANDOFF.md` `/to-prd` also append any conversations from now on
   including this one to PROMPTS.md accoring to source formatting.

### Summary
- **Outcome:** The agent ran the `to-prd` skill on the design in
  `HANDOFF.md` and wrote `prd/axcenity-toolbox.md`. It contains:
  - a problem statement and solution
  - 86 user stories in nine groups, each tagged with its build tier
    (T1 essential, T2 signature)
  - a table tracing every graded requirement to its stories
  - implementation decisions: apps, data model, providers and caching,
    pages, auth, an API endpoint table, visual design, tooling, tests,
    demo data and the build order
  - two explicit acceptance-criteria sections, as the handoff asked: an
    access-rules table covering the website and the API, and the export
    manifest's fields (Option A, locked by a golden-file test)
  - Out of Scope (including the Tier 3 stretch items) and Further Notes

  No app code was written and nothing was committed.
- **Deviations:** None; the user overrode no recommendations and asked no
  follow-up questions. The user asked for this session's prompts to be
  logged as it goes, so this entry was written without the usual
  end-of-session prompt. The design was silent on five points, so the
  agent picked defaults and listed them under Further Notes for review:
  - Discover search is open to signed-out visitors, but saving needs
    sign-in
  - owners can delete their packs
  - private packs return 404 to non-owners
  - the default variant falls back to the first one listed
  - a signed-out API request gets DRF's default 401 or 403
- **Sideways:** No failures. The skill bans code snippets, so the manifest
  contract is written as field tables, not a JSON example.

## 2026-10-30 — Designed Axcenity Toolbox (Django asset catalog and pack creator)

### Prompts
1. `/grill-me` I would like you to build an asset catalog and pack creator
   for a game engine known as Axcenity that I have created using Rust and
   Lua. This will be known simply as Axcenity toolbox, the website features
   a main page allowing users to see packs that have been created by other
   users such as combined textures, hdri, models and sounds. It can also
   offer suggestions on certain assets that can be used on certain
   projects. It must adhere to the following requirements technical and
   business:
   Technical: Django, Django REST Framework (DRF), SQLite, uv, Ruff,
   Tailwind CSS with DaisyUI, HTMX and Pytest
   Business:
   Your project must have one cohesive purpose. The purpose of your app is
   your own decision, but must serve a clear user need, with features that
   work together.
   Users can find items through an external API. Choose an API provider
   with free access sufficient to build and demonstrate your project.
   Users can save selected items to your application. Store enough
   information locally for saved items to remain accessible when the
   external API is unavailable.
   Users can add and edit their own information. This might include notes,
   ratings, status, or progress. Choose information that serves your
   application's purpose.
   Users can browse their saved items on a website. Include search,
   filtering, sorting, and pagination. These features must operate on
   locally saved data.
   Users must sign in to manage their saved data. Decide who can view or
   modify it. You may choose private data, public viewing, or selective
   sharing. Enforce those rules through both the website and the API.
   Your application provides its own API. Support listing, creating,
   updating, and deleting saved entries.
   The application handles unsuccessful external requests. Show a useful
   message when the provider is unavailable or a request fails.
2. B *(a personal library plus packs)*
3. A *(a shared `Asset` table plus a per-user `SavedAsset`)*
4. A *(link to provider thumbnails, with a placeholder icon if one fails)*
5. A *(packs double as project kits; suggestions match tags)*
6. C *(notes, rating and status, plus Axcenity fields `preferred_variant`
   and `import_path`)*
7. A *(a JSON manifest export)*
8. A *(a private library; packs are public or private by choice)*
9. A *(Django's built-in login plus DRF session and token authentication)*
10. For this one I feel like I can make it to where we seperate the asset
    types between textures models sounds and hdris. The sound will only
    pull from openverse and the others will pull from both ambientcg and
    poly haven
11. A *(provider sections that load on their own; no paging on Discover)*
12. A *(move `preferred_variant` and `import_path` to `PackItem`)*
13. C *(the pack builder plus an "Add to pack" dropdown in the library)*
14. A *(the full library search, filter, sort and pagination set through
    one `filter_library()`)*
15. A *(API create takes `provider` + `external_id` and the server fetches
    the rest)*
16. A *(library CRUD; packs read-only plus export in the API)*
17. A - I would also like to make the page look modern and have some cool
    transitions, the actual engine is inspired off of VSCode so make it
    look modern and sleek using Inter fonts. One of the websites I really
    like the design of is ArtCraft at getartcraft.com with its scrolling
    sidebar and fancy animations, if we could have something like that it
    would be cool
18. *(screenshot of the getartcraft.com home page)* A - this is the artcraft
    home for inspiration
19. A - Try to keep it unique with your own desgin inspired from vscode
    while adapting appearance features from the reference I gave you.
20. B *(`seed_demo` loads a committed snapshot of real provider data)*
21. A *(`django-tailwind-cli` with DaisyUI)*
22. A *(`monkeypatch` for app tests, `responses` for provider tests)*
23. A - /prototype I would like you to show me how you plan on laying out
    the searches for assets as I want to make sure that looks good.
    *(A answered Q21: new provider functions next to the old ones)*
24. *(attached the engine's `assets/branding/build.py`, its README and the
    logo images)* I really like the gallery shelves as it seems the most
    like what I am going for, it does look very much like artcraft which I
    am ok with. But I was wondering if we could transform it a bit and add
    a few features that keep the modern asthetic. such as changing the font
    and logo design to include this throughout the project in various
    locations that are animated, watermarked or featured.
25. Lets do monochrome. I also am not sure of the font of my wordmark so
    make a best guess and move onto further grill me questions as needed
26. A *(a `Tag` model with `normalize_tag()`)*
27. B *(deleting a saved asset removes it from packs, after confirmation)*
28. A *(cache successful searches for 1 h and Poly Haven `/info` for 12 h)*
29. A *(copy a public pack, and save single items from it)*
30. A *(apps: `catalog`, `packs`, `accounts`, plus `config` and
    `providers`)*
31. A *(the library drawer with autosave)*
32. A *(a versioned export manifest with `files[]` and `credits`)*
33. Use the tier system you reccomended
34. `/handoff` in the next session you will create the PRD
35. go ahead and append this conversations to PROMPTS.md according to
    source formatting

### Summary
- **Outcome:** A `/grill-me` interview of 29 questions, plus one
  `/prototype` round, produced a complete design for **Axcenity Toolbox**:
  - a Django site where users find assets from ambientCG, Poly Haven and
    Openverse, save them to a private library with notes, rating and status,
    and build tagged packs
  - public pack sharing with a "Copy pack" button, and suggestions by tag
    overlap
  - packs export as a versioned JSON manifest for the user's engine

  The full design is in `HANDOFF.md`, which was rewritten for the next
  session (writing the PRD). The previous console-script handoff is still
  in git at `48548a6`. Other work:
  - **Prototypes:** `prototypes/discover.html` shows three Discover
    layouts. `prototypes/discover-branded.html` is the chosen one: gallery
    shelves with the engine's logo, the `theme.rs` palette, monochrome
    chrome and Plus Jakarta Sans headings.
  - **Memory:** the agent saved a note recording where the engine's
    branding and palette live.
  - No app code was written and nothing was committed.
- **Deviations:**
  - **Personal fields (Q5):** the user chose C (adding engine-specific
    `preferred_variant` and `import_path`) over the recommended A. The
    agent later found that a saved asset can be in several packs with
    different needs, so Q10 moved those fields to `PackItem`.
  - **Discover layout (Q9):** the user replaced the agent's provider picker
    with their own type-first design: Sounds come from Openverse, and
    everything else from ambientCG plus Poly Haven. That raised a new
    question (Q9b) on combining two providers.
  - **Adding to packs (Q11):** the user chose C (both the pack builder and a
    library dropdown) over the recommended A. The agent routed both through
    one `add_to_pack()` function.
  - **Visual direction:** the user asked for a modern VSCode-inspired look
    based on getartcraft.com, and sent a screenshot to show that its
    "scrolling sidebar" is a right-edge scroll ruler. They then asked for a
    prototype, picked "Gallery shelves" out of three variants, and asked
    for their engine's logo and fonts to be woven through it. They chose
    monochrome chrome, and the wordmark font was left to the agent's best
    guess (Plus Jakarta Sans).
  - **Unanswered sub-questions:** the user didn't answer six of them. The
    agent took the recommended default each time and said so:
    - how Axcenity loads assets today (Q6)
    - paging on Discover (none)
    - `pytest-cov` and Ruff as formatter (yes)
    - keeping `asset_search.py` working (yes)
    - copying packs being website-only (yes)
    - `django-htmx` (yes)
- **Sideways:**
  - **ArtCraft fetch:** fetching getartcraft.com returned only page text,
    with no CSS or scripts, so the agent couldn't verify the sidebar or the
    animations and said so. The user's screenshot settled it.
  - **Provider data gaps:** reading `providers/` showed that the
    console-shaped results have no thumbnails, and that Poly Haven's
    `get_details()` throws away download URLs. That led to Q21 (a new
    `AssetRecord` shape). The live snapshot taken for the prototype showed
    that ambientCG has only one "wood" model.
  - **Checking the prototype:** Node isn't installed, so the agent couldn't
    syntax-check the JavaScript. It checked the prototypes by rendering
    them with headless Edge and reading screenshots. That caught:
    - type badges with low contrast against the textures
    - a stray outline around the search box
    - bright borders on the skeleton (loading) cards
    - the prototype panel covering the design
    - a title-bar wordmark that was too small

    All were fixed.
  - **Logo masks:** CSS masks can't load local files from `file://` pages,
    so the logos were downscaled with Pillow (`uv run --with pillow`, not
    added to the project) and embedded as data URIs.
  - **Live requests:** the agent made read-only requests to the three
    providers to capture the prototype's data. The snapshot and the build
    scripts stayed in the session scratchpad, not the repo.

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