# CLAUDE.md

Axcenity Toolbox is a Django site, styled like the Axcenity editor, for
finding free game assets (ambientCG, Poly Haven, Openverse), saving them to a
private library, and building packs the engine can import. It's CIDM 3312
Project 2. The original console script (`asset_search.py` + `providers/`)
must keep working.

- **What to build:** [prd/axcenity-toolbox.md](prd/axcenity-toolbox.md). Its
  wording wins wherever the plan says "per the PRD".
- **Build order and progress:** [plans/axcenity-toolbox.md](plans/axcenity-toolbox.md).
  Ticked boxes are done.

## Commands

```sh
uv sync                                          # install (uv only, no pip or Node)
uv run python manage.py migrate
uv run python manage.py tailwind runserver       # Django + Tailwind watcher, http://127.0.0.1:8000/
uv run pytest                                    # must be green before any commit
uv run ruff check . && uv run ruff format .      # must be clean
uv run asset_search.py                           # the Project 1 console script
```

If Tailwind fails with WinError 4551, Windows Smart App Control is blocking
the standalone binary in `.django_tailwind_cli/`; the code isn't the cause.

## Rules that always apply

- **Layout:** `config` (settings, root URLs), `providers` (API clients),
  `catalog` (assets, Discover, library), `packs` (packs, gallery, export),
  `accounts` (auth, profile, token page). Tests live only in `tests/`.
- **Django style:** logic lives in models, managers and shared functions;
  cross-model workflows get a service module. Views are thin and
  class-based. Every URL is named and namespaced (`catalog:library`).
  Public shared functions get a docstring and type hints.
- **Access:** members-only pages use `LoginRequiredMixin`. Anything the
  caller doesn't own returns **404**, never 403. Every write is CSRF
  protected, HTMX included (`base.html` sends the token header).
- **Providers:** never change the existing `search()` / `get_details()`.
  New code sits next to them. All HTTP goes through `get_json()`, and every
  failure is a `ProviderError` with a message that's safe to show users.
- **Tests:** no test reaches the network. The autouse guard enforces it, and
  nothing may switch it off.
- **Colour:** the chrome is monochrome. The four type colours mean asset type
  and nothing else. The only other colour is each page's ambient drop
  glow, drifting behind the whole page (see docs/frontend/theme.md). Only the
  `axcenity` palette exists. It has a dark and a light set (System, Light or
  Dark, chosen in the title bar or Settings), and chrome uses the
  `ink`/`on-ink` tokens, never raw white/black.
- **Stay in the phase:** build only what the current plan phase asks for.
  Note anything a later phase needs; don't build it.

## Read before…

Docs are layered so you load only what a task needs. Read the **index**
first. Its rules apply everywhere, and its table says which **topic file**
covers your area. Open only that topic file. Don't read whole folders.

| Before you… | Read the index | Then the topic file in |
|---|---|---|
| add models, URLs, views or shared functions | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | `docs/architecture/` (URLs, providers, Discover, library, packs, exports, home and demo, APIs) |
| touch templates, styles, branding or HTMX | [docs/FRONTEND.md](docs/FRONTEND.md) | `docs/frontend/` (theme, shell, HTMX, motion, and one file per page area) |
| write or change tests | [docs/TESTING.md](docs/TESTING.md) | [docs/testing/test-files.md](docs/testing/test-files.md), to find where a test belongs |
| change a provider client | [docs/architecture/providers.md](docs/architecture/providers.md) | [docs/code-walkthrough.md](docs/code-walkthrough.md) for the console path; [docs/research/game-asset-apis.md](docs/research/game-asset-apis.md), that provider's section only |

## Keeping the docs organized

- **Indexes stay short** (`ARCHITECTURE.md`, `FRONTEND.md`, `TESTING.md`,
  about 150 lines at most). They hold only the rules that apply to every
  area, plus the table of topic files. Detail goes in a topic file.
- **One area per topic file**, in `docs/architecture/`, `docs/frontend/`
  or `docs/testing/`. Each opens with one paragraph naming its code files
  and linking its counterpart (server side ↔ templates). When a file passes
  about 200 lines, or a new area appears, split it or add a new file, and
  add its row to the index table in the same change.
- **Describe what the code does now, not how it got there.** Write the
  contract: names, rules, ids and classes, replies and status codes. Don't
  write "(user request, <date>)", "used to", "the first version" or phase
  numbers. That history belongs in `PROMPTS.md` and git. Keep a short
  **Why:** only where it stops someone from reintroducing a known bug.
- **Update docs in the same change as the code.**
  - New URL: a row in `architecture/urls.md`.
  - New shared function: a row in the index's Shared functions table.
  - New test file: a row in `testing/test-files.md`.
  - New rule that applies to every template or app: the index.
  - Anything else: the area's topic file.
- **Say each fact once.** Link to the other file instead of repeating it.
  Server behaviour goes in `architecture/`, markup and HTMX in `frontend/`.
- **Leave dated records alone.** `docs/research/` files are dated, cited
  research, and `code-walkthrough.md` is the Project 1 write-up. Add a new
  dated research file rather than rewriting an old one. Plans and the PRD
  are records too; don't trim them to match the docs.
- Code comments that point to docs name the index (`docs/FRONTEND.md`) or
  a topic file, never a section heading, so headings can move.

## Workflow

- `/implement <feature> phase <N>` builds one plan phase end to end.
- `PROMPTS.md` is the AI-usage log. Add entries only when asked (the
  `/implement` skill counts as asking). New entries go at the top, and old
  entries are never edited.
- Commits follow `Added Phase <N>/<M> of <Feature> - <what it delivers>`.
  Stage files one path at a time.
