"""Light, dark or the system's choice: the site's colour scheme (user request, 2026-11-05).

The choice lives in the `ax-theme` cookie, for visitors and members alike, so
every page renders in it from the first paint. The title bar's switch and the
Settings page set it, through JavaScript at once or through ThemeView's POST
without it.
"""

COOKIE_NAME = "ax-theme"
COOKIE_MAX_AGE = 365 * 24 * 60 * 60
DEFAULT_THEME = "system"
# The choices, in the order the title bar's switch steps through them.
THEME_CHOICES = [("system", "System"), ("light", "Light"), ("dark", "Dark")]
THEME_LABELS = dict(THEME_CHOICES)


def theme_choice(request) -> str:
    """The visitor's chosen scheme from their cookie: "system", "light" or "dark"."""
    value = request.COOKIES.get(COOKIE_NAME, "")
    return value if value in THEME_LABELS else DEFAULT_THEME


def next_theme(choice: str) -> str:
    """The choice after `choice`, as the title bar's switch steps through them."""
    keys = [key for key, _ in THEME_CHOICES]
    return keys[(keys.index(choice) + 1) % len(keys)] if choice in keys else keys[0]
