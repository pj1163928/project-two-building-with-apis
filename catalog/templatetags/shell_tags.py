"""Template tags for the shell (templates/base.html)."""

import os

from django import template
from django.contrib.staticfiles import finders
from django.templatetags.static import static

register = template.Library()


@register.simple_tag
def versioned_static(path: str) -> str:
    """The static URL for `path` with `?v=<when it last changed>`.

    The stylesheet and scripts keep one URL each, so a browser could go on
    using a cached copy after they change (a member once clicked the new
    light/dark chips while still running the old shell.js, and nothing
    happened). The version makes every change a new URL. A file the finders
    can't see gets its plain static URL.
    """
    url = static(path)
    found = finders.find(path)
    if not found:
        return url
    return f"{url}?v={int(os.path.getmtime(found))}"


# Each section's icon (the same one as its sidebar entry), drawn large and faint as the
# page's watermark and on the page header's icon tile. The main page has none: its
# orbit fills the first screen.
PAGE_ICONS = {
    "discover": "search",
    "library": "library",
    "packs": "pack",
    "attribution": "license",
    "account": "user",
    "settings": "gear",
}


@register.filter
def page_icon(active_nav: str | None) -> str:
    """The icon name for the section `active_nav`, or "" when it has none."""
    return PAGE_ICONS.get(active_nav or "", "")
