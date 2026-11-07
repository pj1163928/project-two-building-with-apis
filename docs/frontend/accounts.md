# Sign-in, sign-up and the Account pages

## Sign-in and sign-up

Both extend `templates/registration/auth_base.html` (blocks `auth_heading`,
`auth_lead`, `auth_form`, `auth_switch`). Work surfaces.

- **Layout:** one `#auth-card` (`.auth-card`, `line-strong` border, two
  equal-height columns, contents centred vertically, `max-w-6xl`). The form
  column (`max-w-md`): a micro-label, a `2.75rem` headline, a 15 px lead,
  48 px inputs (`.auth-form .input`), `pt-4` above a 48 px full-width
  square submit, and a ruled "New here?" / "Already have an account?" line.
- `partials/auth_brand.html`: the branding panel on wide screens only (the
  wordmark, "Your assets. Your projects. / Your Axcenity.", a line on the
  Toolbox, a "Toolbox" micro-label, over a monochrome radial glow).
- **Inline errors only:** the forms are `novalidate`, so every error comes
  from the server, inline, never a browser bubble.
- **Inputs:** `accounts.forms.StyledFieldsMixin` adds DaisyUI's `input`.
  `.input` is square on the inset colour with a subtle focus ring (a light
  border plus a 3 px, 12 % glow) in place of DaisyUI's outline; an
  `aria-invalid` input has a red edge and ring.
- **Forgot password?:** recovery is out of scope (PRD). `login.html`
  resolves `accounts:password_reset` with `{% url … as forgot_url %}`, which
  yields nothing while the URL doesn't exist, so the link appears by itself
  once built. Test it with `tests/urls_with_password_reset.py`.
- **Title bar:** a visitor sees Sign in and Sign up, except on those pages:
  sign-in shows only Sign up, sign-up only Sign in (with no `?next=` back to
  sign-up).

## Account pages

Profile, Settings and API token share one centred column (`.account-page
max-w-3xl mx-auto`) and one side panel
(`accounts/partials/account_pages.html`: user, gear and key rows).

- **Settings** (`accounts/settings.html`): **Appearance** (`#appearance`,
  System / Light / Dark chips; see [theme.md](theme.md#light-and-dark)),
  then **Download defaults** (`#download-defaults`): one small form per
  group of `.filter-chip`s (Resolution, Texture format, HDRI format, Model
  format, Sound format, Texture maps), each posting only its field to
  `accounts:download_preferences` on change. No Save button (a `<noscript>`
  one stands in). Replies replace `#settings-save-status`. The maps form
  also sends `maps_posted`, so unticking every map counts as posted (and is
  refused: "Choose at least one map type."). The library drawer's bundle
  follows these settings.
- **API token** (`accounts/token.html`): the key, the example header,
  **Copy token**, and **New token**, which opens `#token-rotate-dialog`
  (the `[data-dialog-open]` pattern) whose form posts to
  `accounts:rotate_token`. The status line shows the one-time message. A
  "From the console" note points to `library_client.py`.
