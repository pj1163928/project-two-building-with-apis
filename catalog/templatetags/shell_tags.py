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
