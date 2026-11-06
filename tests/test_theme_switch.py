"""Choosing light or dark by hand (user request, 2026-11-05).

The choice is the ax-theme cookie: System (follow the computer), Light or Dark.
The title bar's switch and the Settings page set it.
"""

import re

import pytest
from django.conf import settings
from django.test import Client
from django.urls import reverse

pytestmark = pytest.mark.django_db


def _html(client, name="packs:home"):
    return client.get(reverse(name)).content.decode()


def _html_tag(html):
    return re.search(r"<html [^>]*>", html).group(0)


@pytest.mark.parametrize(
    ("cookie", "choice", "scheme"),
    [
        (None, "system", None),
        ("light", "light", "light"),
        ("dark", "dark", "dark"),
        ("x", "system", None),
    ],
)
def test_the_page_renders_in_the_chosen_scheme(client, cookie, choice, scheme):
    if cookie:
        client.cookies["ax-theme"] = cookie
    tag = _html_tag(_html(client))
    assert f'data-scheme-choice="{choice}"' in tag
    # A fixed choice is on <html> from the server; System is resolved before first paint.
    assert (f'data-scheme="{scheme}"' in tag) if scheme else ("data-scheme=" not in tag)


def test_system_follows_the_computer_before_first_paint(client):
    head = _html(client).split("</head>", 1)[0]
    script = head.split("// The colour scheme, before first paint", 1)[1].split("</script>", 1)[0]
    assert 'matchMedia("(prefers-color-scheme: light)")' in script
    assert 'query.addEventListener("change", apply)' in script
    # It runs before the stylesheet's first paint matters: in <head>, not deferred.
    assert head.index("The colour scheme, before first paint") < head.index("js/shell.js")


@pytest.mark.parametrize("signed_in", [False, True])
def test_the_title_bar_switch_steps_system_light_dark(client, member, signed_in):
    if signed_in:
        client.force_login(member)
    for cookie, label, next_choice, next_label in [
        ("system", "System", "light", "Light"),
        ("light", "Light", "dark", "Dark"),
        ("dark", "Dark", "system", "System"),
    ]:
        client.cookies["ax-theme"] = cookie
        title_bar = _html(client).split('id="title-bar"', 1)[1].split("</header>", 1)[0]
        form = re.search(
            r'<form method="post" action="/accounts/theme/".*?</form>', title_bar, re.S
        )
        assert form and "csrfmiddlewaretoken" in form.group(0)
        button = re.search(r'<button type="submit" id="theme-toggle"[^>]*>', form.group(0)).group(0)
        assert f'value="{next_choice}"' in button
        assert f'aria-label="Theme: {label}. Switch to {next_label}"' in button
    # One icon per choice; CSS shows the current one.
    assert form.group(0).count('class="scheme-icon"') == 3


def test_settings_offers_system_light_and_dark(member_client):
    member_client.cookies["ax-theme"] = "dark"
    html = _html(member_client, "accounts:settings")
    panel = html.split('id="appearance"', 1)[1].split("</section>", 1)[0]
    assert re.findall(r'name="choice" value="(\w+)"', panel) == ["system", "light", "dark"]
    assert re.search(r'value="dark" data-theme-choice checked', panel)
    assert 'action="/accounts/theme/"' in panel


def _choose(client, choice, **extra):
    return client.post(reverse("accounts:theme"), {"choice": choice}, **extra)


def test_choosing_sets_the_cookie_for_a_year_and_goes_back(client):
    response = _choose(client, "light", HTTP_REFERER="http://testserver/library/")
    assert response.status_code == 302 and response["Location"] == "http://testserver/library/"
    cookie = response.cookies["ax-theme"]
    assert cookie.value == "light" and cookie["max-age"] == 365 * 24 * 60 * 60
    assert cookie["samesite"] == "Lax"
    assert 'data-scheme="light"' in _html_tag(_html(client))


def test_an_off_site_return_address_goes_home(client):
    response = _choose(client, "dark", HTTP_REFERER="https://evil.example/")
    assert response["Location"] == reverse("packs:home")


def test_an_htmx_choice_gets_a_204(client):
    response = _choose(client, "dark", HTTP_HX_REQUEST="true")
    assert response.status_code == 204 and response.cookies["ax-theme"].value == "dark"


def test_an_unknown_choice_is_a_400_and_sets_nothing(client):
    response = _choose(client, "sepia")
    assert response.status_code == 400 and "ax-theme" not in response.cookies


def test_choosing_needs_csrf_and_post():
    strict = Client(enforce_csrf_checks=True)
    assert _choose(strict, "dark").status_code == 403
    assert strict.get(reverse("accounts:theme")).status_code == 405


def test_the_switch_works_at_once_in_the_browser():
    script = (settings.BASE_DIR / "static" / "js" / "shell.js").read_text(encoding="utf-8")
    assert 'var SCHEMES = ["system", "light", "dark"];' in script
    assert (
        'document.cookie = "ax-theme=" + choice + "; path=/; max-age=31536000; SameSite=Lax";'
        in script
    )
    assert "window.axScheme.apply()" in script
    source = (settings.BASE_DIR / "styles" / "source.css").read_text(encoding="utf-8")
    assert 'html[data-scheme-choice="light"] #theme-toggle [data-scheme-icon="light"]' in source
