"""Sign-in and sign-up: layout, top-bar actions, the password toggle and error messages."""

import re

import pytest
from django.conf import settings
from django.urls import reverse

pytestmark = pytest.mark.django_db

AUTH_PAGES = ["accounts:login", "accounts:signup"]


def _title_bar(html):
    return html.split('id="title-bar"', 1)[1].split("</header>", 1)[0]


def _right_actions(html):
    return _title_bar(html).split('class="ml-auto', 1)[1]


@pytest.mark.parametrize("name", AUTH_PAGES)
def test_form_and_brand_share_one_bordered_container(client, name):
    html = client.get(reverse(name)).content.decode()
    card = html.split('id="auth-card"', 1)[1]
    assert card.startswith(' class="auth-card grid lg:grid-cols-2 ')
    # Form column first, then the brand panel, both inside the card.
    assert card.index("</form>") < card.index('id="auth-brand"')
    source = (settings.BASE_DIR / "styles" / "source.css").read_text(encoding="utf-8")
    assert ".auth-card { border: 1px solid var(--color-line-strong);" in source


@pytest.mark.parametrize("name", AUTH_PAGES)
def test_brand_panel_has_a_glow_and_a_supporting_message(client, name):
    html = client.get(reverse(name)).content.decode()
    brand = html.split('id="auth-brand"', 1)[1].split("</div>\n</div>", 1)[0]
    assert "Your assets. Your projects.<br>Your Axcenity." in brand
    assert "Keep your favorite resources organized and ready for your next project." in brand
    source = (settings.BASE_DIR / "styles" / "source.css").read_text(encoding="utf-8")
    brand_css = re.search(r"\.auth-brand \{(.*?)\}", source, re.S).group(1)
    assert "radial-gradient(" in brand_css


def test_form_heading_is_prominent(client):
    html = client.get(reverse("accounts:login")).content.decode()
    assert re.search(
        r'<h1 class="headline text-\[2\.5rem\] md:text-\[2\.75rem\] text-fg-strong">Sign in\.</h1>',
        html,
    )


@pytest.mark.parametrize("name", AUTH_PAGES)
def test_the_form_is_the_focal_point(client, name):
    html = client.get(reverse(name)).content.decode()
    # A wider card and form column than before (max-w-5xl and max-w-sm).
    assert 'class="auth-card grid lg:grid-cols-2 max-w-6xl mx-auto"' in html
    assert '<div class="w-full max-w-md mx-auto">' in html
    source = (settings.BASE_DIR / "styles" / "source.css").read_text(encoding="utf-8")
    assert ".auth-form .input { height: 3rem; font-size: 15px; }" in source
    # No footer watermark competing with the form; the small signature stays.
    footer = html.split('id="page-footer"', 1)[1].split("</footer>", 1)[0]
    assert "watermark" not in footer
    assert 'class="brand-signature' in footer


def test_sign_in_page_drops_its_own_sign_in_action(client):
    html = client.get(reverse("accounts:login")).content.decode()
    right = _right_actions(html)
    assert reverse("accounts:login") not in right
    assert re.search(r'<a href="/accounts/signup/" class="btn btn-primary ', right)
    # The breadcrumb still marks where you are.
    assert re.search(
        r'class="crumb chip-swap"[^>]*aria-current="page"><span class="chip-label">sign in<',
        _title_bar(html),
    )


def test_sign_up_page_drops_its_own_sign_up_action(client):
    html = client.get(reverse("accounts:signup")).content.decode()
    right = _right_actions(html)
    assert reverse("accounts:signup") not in right
    # Sign in, without a pointless ?next= back to the sign-up page.
    assert re.search(r'<a href="/accounts/login/" class="bar-item">', right)


def test_other_pages_keep_both_actions(client):
    right = _right_actions(client.get(reverse("catalog:discover")).content.decode())
    assert "/accounts/login/?next=/discover/" in right
    assert "/accounts/signup/" in right


@pytest.mark.parametrize(
    ("name", "fields"),
    [("accounts:login", ["id_password"]), ("accounts:signup", ["id_password1", "id_password2"])],
)
def test_every_password_input_has_a_visibility_toggle(client, name, fields):
    html = client.get(reverse(name)).content.decode()
    toggles = re.findall(
        r'<button type="button" class="password-toggle" data-password-toggle aria-controls="([^"]+)" aria-pressed="false" aria-label="Show password">',
        html,
    )
    assert toggles == fields
    assert "js/password-toggle.js" in html
    js = (settings.BASE_DIR / "static" / "js" / "password-toggle.js").read_text(encoding="utf-8")
    assert 'input.type = show ? "text" : "password";' in js
    assert 'button.setAttribute("aria-pressed", String(show));' in js


def test_toggle_script_loads_everywhere_and_delegates(client):
    # Navigation is boosted, and a swap doesn't run the new page's <head>, so the
    # script must already be loaded when a swap brings a password field in.
    head = client.get(reverse("catalog:discover")).content.decode().split("</head>", 1)[0]
    assert "js/password-toggle.js" in head
    js = (settings.BASE_DIR / "static" / "js" / "password-toggle.js").read_text(encoding="utf-8")
    assert 'document.addEventListener("click"' in js
    assert 'event.target.closest("[data-password-toggle]")' in js


def test_forgot_password_link_is_hidden_until_recovery_exists(client):
    html = client.get(reverse("accounts:login")).content.decode()
    assert "Forgot password?" not in html


@pytest.mark.urls("tests.urls_with_password_reset")
def test_forgot_password_link_appears_once_recovery_exists(client):
    html = client.get(reverse("accounts:login")).content.decode()
    link = re.search(r'<a href="([^"]+)"[^>]*>Forgot password\?</a>', html)
    assert link and link.group(1) == reverse("accounts:password_reset")
    # It sits beside the password label, after the username field.
    assert html.index('for="id_username"') < link.start() < html.index('id="id_password"')


def test_more_room_above_the_submit_button(client):
    html = client.get(reverse("accounts:login")).content.decode()
    form = html.split('class="auth-form', 1)[1].split("</form>", 1)[0]
    assert re.search(
        r'<div class="pt-4">\s*<button type="submit" class="btn btn-primary w-full h-12 '
        r'text-\[15px\] rounded-none">Sign in</button>',
        form,
    )


def test_inputs_get_a_subtle_focus_ring():
    source = (settings.BASE_DIR / "styles" / "source.css").read_text(encoding="utf-8")
    assert ".input:focus, .input:focus-within { outline: none;" in source
    assert "box-shadow: 0 0 0 3px color-mix(in srgb, var(--color-ink) 12%, transparent);" in source
    assert '.input[aria-invalid="true"] { border-color: var(--color-error); }' in source


def test_wrong_credentials_show_a_clear_alert(client, member):
    response = client.post(
        reverse("accounts:login"), {"username": member.username, "password": "nope"}
    )
    html = response.content.decode()
    alert = re.search(
        r'<div id="form-errors" role="alert" class="form-alert">(.*?)</div>\s*</div>', html, re.S
    )
    assert alert, "no form-level alert"
    assert "Please enter a correct username and password" in alert.group(1)
    assert "<svg" in alert.group(1)


def test_field_errors_sit_under_their_field_and_are_linked(client):
    response = client.post(
        reverse("accounts:signup"),
        {"username": "new_member", "password1": "a-Long-pass-123", "password2": "different-456"},
    )
    html = response.content.decode()
    # Django marks the invalid input and points it at the error list's id.
    assert re.search(
        r'<input type="password" name="password2"[^>]*aria-invalid="true"[^>]*aria-describedby="[^"]*\bid_password2_error\b',
        html,
    )
    errors = re.search(r'<ul id="id_password2_error" class="field-errors">(.*?)</ul>', html, re.S)
    assert errors and "didn’t match" in errors.group(1)
    assert html.index('id="id_password2"') < errors.start()


@pytest.mark.parametrize("name", AUTH_PAGES)
def test_auth_pages_share_the_working_pages_background(client, name):
    html = client.get(reverse(name)).content.decode()
    assert re.search(r'<main id="content" [^>]*data-surface="work"', html)
    source = (settings.BASE_DIR / "styles" / "source.css").read_text(encoding="utf-8")
    assert 'data-surface="auth"' not in source  # the auth-only glow is gone
