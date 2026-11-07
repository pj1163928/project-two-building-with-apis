# Frontend

Read this before changing templates, styles, branding or HTMX. **This page
is an index:** the rules below apply to every template; open a topic file
only for the area you're changing. The visual reference is
[prototypes/discover-branded.html](../prototypes/discover-branded.html), a
throwaway prototype: take its look, not its code.

## Topic files

| Open… | Before you touch… |
|---|---|
| [frontend/theme.md](frontend/theme.md) | colours, light and dark, fonts, the logo, section icons |
| [frontend/shell.md](frontend/shell.md) | `base.html` (title bar, sidebar, status bar), hover, tooltips, the ambient glow, surfaces, page widths, shared partials, the scroll ruler |
| [frontend/htmx.md](frontend/htmx.md) | boosting, fragments, CSRF, scripts, versioned URLs, page transitions |
| [frontend/motion.md](frontend/motion.md) | the loader, wordmark and mark motion, parallax, card motion, the main page's cover, reduced motion |
| [frontend/discover.md](frontend/discover.md) | Discover's page, shelves, result cards, license filters, drawer |
| [frontend/library.md](frontend/library.md) | the library page, its cards, the pack picker, the Remove dialog, the library drawer |
| [frontend/packs.md](frontend/packs.md) | Your packs, New pack, the builder, a pack's page |
| [frontend/attribution.md](frontend/attribution.md) | the Attribution center and the license partials |
| [frontend/home.md](frontend/home.md) | the main page: orbit hero, How it works, gallery |
| [frontend/accounts.md](frontend/accounts.md) | sign-in and sign-up, Profile, Settings, the API token page |

## Tailwind + DaisyUI (no Node)

- django-tailwind-cli downloads a standalone Tailwind binary with DaisyUI
  built in (`TAILWIND_CLI_USE_DAISY_UI = True`) into `.django_tailwind_cli/`
  (git-ignored).
- The source is `styles/source.css`, outside `STATICFILES_DIRS` as the
  library requires. The build writes `static/css/tailwind.css`
  (git-ignored). `tailwind runserver` runs Django and the watcher;
  `tailwind build` makes a one-off minified build.
- Tailwind finds classes by scanning files. **Write class names out in
  full**; a class built from string pieces at runtime won't be found.

## Rules for every template

**Colour** (details in [theme.md](frontend/theme.md); `test_theme.py` and
`test_shell.py` enforce):

- The chrome is monochrome. Use the `axcenity` tokens only; chrome uses
  `ink` / `on-ink` / `shade`, never `white` or `black`.
- Type colours (`texture`, `hdri`, `model`, `sound`) mark an asset's type
  icon and nothing else.
- The only other colour is each page's ambient drop glow, set in the
  `#content[data-drop]` rules and nowhere else.

**Logo and thumbnails:**

- Never put the logo on a provider thumbnail, and never use it as a
  fallback.
- A thumbnail is the provider's URL (`referrerpolicy="no-referrer"`,
  `data-thumb-fallback`) over the asset's type icon.

**Chrome:**

- Every chrome `:hover` rule goes behind `html[data-pointer]` (the hover
  gate).
- No `rounded-*` in the chrome, and no text-colour utility on a chip.
- One `aria-current` per bar, and each `view-transition-name` once per page.
- Anything absolutely positioned in the side panel needs a positioned
  parent inside it.

**Layout** ([shell.md](frontend/shell.md#page-widths)):

- Two page shapes only. Full width is for browsing or working on a
  collection. Everything narrower is a centred column (`width: 100%`, a
  `max-width`, `margin-inline: auto`); add its class to
  `test_every_column_page_is_centred_like_the_rest`.
- New pages are work surfaces unless they're for browsing.
- Reuse the existing components before inventing one, and use one
  `btn-primary` per area.

**Forms:** autosave with one form per field and a status line, no Save
button. Add a `<noscript>` submit where the form needs one without
JavaScript. Forms are `novalidate`, and errors render inline from the
server.

**HTMX** ([htmx.md](frontend/htmx.md)):

- A fragment view checks `request.htmx and not request.htmx.boosted`.
- The CSRF header comes from `#app`. Never exempt a view.
- Scripts load once in `base.html` and delegate on `document`.
- Drawers, pickers and the builder swap with `transition:false`.

**Motion** ([motion.md](frontend/motion.md)):

- Monochrome only.
- The logo loader is the only loading indicator: no spinners.
- Every entry animation must end on the element's resting style, so
  reduced motion shows the content as it rests.

**Scroll ruler:** a page's ruler entries sit under the same `{% if %}` as
their sections.
