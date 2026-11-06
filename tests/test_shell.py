"""Every page renders inside the editor-style shell, with branding from static files."""

import json
import mimetypes
import re

import pytest
from django.conf import settings
from django.contrib.staticfiles import finders
from django.shortcuts import resolve_url
from django.template.loader import render_to_string
from django.test import Client
from django.urls import reverse

pytestmark = pytest.mark.django_db

PUBLIC_PAGES = ["packs:home", "catalog:discover", "packs:attribution", "accounts:login"]
PUBLIC_PAGES += ["accounts:signup"]
MEMBER_PAGES = ["packs:home", "catalog:discover", "catalog:library", "packs:list", "packs:create"]
MEMBER_PAGES += ["packs:attribution", "packs:attribution_packs", "packs:attribution_assets"]
MEMBER_PAGES += ["accounts:profile", "accounts:settings", "accounts:token"]

TYPE_HEXES = ["#F2A15A", "#6C8CFF", "#4CC38A", "#A48AFF"]
KIND_KEYS = ["texture", "hdri", "model", "sound"]
TYPE_TOKEN = re.compile(r"\b[\w:-]*-(texture|hdri|model|sound)\b")


@pytest.fixture
def pages(client, django_user_model, password):
    """(name, response) for every page, signed out and signed in."""
    rendered = [(name, client.get(reverse(name))) for name in PUBLIC_PAGES]
    member = Client()
    member.force_login(django_user_model.objects.create_user("shell_member", password=password))
    rendered += [(name, member.get(reverse(name))) for name in MEMBER_PAGES]
    return rendered


def test_every_page_renders_inside_the_shell(pages):
    for name, response in pages:
        html = response.content.decode()
        assert response.status_code == 200, name
        for part in ('id="title-bar"', 'id="activity-bar"', 'id="side-panel"', 'id="status-bar"'):
            assert part in html, f"{name} is missing {part}"
        assert 'data-theme="axcenity"' in html, name


def test_side_panel_has_a_collapse_toggle(client):
    html = client.get(reverse("catalog:discover")).content.decode()
    assert re.search(r'<button[^>]*id="panel-toggle"[^>]*aria-controls="side-panel"', html, re.S)
    assert 'aria-expanded="true"' in html
    assert 'localStorage.getItem("ax-panel")' in html  # state applied before paint
    assert "js/shell.js" in html
    # Two icons; CSS shows "collapse" while open and "expand" while collapsed.
    assert 'class="when-open"' in html
    assert 'class="when-collapsed"' in html


def test_panel_toggle_sits_on_the_sidebar_in_place_of_the_logo_tile(client):
    html = client.get(reverse("catalog:discover")).content.decode()
    title_bar = html.split('id="title-bar"', 1)[1].split("</header>", 1)[0]
    nav = html.split('id="activity-bar"', 1)[1].split("</nav>", 1)[0]
    assert 'id="panel-toggle"' not in title_bar
    # The toggle is the first thing in the activity bar, above Discover.
    assert 'id="panel-toggle"' in nav
    assert nav.index('id="panel-toggle"') < nav.index('aria-label="Discover"')
    assert "brand/icon-256.png" not in html


def test_side_panel_slides_to_the_icon_strip_rather_than_disappearing():
    source = (settings.BASE_DIR / "styles" / "source.css").read_text(encoding="utf-8")
    assert "#side-panel { width: 16rem; }" in source
    assert 'html[data-panel="collapsed"] #side-panel { width: 3.5rem; }' in source
    assert "html[data-panel-ready] #side-panel { transition: width" in source
    assert "@media (prefers-reduced-motion: reduce)" in source
    shell_js = (settings.BASE_DIR / "static" / "js" / "shell.js").read_text(encoding="utf-8")
    assert "panelReady" in shell_js  # animation switched on after first paint


def test_title_bar_has_wordmark_and_toolbox_label(client):
    html = client.get(reverse("packs:home")).content.decode()
    title_bar = html.split('id="title-bar"', 1)[1].split("</header>", 1)[0]
    assert re.search(r'<img src="[^"]*brand/wordmark-white\.png"[^>]*class="h-8 w-auto"', title_bar)
    assert '<span class="chip-label">Toolbox</span>' in title_bar


def test_title_bar_items_share_one_height(member_client):
    html = member_client.get(reverse("catalog:discover")).content.decode()
    title_bar = html.split('id="title-bar"', 1)[1].split("</header>", 1)[0]
    assert re.search(
        r'class="bar-item[^"]*"[^>]*><span class="chip-label">Toolbox</span>', title_bar
    )
    assert re.search(
        r'<a class="crumb chip-swap" href="/discover/" aria-current="page">'
        r'<span class="chip-label">discover</span>',
        title_bar,
    )
    # Account chip and sign-out each carry an icon.
    user_chip = re.search(r'<a [^>]*class="bar-item bar-item-user".*?</a>', title_bar, re.S).group(
        0
    )
    assert "<svg" in user_chip and "demo_member" in user_chip
    sign_out = re.search(
        r"<button type=\"submit\" class=\"bar-item\">.*?</button>", title_bar, re.S
    )
    assert "<svg" in sign_out.group(0) and "Sign out" in sign_out.group(0)


def test_title_bar_sign_in_and_sign_up_carry_icons(client):
    html = client.get(reverse("catalog:discover")).content.decode()
    title_bar = html.split('id="title-bar"', 1)[1].split("</header>", 1)[0]
    sign_in = re.search(
        r'<a href="/accounts/login/[^"]*" class="bar-item">.*?</a>', title_bar, re.S
    )
    assert "<svg" in sign_in.group(0) and "Sign in" in sign_in.group(0)
    sign_up = re.search(
        r'<a href="/accounts/signup/" class="btn btn-primary[^"]*">.*?</a>', title_bar, re.S
    )
    assert "<svg" in sign_up.group(0) and "Sign up" in sign_up.group(0)


def test_each_sidebar_icon_sits_beside_its_label_in_one_column(client):
    """The activity bar and side panel are one column (user request, 2026-11-05)."""
    html = client.get(reverse("catalog:discover")).content.decode()
    sidebar = html.split('id="side-panel"', 1)[1].split("</aside>", 1)[0]
    # One column: the activity bar is inside the side panel, not beside it.
    assert 'id="activity-bar"' in sidebar
    assert 'class="panel-row"' not in sidebar  # no second list of the same pages
    rows = re.findall(
        r'<a [^>]*class="act act-row"[^>]*>\s*<span class="act-icon">\s*<svg.*?</svg>\s*</span>'
        r'<span class="act-label" aria-hidden="true">([^<]+)</span>',
        sidebar,
        re.S,
    )
    assert rows == ICON_LABELS
    assert re.search(r'aria-label="Discover" class="act act-row"\s*aria-current="page"', sidebar)
    # The toggle's slot is h-14, and its title shows beside it while expanded.
    assert '<div class="h-14 ' in sidebar and 'class="sidebar-title' in sidebar
    source = (settings.BASE_DIR / "styles" / "source.css").read_text(encoding="utf-8")
    assert ".act-icon { flex: none; display: grid; place-items: center; width: 3.5rem; }" in source
    # Labels hide when collapsed, and tooltips name the icons only then.
    assert 'html[data-panel="collapsed"] :is(.act-label, .sidebar-title) { opacity: 0;' in source
    assert 'html:not([data-panel="collapsed"]) .act-row > .tip { display: none; }' in source


def test_the_giant_watermark_is_gone(client):
    """Pinned in view it was cut off behind the content, and at the foot of the page it
    was rarely seen, so the user had it removed (2026-11-05). The top-right mark
    carries the logo on every page instead."""
    html = client.get(reverse("packs:home")).content.decode()
    assert "watermark" not in html
    source = (settings.BASE_DIR / "styles" / "source.css").read_text(encoding="utf-8")
    assert ".watermark" not in source
    assert "CIDM 3312" not in html


def test_footer_has_a_small_brand_signature(client):
    html = client.get(reverse("packs:home")).content.decode()
    footer = html.split('id="page-footer"', 1)[1].split("</footer>", 1)[0]
    # A small signature: credits either side of a small wordmark.
    signature = footer.split('class="brand-signature', 1)[1]
    assert signature.index("Built for Axcenity Engine") < signature.index('<i class="word w-20 ')
    assert signature.index('<i class="word w-20 ') < signature.index("Axcenity Studios · 2026")


PAGE_ICONS = [
    ("packs:home", "home"),
    ("catalog:discover", "search"),
    ("catalog:library", "library"),
    ("packs:list", "pack"),
    ("accounts:profile", "user"),
    ("accounts:settings", "gear"),
]


@pytest.mark.parametrize(("name", "icon"), PAGE_ICONS)
def test_title_bar_text_chips_swap_to_icons_on_hover(member_client, name, icon):
    html = member_client.get(reverse(name)).content.decode()
    title_bar = html.split('id="title-bar"', 1)[1].split("</header>", 1)[0]
    swaps = re.findall(
        r'<a [^>]*class="(?:bar-item|crumb)[^"]*chip-swap[^"]*"[^>]*>'
        r'<span class="chip-label">([^<]+)</span>'
        r'<span class="chip-icon" aria-hidden="true">\s*<svg',
        title_bar,
    )
    assert swaps[:2] == ["Home", "Toolbox"]
    # The current page's chip (Home's own chip on Home, otherwise its crumb)
    # carries that page's own icon.
    current = re.search(
        r'<a [^>]*class="(?:bar-item|crumb) [^"]*chip-swap"[^>]*aria-current="page">.*?</a>',
        title_bar,
        re.S,
    )
    icon_html = render_to_string("partials/icon.html", {"name": icon, "size": 16})
    assert icon_html.strip() in current.group(0)


def test_chip_swap_css_hides_the_icon_until_hover():
    source = (settings.BASE_DIR / "styles" / "source.css").read_text(encoding="utf-8")
    assert (
        ".chip-swap > .chip-icon { display: grid; padding-top: 0; text-indent: 0; opacity: 0;"
        in source
    )
    assert ".chip-swap:hover > .chip-label" in source
    assert ".chip-swap:hover > .chip-icon" in source


@pytest.mark.parametrize("signed_in", [False, True])
def test_one_home_button_sits_left_of_toolbox(client, member, signed_in):
    if signed_in:
        client.force_login(member)
    html = client.get(reverse("catalog:discover")).content.decode()
    title_bar = html.split('id="title-bar"', 1)[1].split("</header>", 1)[0]
    assert title_bar.count('id="home-button"') == 1
    assert ">Home</span>" not in title_bar.split('class="ml-auto', 1)[1]  # none on the right
    links = re.findall(r"<(?:a|button)\b[^>]*>", title_bar)
    assert 'class="brand-link' in links[0]
    assert 'id="home-button"' in links[1]
    assert "bar-item-app" in links[2]  # TOOLBOX


def test_home_page_has_no_duplicate_home_crumb(client):
    html = client.get(reverse("packs:home")).content.decode()
    title_bar = html.split('id="title-bar"', 1)[1].split("</header>", 1)[0]
    assert 'aria-label="Breadcrumb"' not in title_bar
    assert re.search(r'id="home-button" class="bar-item chip-swap" aria-current="page"', title_bar)


def test_title_bar_buttons_are_square(member_client, client):
    source = (settings.BASE_DIR / "styles" / "source.css").read_text(encoding="utf-8")
    chips = re.search(r"\.bar-item, \.crumb \{([^}]*)\}", source).group(1)
    assert "border-radius: 0;" in chips
    for page in (member_client.get(reverse("catalog:discover")), Client().get("/discover/")):
        html = page.content.decode()
        title_bar = html.split('id="title-bar"', 1)[1].split("</header>", 1)[0]
        classes = re.findall(r'<(?:a|button)\b[^>]*class="([^"]*)"', title_bar)
        assert not any(re.search(r"\brounded-(?!none)", c) for c in classes)
        assert all("rounded-none" in c for c in classes if "btn" in c.split())
    nav = html.split('id="activity-bar"', 1)[1].split("</nav>", 1)[0]
    assert "rounded" not in re.search(r'id="panel-toggle" class="([^"]*)"', nav).group(1)


def test_hover_inverts_to_black_on_white_and_back():
    source = (settings.BASE_DIR / "styles" / "source.css").read_text(encoding="utf-8")
    # ink/on-ink: white on black in dark mode, near-black on white in light mode.
    inverted = "{ color: var(--color-on-ink); background: var(--color-ink); }"
    # Gated on html[data-pointer]; see test_chrome_hover_waits_for_real_pointer_movement.
    for selector in (".act:hover", ".panel-row:hover", ".bar-item:hover"):
        prefixed = "html[data-pointer] " + selector
        rule = next(line for line in source.splitlines() if line.strip().startswith(prefixed))
        assert inverted in rule, selector
    assert (
        ".brand-link:hover img, .brand-link:focus-visible img "
        "{ filter: var(--logo-filter-hover, invert(1)); }" in source
    )
    assert (
        ".btn:hover, .btn:focus-visible { background-color: var(--color-ink); "
        "color: var(--color-on-ink);" in source
    )
    assert (
        ".btn-primary:hover, .btn-primary:focus-visible { background-color: var(--color-on-ink); "
        "color: var(--color-ink);" in source
    )


def _source():
    return (settings.BASE_DIR / "styles" / "source.css").read_text(encoding="utf-8")


def test_ambient_glow_runs_through_the_whole_page(client):
    """The glow layer fills .content-stage, which grows with the content, so it runs
    from the top of the page to the bottom of the footer, however long the page is
    (user request, 2026-11-05)."""
    html = client.get(reverse("catalog:discover")).content.decode()
    content = html.split('id="content"', 1)[1]
    stage = content.split('class="content-stage"', 1)[1]
    assert stage.count('class="ambient" aria-hidden="true" data-ambient') == 1
    # Back to front: the glow, the mark, the page, then the footer, all on the stage.
    assert (
        stage.index('class="ambient"')
        < stage.index('class="hero-atmosphere"')
        < stage.index('class="page-hero')
        < stage.index('id="page-footer"')
    )
    # The old fixed hero and footer glows (three symmetrical blobs and rings) are gone.
    assert "drop-glow" not in html and "drop-blob" not in html
    source = _source()
    assert ".content-stage { position: relative; flex: 1 0 auto;" in source
    ambient = re.search(r"\.ambient \{([^}]*)\}", source).group(1)
    assert "inset: 0;" in ambient and "pointer-events: none;" in ambient
    assert ".drop-glow" not in source and "@keyframes drop-ripple" not in source


def test_ambient_drops_are_big_loose_lava_lamp_wax():
    """Each drop gets its own shape, colours, size, path, wobble, speed and phase from
    ambient.js, so nothing moves in step; the CSS animates transforms only. The user
    asked for bigger drops that move like water, then bigger, looser and faster, like
    a lava lamp (2026-11-05)."""
    script = (settings.BASE_DIR / "static" / "js" / "ambient.js").read_text(encoding="utf-8")
    assert "Math.random()" in script
    props = ("--top", "--left", "--size", "--shape", "--from", "--to", "--drift", "--delay")
    for prop in (*props, "--wobble", "--wa", "--wb", "--hx", "--hy"):
        assert f'"{prop}"' in script, prop
    # Big: 620 px up to 1300 px across. One per band of page, more when the page grows.
    assert "var size = whole(620, Math.max(720, Math.min(1300, width * 0.8)));" in script
    assert "var BAND = 650;" in script
    # Faster: 18-34 s to rise or fall, a 5-9 s wobble; and a long way up and down.
    assert "var drift = whole(18, 34);" in script
    assert 'between(5, 9).toFixed(1) + "s"' in script
    assert '"--y" + i, Math.round(signed(180, 480))' in script
    # Like wax: tall and thin while it travels, wide and squat as it turns.
    for prop in ("--tall", "--thin", "--squat", "--flat"):
        assert f'"{prop}"' in script, prop
    assert "ResizeObserver" in script and "htmx.onLoad(setUp)" in script
    # Water keeps its volume: as a drop stretches one way it squashes the other.
    assert '"--wb", (2 - squash)' in script
    # A drop's body and two shells that follow its wobble a beat behind.
    assert script.count('layer("ambient-shell")') == 2 and 'layer("ambient-drop")' in script
    source = _source()
    blob = re.search(r"\.ambient-blob \{([^}]*)\}", source).group(1)
    assert "animation: ambient-drift var(--drift)" in blob
    body = re.search(r"\.ambient-blob > i \{([^}]*)\}", source).group(1)
    assert (
        "border-radius: var(--shape);" in body and "animation: ambient-wobble var(--wobble)" in body
    )
    drop = re.search(r"\.ambient-drop \{([^}]*)\}", source).group(1)
    assert "filter: blur(var(--blur));" in drop and "at var(--hx) var(--hy)" in drop
    assert "animation-delay: calc(var(--delay) - 0.5s);" in source
    assert "animation-delay: calc(var(--delay) - 1s);" in source
    drift = source.split("@keyframes ambient-drift {", 1)[1].split("} }", 1)[0]
    assert (
        "scale(var(--thin), var(--tall))" in drift and "scale(var(--flat), var(--squat))" in drift
    )
    for name in ("ambient-drift", "ambient-wobble"):
        keyframes = source.split(f"@keyframes {name} {{", 1)[1].split("} }", 1)[0]
        assert "transform:" in keyframes
        assert not re.search(r"\b(top|left|width|height|border-radius):", keyframes)
    reduced = source.split("@media (prefers-reduced-motion: reduce) {", 1)[1].split("\n}", 1)[0]
    assert ".ambient-blob, .ambient-blob > i { animation: none; }" in reduced


def test_glow_colours_come_only_from_the_page_drop_tokens():
    script = (settings.BASE_DIR / "static" / "js" / "ambient.js").read_text(encoding="utf-8")
    assert '["var(--drop-a)", "var(--drop-b)", "var(--drop-c)"]' in script
    assert not re.search(r"#[0-9A-Fa-f]{3,8}\b", script)


@pytest.mark.parametrize(
    ("name", "drop"),
    [
        ("packs:home", "home"),
        ("catalog:discover", "discover"),
        ("catalog:library", "library"),
        ("packs:list", "packs"),
        ("accounts:profile", "account"),
        ("accounts:settings", "settings"),
        ("packs:attribution", "attribution"),
        ("accounts:login", "account"),
    ],
)
def test_drop_glow_is_tinted_per_page(member_client, name, drop):
    if name == "accounts:login":
        member_client = Client()
    html = member_client.get(reverse(name)).content.decode()
    # The colours are set once on <main>, and the one glow layer reads them.
    assert re.search(rf'<main id="content" [^>]*data-drop="{drop}"', html)
    assert html.count("data-ambient") == 1


@pytest.mark.parametrize("name", ["accounts:login", "accounts:signup"])
def test_auth_pages_show_the_logo_to_the_right_of_the_form(client, name):
    html = client.get(reverse(name)).content.decode()
    content = html.split('id="content"', 1)[1]
    assert content.index("</form>") < content.index('id="auth-brand"')
    brand = content.split('id="auth-brand"', 1)[1].split("</div>", 1)[0]
    assert 'class="word ' in brand


def test_activity_bar_entries_in_order(client):
    html = client.get(reverse("packs:home")).content.decode()
    sidebar = html.split('id="side-panel"', 1)[1].split("</aside>", 1)[0]
    labels = re.findall(r'<a [^>]*aria-label="([^"]+)"', sidebar)
    assert labels == ["Discover", "Library", "Packs", "Attribution", "Account", "Settings"]
    # Account and Settings sit at the foot, after the page's own panel.
    assert sidebar.index("side-panel-inner") < sidebar.index('aria-label="Account"')


@pytest.mark.parametrize(
    ("name", "label"),
    [
        ("catalog:discover", "Discover"),
        ("catalog:library", "Library"),
        ("packs:list", "Packs"),
        ("packs:attribution", "Attribution"),
        ("accounts:profile", "Account"),
        ("accounts:settings", "Settings"),
    ],
)
def test_current_page_is_marked_in_activity_bar(member_client, name, label):
    html = member_client.get(reverse(name)).content.decode()
    current = re.findall(r'aria-label="([^"]+)"[^>]*aria-current="page"', html, re.S)
    assert current == [label]


def test_status_bar_lists_every_provider_as_unknown_at_first(client):
    html = client.get(reverse("catalog:discover")).content.decode()
    status_bar = html.split('id="status-bar"', 1)[1]
    for provider in ("ambientCG", "Poly Haven", "Openverse Audio"):
        assert provider in status_bar
    assert "status unknown" in status_bar


def test_status_bar_saved_count_only_for_members(member_client):
    signed_out = Client().get(reverse("catalog:discover")).content.decode()
    assert "saved</span>" not in signed_out.split('id="status-bar"', 1)[1]
    signed_in = member_client.get(reverse("catalog:discover")).content.decode()
    assert "saved</span>" in signed_in.split('id="status-bar"', 1)[1]


def test_title_bar_shows_sign_in_and_sign_up_to_visitors(client):
    html = client.get(reverse("catalog:discover")).content.decode()
    assert reverse("accounts:login") in html
    assert reverse("accounts:signup") in html
    assert reverse("accounts:logout") not in html


def test_title_bar_sign_out_is_a_csrf_protected_post_form(member_client, member):
    html = member_client.get(reverse("catalog:discover")).content.decode()
    form = re.search(
        r'<form method="post" action="'
        + re.escape(reverse("accounts:logout"))
        + r'"[^>]*>(.*?)</form>',
        html,
        re.S,
    )
    assert form, "sign-out form missing"
    assert 'name="csrfmiddlewaretoken"' in form.group(1)
    assert member.username in html


def test_htmx_requests_send_the_csrf_token(client):
    html = client.get(reverse("catalog:discover")).content.decode()
    assert re.search(r"hx-headers='\{\"X-CSRFToken\": \"[^\"]+\"\}'", html)
    assert "htmx" in html  # the htmx script is loaded


def test_branding_loads_from_static_files(client):
    html = client.get(reverse("packs:home")).content.decode()
    for asset in (
        "brand/favicon-32.png",
        "brand/wordmark-white.png",
        "brand/mark-white.png",
        "css/tailwind.css",
    ):
        assert f"{settings.STATIC_URL}{asset}" in html or f"/{settings.STATIC_URL}{asset}" in html
    assert re.search(
        r'<link rel="icon" type="image/png" sizes="32x32" href="[^"]*favicon-32\.png"', html
    )
    for asset in (
        "brand/favicon-32.png",
        "brand/wordmark-white.png",
        "brand/mark-white.png",
    ):
        assert finders.find(asset), f"{asset} is not in static files"


def test_every_font_in_the_stylesheet_is_a_static_file():
    source = (settings.BASE_DIR / "styles" / "source.css").read_text(encoding="utf-8")
    fonts = re.findall(r'url\("\.\./fonts/([^"]+)"\)', source)
    families = set(re.findall(r'font-family: "([^"]+)"; src:', source))
    assert families == {"Inter", "JetBrains Mono", "Plus Jakarta Sans"}
    for font in fonts:
        assert finders.find(f"fonts/{font}"), f"fonts/{font} is missing"


def test_each_font_family_ships_its_ofl_licence():
    for licence in ("Inter-OFL.txt", "JetBrainsMono-OFL.txt", "PlusJakartaSans-OFL.txt"):
        path = finders.find(f"fonts/{licence}")
        assert path, licence
        with open(path, encoding="utf-8") as f:
            assert "SIL Open Font License" in f.read()


def test_plus_jakarta_source_is_pinned():
    sources = (settings.BASE_DIR / "static" / "fonts" / "SOURCES.md").read_text(encoding="utf-8")
    assert "8b0a1d0f5983c89bc2b93f1b5fb55f9e252744b5" in sources
    assert "89b3fb38aa0d275d7a731d0d817a4f1622b316b4d7fbdedcf02ee9099ff68bc8" in sources


def _classes(html):
    return " ".join(re.findall(r'class="([^"]*)"', html))


def test_type_colour_never_appears_in_the_chrome(pages):
    for name, response in pages:
        html = response.content.decode()
        for hex_value in TYPE_HEXES:
            assert hex_value.lower() not in html.lower(), f"{name} uses {hex_value}"
        chrome = [
            html.split('id="title-bar"', 1)[1].split("</header>", 1)[0],
            html.split('id="activity-bar"', 1)[1].split("</nav>", 1)[0],
            html.split('id="side-panel"', 1)[1].split("</aside>", 1)[0],
            html.split('id="status-bar"', 1)[1],
        ]
        for part in chrome:
            assert not TYPE_TOKEN.search(_classes(part)), f"{name}'s chrome uses a type colour"


def test_type_colour_means_type_only_on_the_discover_tiles(pages):
    """On a page's own HTML, Discover's type tiles are the only place type colour appears.

    (Shelf fragments and library cards also use it, only for an asset's type:
    see the test below and test_discover.py.)
    """
    for name, response in pages:
        html = response.content.decode()
        content = html.split('id="content"', 1)[1].split('id="page-footer"', 1)[0]
        if name != "catalog:discover":
            assert not TYPE_TOKEN.search(_classes(content)), f"{name} uses a type colour"
            continue
        tiles = content.split('id="type-tiles"', 1)[1].split("</nav>", 1)[0]
        outside = content.replace(tiles, "")
        assert not TYPE_TOKEN.search(_classes(outside)), "type colour outside the tiles"
        used = {match.group(0) for match in TYPE_TOKEN.finditer(_classes(tiles))}
        assert used == {f"{prefix}-{kind}" for prefix in ("text", "bg") for kind in KIND_KEYS}


def test_pack_items_use_type_colour_only_for_the_assets_type(member_client, member, make_asset):
    from catalog.models import SavedAsset
    from packs.models import Pack
    from packs.services import add_to_pack

    pack = Pack.objects.create_pack(member, "Every Kind")
    for kind in KIND_KEYS:
        add_to_pack(
            pack,
            SavedAsset.objects.create(user=member, asset=make_asset(external_id=kind, kind=kind)),
        )
    html = member_client.get(reverse("packs:builder", args=[pack.pk])).content.decode()
    content = html.split('id="content"', 1)[1].split('id="page-footer"', 1)[0]
    coloured = re.findall(
        r'class="([^"]*\b(?:text|bg)-(?:texture|hdri|model|sound)\b[^"]*)"', content
    )
    assert {classes.split()[0] for classes in coloured} == {"library-type-icon", "result-fallback"}
    # The side panel's list of packs is chrome, and stays monochrome.
    chrome = html.split('id="content"', 1)[0] + html.split('id="status-bar"', 1)[1]
    assert not TYPE_TOKEN.search(_classes(chrome))


def test_library_cards_use_type_colour_only_for_the_assets_type(member_client, member, make_asset):
    from catalog.models import SavedAsset

    for kind in KIND_KEYS:
        SavedAsset.objects.create(user=member, asset=make_asset(external_id=kind, kind=kind))
    html = member_client.get(reverse("catalog:library")).content.decode()
    content = html.split('id="content"', 1)[1].split('id="page-footer"', 1)[0]
    coloured = re.findall(
        r'class="([^"]*\b(?:text|bg)-(?:texture|hdri|model|sound)\b[^"]*)"', content
    )
    # Only the type icon beside the label and the fallback icon under the thumbnail.
    assert {classes.split()[0] for classes in coloured} == {"library-type-icon", "result-fallback"}
    for kind in KIND_KEYS:
        assert f'class="library-type-icon text-{kind}"' in content
    # And the chrome around a full library stays monochrome.
    chrome = html.split('id="content"', 1)[0] + html.split('id="status-bar"', 1)[1]
    assert not TYPE_TOKEN.search(_classes(chrome))


@pytest.mark.parametrize("signed_in", [False, True])
def test_home_hero_search_is_the_one_primary_action(client, member, signed_in):
    if signed_in:
        client.force_login(member)
    html = client.get(reverse("packs:home")).content.decode()
    content = html.split('id="content"', 1)[1].split('id="page-footer"', 1)[0]
    form = re.search(
        r'<form id="hero-search" method="get" action="/discover/"[^>]*>(.*?)</form>', content, re.S
    )
    assert form, "hero search missing"
    assert 'type="search" name="q"' in form.group(1)
    assert '<label for="hero-search-input" class="sr-only">' in form.group(1)
    # Directly below the description, and above the other actions.
    assert content.index("Find free textures") < form.start() < content.index("btn-quiet")
    primaries = re.findall(r'class="btn btn-primary[^"]*"[^>]*>([^<]+)<', content)
    assert primaries == ["Search"]
    quiet = re.findall(r'class="btn btn-quiet"[^>]*>([^<]+)<', content)
    if signed_in:
        assert quiet == ["Browse Discover", "Open your library"]
    else:
        assert quiet == ["Sign up", "Sign in"]


def test_title_bar_sign_up_is_still_a_white_primary_button(client):
    html = client.get(reverse("catalog:discover")).content.decode()
    title_bar = html.split('id="title-bar"', 1)[1].split("</header>", 1)[0]
    assert re.search(r'<a href="/accounts/signup/" class="btn btn-primary ', title_bar)


def test_page_headline_is_refined_and_a_step_smaller(client):
    html = client.get(reverse("catalog:discover")).content.decode()
    h1 = re.search(r'<h1 class="([^"]*)"', html).group(1).split()
    assert "headline" in h1 and "display" not in h1
    assert "md:text-[2.75rem]" in h1  # down from md:text-5xl (3rem)
    source = (settings.BASE_DIR / "styles" / "source.css").read_text(encoding="utf-8")
    assert ".headline { font-family: var(--font-display); font-weight: 700;" in source


def test_content_has_breathing_room_without_spreading_out(client):
    html = client.get(reverse("catalog:discover")).content.decode()
    content = html.split('id="content"', 1)[1]
    assert 'mx-auto px-8 lg:px-12 pt-14 pb-12 space-y-8">' in content


ICON_LABELS = ["Discover", "Library", "Packs", "Attribution", "Account", "Settings"]


def test_activity_bar_icons_show_tooltips(client):
    html = client.get(reverse("catalog:discover")).content.decode()
    sidebar = html.split('id="side-panel"', 1)[1].split("</aside>", 1)[0]
    tips = re.findall(r'<span class="tip" aria-hidden="true">([^<]+)</span>', sidebar)
    assert tips == ["Collapse panel", *ICON_LABELS]
    assert "title=" not in sidebar  # no doubled-up native tooltip
    shell_js = (settings.BASE_DIR / "static" / "js" / "shell.js").read_text(encoding="utf-8")
    assert '"Collapse panel" : "Expand panel"' in shell_js
    source = (settings.BASE_DIR / "styles" / "source.css").read_text(encoding="utf-8")
    assert ".act:hover > .tip, .act:focus-visible > .tip { opacity: 1;" in source


def test_icons_share_one_size_per_bar(member_client):
    html = member_client.get(reverse("catalog:discover")).content.decode()
    title_bar = html.split('id="title-bar"', 1)[1].split("</header>", 1)[0]
    sidebar = html.split('id="side-panel"', 1)[1].split("</aside>", 1)[0]
    activity = sidebar.split('<div class="side-panel-inner', 1)[0]
    account = sidebar.split('<nav aria-label="Account"', 1)[1]
    assert set(re.findall(r'<svg width="(\d+)"', title_bar)) == {"16"}
    assert set(re.findall(r'<svg width="(\d+)"', activity + account)) == {"20"}
    # The page's own panel (Discover's filters) has smaller icons beside its labels.
    panel = sidebar.split('<div class="side-panel-inner', 1)[1].split('<nav aria-label="Account"')[
        0
    ]
    assert set(re.findall(r'<svg width="(\d+)"', panel)) <= {"13", "14", "16"}
    # Each group of entries starts 4px below its border.
    assert '<div class="flex flex-col gap-1 pt-1">' in sidebar
    assert '<nav aria-label="Account" class="shrink-0 flex flex-col gap-1 pt-1 ' in sidebar


def test_current_page_is_marked_in_the_sidebar_and_the_title_bar(member_client):
    html = member_client.get(reverse("catalog:library")).content.decode()
    nav = html.split('id="activity-bar"', 1)[1].split("</nav>", 1)[0]
    title_bar = html.split('id="title-bar"', 1)[1].split("</header>", 1)[0]
    assert re.search(r'aria-label="Library"[^>]*aria-current="page"', nav)
    # The account pages' own rows still mark theirs (Profile, Settings).
    profile = member_client.get(reverse("accounts:profile")).content.decode()
    assert re.search(
        r'class="panel-row"[^>]*aria-current="page">(?:(?!</a>).)*>Profile<', profile, re.S
    )
    assert re.search(
        r'class="crumb chip-swap"[^>]*aria-current="page"><span class="chip-label">library<',
        title_bar,
    )
    source = (settings.BASE_DIR / "styles" / "source.css").read_text(encoding="utf-8")
    for rule in (
        '.act[aria-current="page"]::before',
        '.panel-row[aria-current="page"]::before',
        '.bar-item[aria-current="page"], .crumb[aria-current="page"]',
    ):
        assert rule in source, rule
    assert "box-shadow: inset 0 -2px 0 var(--color-ink);" in source


def test_side_panel_expands_smoothly_with_staggered_labels():
    source = (settings.BASE_DIR / "styles" / "source.css").read_text(encoding="utf-8")
    assert (
        "html[data-panel-ready] #side-panel { transition: width 0.5s cubic-bezier(0.16, 1, 0.3, 1)"
        in source
    )
    assert (
        "html[data-panel-ready] .side-panel-inner { transition: opacity 0.35s ease 0.15s" in source
    )
    assert (
        'html[data-panel="collapsed"] .side-panel-inner { opacity: 0; visibility: hidden;' in source
    )
    assert ".act-row:nth-child(2) { --row-delay: 0.15s; }" in source
    reduced = source.split("@media (prefers-reduced-motion: reduce) {", 1)[1].split("\n}", 1)[0]
    assert (
        "#side-panel, .side-panel-inner, .act-label, .sidebar-title { transition: none !important; }"
        in reduced
    )


SHOWCASE = ["packs:home", "catalog:discover"]
WORK = ["catalog:library", "packs:list", "packs:create", "accounts:profile", "accounts:settings"]


@pytest.mark.parametrize("name", SHOWCASE + WORK)
def test_each_page_picks_a_surface_mood(member_client, name):
    html = member_client.get(reverse(name)).content.decode()
    surface = re.search(r'<main id="content" [^>]*data-surface="(\w+)"', html).group(1)
    assert surface == ("showcase" if name in SHOWCASE else "work")
    h1 = re.search(r'<h1 class="([^"]*)"', html).group(1).split()
    if name in SHOWCASE:
        assert "md:text-[2.75rem]" in h1
    else:
        assert "md:text-[2rem]" in h1  # compact: the content leads, not the header


def test_showcase_is_expressive_and_work_is_restrained():
    source = (settings.BASE_DIR / "styles" / "source.css").read_text(encoding="utf-8")
    # Showcase: the full-size mark, top light and a stronger glow.
    assert "width: min(46rem, 62%)" in re.search(r"\.hero-mark \{([^}]*)\}", source).group(1)
    assert '#content[data-surface="showcase"] .ambient { opacity: 0.52; }' in source
    # Work: a subtler, slower glow and a smaller mark tucked into the corner.
    assert "opacity: 0.34;" in re.search(r"\.ambient \{([^}]*)\}", source).group(1)
    assert (
        '#content[data-surface="work"] .hero-mark { top: -3.5rem; right: -3rem; '
        "width: min(22rem, 30%); opacity: 0.06; }" in source
    )
    assert "calc(var(--drift) * 1.15)" in source


@pytest.mark.parametrize("name", SHOWCASE + WORK)
def test_the_mark_shows_on_every_page_above_the_glow(member_client, name):
    """The logo was hidden on work pages; now every page shows it, layered over the
    glow so the glow never covers it (user request, 2026-11-05)."""
    html = member_client.get(reverse(name)).content.decode()
    content = html.split('id="content"', 1)[1]
    assert content.count('class="mark hero-mark"') == 1
    assert content.index('class="ambient"') < content.index('class="hero-atmosphere"')
    source = (settings.BASE_DIR / "styles" / "source.css").read_text(encoding="utf-8")
    assert ".hero-atmosphere { display: none; }" not in source
    atmosphere = re.search(r"\.hero-atmosphere \{([^}]*)\}", source).group(1)
    assert "position: absolute;" in atmosphere and "display: none" not in atmosphere


def test_the_drawer_keeps_the_mark_in_view(member_client, member, make_asset):
    from catalog.models import SavedAsset

    entry = SavedAsset.objects.create(user=member, asset=make_asset())
    html = member_client.get(reverse("catalog:entry", args=[entry.pk]), HTTP_HX_REQUEST="true")
    html = html.content.decode()
    assert '<i class="mark drawer-mark" aria-hidden="true"></i>' in html
    # Behind the body, and nowhere near the thumbnail.
    thumb = html.split('<div class="entry-thumb">', 1)[1].split("</div>", 1)[0]
    assert "mark" not in thumb


def test_side_panel_inputs_stay_inside_their_chips():
    """A chip's hidden input used to be placed against the sidebar, which doesn't clip,
    so a long tag list pushed inputs below the window and the whole page scrolled on
    into empty space (user report, 2026-11-05)."""
    source = (settings.BASE_DIR / "styles" / "source.css").read_text(encoding="utf-8")
    chip = re.search(r"\.filter-chip \{([^}]*)\}", source).group(1)
    assert "position: relative;" in chip


def test_oversized_mark_renders_once_behind_the_content(client):
    html = client.get(reverse("packs:home")).content.decode()
    content = html.split('id="content"', 1)[1]
    assert content.count('class="mark hero-mark"') == 1
    assert content.index('class="hero-atmosphere" aria-hidden="true"') < content.index(
        'class="page-hero'
    )


def test_chrome_hover_waits_for_real_pointer_movement():
    """After a click the next page loads under a still cursor; nothing may flip on arrival."""
    shell_js = (settings.BASE_DIR / "static" / "js" / "shell.js").read_text(encoding="utf-8")
    assert 'addEventListener("pointermove", onMove' in shell_js
    assert "root.dataset.pointer" in shell_js
    source = (settings.BASE_DIR / "styles" / "source.css").read_text(encoding="utf-8")
    for selector in (
        ".act:hover, .act:focus-visible",
        ".act:hover > .tip",
        ".panel-row:hover",
        ".bar-item:hover",
        ".crumb:hover",
        ".bar-item-user:hover",
        ".chip-swap:hover > .chip-label",
        ".chip-swap:hover > .chip-icon",
        ".brand-link:hover,",
        ".brand-link:hover img",
    ):
        lines = [line for line in source.splitlines() if selector in line]
        assert lines, selector
        for line in lines:
            assert f"html[data-pointer] {selector}" in line, line


def test_chrome_fonts_are_preloaded_and_never_swap_in_late(client):
    html = client.get(reverse("catalog:discover")).content.decode()
    head = html.split("</head>", 1)[0]
    for font in (
        "JetBrainsMono-Regular",
        "Inter-Regular",
        "Inter-Medium",
        "PlusJakartaSans-Variable",
    ):
        assert re.search(
            rf'<link rel="preload" href="[^"]*fonts/{font}\.ttf" as="font" type="font/ttf" crossorigin>',
            head,
        ), font
    assert head.index('rel="preload"') < head.index("tailwind.css")
    source = (settings.BASE_DIR / "styles" / "source.css").read_text(encoding="utf-8")
    for line in source.splitlines():
        if line.startswith('@font-face { font-family: "JetBrains Mono"') or line.startswith(
            '@font-face { font-family: "Plus Jakarta Sans"'
        ):
            assert "font-display: block;" in line, line


# ---------- Boosted navigation ----------


def test_navigation_is_boosted_so_the_page_never_reloads(client):
    html = client.get(reverse("catalog:discover")).content.decode()
    assert '<body class="bg-app text-fg" hx-boost="true">' in html
    config = re.search(r'<meta name="htmx-config" content=\'([^\']+)\'>', html).group(1)
    config = json.loads(config)
    assert config["historyCacheSize"] == 0  # Back refetches; no stale snapshots
    error_rule = next(rule for rule in config["responseHandling"] if rule["code"] == "[45]..")
    assert error_rule["swap"] is True  # a 404 or 403 shows, rather than a dead click


def test_csrf_header_lives_inside_the_swapped_region(client):
    html = client.get(reverse("catalog:discover")).content.decode()
    body_tag = re.search(r"<body[^>]*>", html).group(0)
    assert "hx-headers" not in body_tag  # <body> survives swaps; the token rotates at sign-in
    assert re.search(
        r'<div id="app" class="h-screen flex flex-col" hx-headers=\'\{"X-CSRFToken": "[^"]+"\}\'>',
        html,
    )


def test_boosted_requests_get_the_full_page(member_client):
    headers = {"HX-Request": "true", "HX-Boosted": "true"}
    for name in ("packs:home", "catalog:discover", "catalog:library", "accounts:profile"):
        html = member_client.get(reverse(name), headers=headers).content.decode()
        assert '<div id="app"' in html and 'id="title-bar"' in html, name


def test_boosted_sign_in_redirects_like_a_normal_one(client, member, password):
    response = client.post(
        reverse("accounts:login"),
        {"username": member.username, "password": password},
        headers={"HX-Request": "true", "HX-Boosted": "true"},
    )
    assert response.status_code == 302
    assert response.url == resolve_url(settings.LOGIN_REDIRECT_URL)


def test_logo_survives_swaps_and_reserves_its_space(client):
    html = client.get(reverse("catalog:discover")).content.decode()
    brand = re.search(r'<a [^>]*id="brand-link"[^>]*>.*?</a>', html, re.S).group(0)
    assert " hx-preserve " in brand
    assert re.search(r'<img [^>]*width="103" height="32"', brand)


def test_shell_script_survives_swaps():
    shell_js = (settings.BASE_DIR / "static" / "js" / "shell.js").read_text(encoding="utf-8")
    # The panel toggle is found through the document, so a swapped-in button works.
    assert 'event.target.closest("#panel-toggle")' in shell_js
    # Each boosted swap re-arms the hover gate and re-syncs the toggle.
    assert 'document.addEventListener("htmx:afterSwap"' in shell_js
    assert "armHoverGate();" in shell_js and "syncPanel();" in shell_js


def test_fonts_are_served_as_fonts():
    assert mimetypes.guess_type("static/fonts/JetBrainsMono-Regular.ttf")[0] == "font/ttf"


def test_first_load_hides_title_bar_chips_until_the_mono_font_is_ready(client):
    head = client.get(reverse("catalog:discover")).content.decode().split("</head>", 1)[0]
    assert "fonts.check(face)" in head and 'root.dataset.fonts = "loading"' in head
    assert "setTimeout(ready, 3000)" in head
    source = (settings.BASE_DIR / "styles" / "source.css").read_text(encoding="utf-8")
    assert (
        'html[data-fonts="loading"] #title-bar :is(.bar-item, .crumb, .crumb-sep) { visibility: hidden; }'
        in source
    )


# ---------- Page transitions ----------


def test_boosted_swaps_run_as_view_transitions(client):
    html = client.get(reverse("catalog:discover")).content.decode()
    config = json.loads(re.search(r'<meta name="htmx-config" content=\'([^\']+)\'>', html).group(1))
    assert config["globalViewTransitions"] is True
    source = (settings.BASE_DIR / "styles" / "source.css").read_text(encoding="utf-8")
    assert "#content { view-transition-name: content; }" in source
    assert "::view-transition-new(content) { animation: page-in " in source
    assert "::view-transition-old(content) { animation: page-out " in source


@pytest.mark.parametrize(
    ("selector", "name"),
    [
        ('.act[aria-current="page"]', "current-act"),
        ('.panel-row[aria-current="page"]', "current-row"),
        ('.bar-item[aria-current="page"], .crumb[aria-current="page"]', "current-chip"),
    ],
)
def test_current_page_marks_glide_between_pages(selector, name):
    source = (settings.BASE_DIR / "styles" / "source.css").read_text(encoding="utf-8")
    assert f"{selector} {{ view-transition-name: {name}; }}" in source


@pytest.mark.parametrize("name", MEMBER_PAGES + ["accounts:login", "accounts:signup"])
def test_each_transition_name_is_used_once_per_page(member_client, name):
    """A view-transition-name used twice on a page cancels the whole transition."""
    if name in ("accounts:login", "accounts:signup"):
        member_client = Client()
    html = member_client.get(reverse(name)).content.decode()
    nav = html.split('id="activity-bar"', 1)[1].split("</nav>", 1)[0]
    panel = html.split('id="side-panel"', 1)[1].split("</aside>", 1)[0]
    title_bar = html.split('id="title-bar"', 1)[1].split("</header>", 1)[0]
    assert len(re.findall(r'class="act[^"]*"[^>]*aria-current="page"', nav)) <= 1
    assert len(re.findall(r'class="panel-row"[^>]*aria-current="page"', panel)) <= 1
    assert (
        len(re.findall(r'class="(?:bar-item|crumb)[^"]*"[^>]*aria-current="page"', title_bar)) <= 1
    )


def test_reduced_motion_turns_page_transitions_off():
    source = (settings.BASE_DIR / "styles" / "source.css").read_text(encoding="utf-8")
    assert (
        "::view-transition-group(*), ::view-transition-old(*), ::view-transition-new(*) "
        "{ animation: none !important; }" in source
    )


# ---------- Light mode ----------


def test_chrome_uses_contrast_tokens_not_fixed_white_or_black():
    source = (settings.BASE_DIR / "styles" / "source.css").read_text(encoding="utf-8")
    # White and black are only defined, never used directly, except white
    # highlight glows that read on both backgrounds.
    assert "var(--color-black)" not in source
    for line in source.splitlines():
        if "var(--color-white)" in line:
            assert "radial-gradient(" in line, line


@pytest.mark.parametrize("name", ["packs:home", "catalog:library"])
def test_marks_use_ink_so_they_show_in_both_modes(member_client, name):
    html = member_client.get(reverse(name)).content.decode()
    classes = " ".join(re.findall(r'class="([^"]*)"', html.split('id="content"', 1)[1]))
    assert "text-white" not in classes
    source = (settings.BASE_DIR / "styles" / "source.css").read_text(encoding="utf-8")
    assert "color: var(--color-ink);" in re.search(r"\.hero-mark \{([^}]*)\}", source).group(1)


def test_scripts_and_the_stylesheet_carry_a_version(client):
    """A browser kept running the old shell.js, so the new light/dark chips did
    nothing (user report, 2026-11-05). Each URL now changes with its file."""
    html = client.get(reverse("packs:home")).content.decode()
    head = html.split("</head>", 1)[0]
    assert re.search(r'<link rel="stylesheet" href="/static/css/tailwind\.css\?v=\d+">', head)
    scripts = re.findall(r'<script src="/static/js/([\w-]+\.js)(\?v=\d+)?" defer>', head)
    assert scripts and all(version for _, version in scripts)


def test_versioned_static_follows_the_file_and_skips_missing_ones(tmp_path, settings):
    import os

    from catalog.templatetags.shell_tags import versioned_static

    folder = tmp_path / "static"
    (folder / "js").mkdir(parents=True)
    script = folder / "js" / "probe.js"
    script.write_text("//", encoding="utf-8")
    os.utime(script, (1_700_000_000, 1_700_000_000))
    settings.STATICFILES_DIRS = [folder]
    assert versioned_static("js/probe.js") == "/static/js/probe.js?v=1700000000"
    assert versioned_static("js/missing.js") == "/static/js/missing.js"


@pytest.mark.parametrize("name", ["accounts:profile", "accounts:settings", "accounts:token"])
def test_account_pages_are_centred_at_one_width(member_client, name):
    """They sat to the left of the content area (user report, 2026-11-05)."""
    html = member_client.get(reverse(name)).content.decode()
    assert '<div class="account-page max-w-3xl mx-auto w-full space-y-8">' in html


@pytest.mark.parametrize("signed_in", [False, True])
def test_pack_page_uses_type_colour_only_for_the_assets_type(client, member, make_asset, signed_in):
    from catalog.models import SavedAsset
    from packs.models import Pack
    from packs.services import add_to_pack

    pack = Pack.objects.create_pack(member, "Every Kind")
    for kind in KIND_KEYS:
        add_to_pack(
            pack,
            SavedAsset.objects.create(user=member, asset=make_asset(external_id=kind, kind=kind)),
        )
    Pack.objects.filter(pk=pack.pk).update(visibility="public")
    if signed_in:
        client.force_login(member)
    html = client.get(reverse("packs:public", args=[pack.slug])).content.decode()
    content = html.split('id="content"', 1)[1].split('id="page-footer"', 1)[0]
    coloured = re.findall(
        r'class="([^"]*\b(?:text|bg)-(?:texture|hdri|model|sound)\b[^"]*)"', content
    )
    assert {classes.split()[0] for classes in coloured} == {"library-type-icon", "result-fallback"}
    chrome = html.split('id="content"', 1)[0] + html.split('id="status-bar"', 1)[1]
    assert not TYPE_TOKEN.search(_classes(chrome))


def test_every_column_page_is_centred_like_the_rest():
    """A page narrower than the content is a centred column, never pinned left
    (the pack page was, user report 2026-11-06)."""
    css = (settings.BASE_DIR / "styles" / "source.css").read_text(encoding="utf-8")
    for selector in (
        ".pack-page",
        ".attribution",
        ".entry-layout",
        ".remove-page",
        ".discover-asset-page",
    ):
        rule = re.search(re.escape(selector) + r" \{([^}]*)\}", css).group(1)
        assert "margin-inline: auto" in rule and "width: 100%" in rule, selector


def test_new_pack_is_a_centred_column(member_client):
    html = member_client.get(reverse("packs:create")).content.decode()
    assert '<section class="pack-new-page max-w-3xl mx-auto w-full space-y-5">' in html


@pytest.mark.parametrize(
    "url_name",
    [
        "accounts:profile",
        "accounts:settings",
        "accounts:token",
        "packs:list",
        "packs:attribution",
        "packs:attribution_packs",
        "packs:attribution_assets",
    ],
)
def test_every_side_panel_row_has_an_icon(member_client, member, url_name):
    """User request, 2026-11-06: iconography in every sidebar menu."""
    from packs.models import Pack

    Pack.objects.create_pack(member, "Forest Kit")
    html = member_client.get(reverse(url_name)).content.decode()
    rows = re.findall(r'<(?:a|summary) [^>]*class="panel-row".*?</(?:a|summary)>', html, re.S)
    assert rows, url_name
    for row in rows:
        assert '<span class="panel-row-icon" aria-hidden="true">' in row, row


def test_filter_groups_have_icons(member_client):
    html = member_client.get(reverse("catalog:library")).content.decode()
    titles = re.findall(r'<p class="filter-group-title micro text-fg-muted">(.*?)</p>', html, re.S)
    assert len(titles) == 5 and all("<svg" in title for title in titles)


def test_a_newer_stylesheet_or_script_loads_the_page_in_full():
    """A boosted swap keeps the old <head>, so a style fix stayed invisible until a
    hard reload (user report, 2026-11-06). shell.js compares the arriving page's
    versioned asset URLs with the loaded ones and loads it in full when they differ."""
    script = (settings.BASE_DIR / "static" / "js" / "shell.js").read_text(encoding="utf-8")
    assert 'document.addEventListener("htmx:beforeSwap"' in script
    assert "arriving === loadedAssets()" in script
    assert "detail.shouldSwap = false;" in script
    assert 'detail.requestConfig.verb !== "get"' in script
