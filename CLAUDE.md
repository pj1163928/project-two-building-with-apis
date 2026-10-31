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
  and nothing else. The only other colour is each page's drop glow, behind
  the hero and in the footer (see docs/FRONTEND.md). Only the `axcenity`
  palette exists. It has a dark and a light set (the site follows the system
  setting), and chrome uses the `ink`/`on-ink` tokens, never raw white/black.
- **Stay in the phase:** build only what the current plan phase asks for.
  Note anything a later phase needs; don't build it.

## Read before…

| Before you… | Read |
|---|---|
| add models, URLs, views or shared functions | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| write or change tests | [docs/TESTING.md](docs/TESTING.md) |
| touch templates, styles, branding or HTMX | [docs/FRONTEND.md](docs/FRONTEND.md) |
| change a provider client | [docs/code-walkthrough.md](docs/code-walkthrough.md) and [docs/research/game-asset-apis.md](docs/research/game-asset-apis.md) |

## Workflow

- `/implement <feature> phase <N>` builds one plan phase end to end.
- `PROMPTS.md` is the AI-usage log. Add entries only when asked (the
  `/implement` skill counts as asking). New entries go at the top, and old
  entries are never edited.
- Commits follow `Added Phase <N>/<M> of <Feature> - <what it delivers>`.
  Stage files one path at a time.
