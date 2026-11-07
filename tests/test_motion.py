"""Branding motion and reduced motion (Phase 13): the wordmark's wipe and shine, the
mark's cut-in and parallax, the logo loader, the cursor spotlight, cards blurring up,
View Transitions on fragment swaps, and nothing moving under reduced motion."""

import re
from types import SimpleNamespace

import pytest
from django.conf import settings
from django.template.loader import render_to_string
from django.test import Client
from django.urls import reverse

pytestmark = pytest.mark.django_db

STATIC = settings.BASE_DIR / "static"
SOURCE = settings.BASE_DIR / "styles" / "source.css"

PUBLIC_PAGES = ["packs:home", "catalog:discover", "packs:attribution", "accounts:login"]
MEMBER_PAGES = ["packs:home", "catalog:discover", "catalog:library", "packs:list", "packs:create"]
MEMBER_PAGES += ["packs:attribution_assets", "accounts:settings", "accounts:token"]

SPOTLIGHT = ".result-card, .type-tile, .gallery-card, .pack-card, .pack-row"
SPINNER = re.compile(
    r"\b(loading-(spinner|dots|ring|ball|bars|infinity)|animate-(spin|ping|pulse|bounce))\b"
)


def css() -> str:
    return SOURCE.read_text(encoding="utf-8")


def script(name: str) -> str:
    return (STATIC / "js" / name).read_text(encoding="utf-8")


def rule(selector: str, last: bool = False) -> str:
    """The declarations of the first (or `last`) rule written exactly as `selector {`."""
    parts = css().split(f"{selector} {{")
    return (parts[-1] if last else parts[1]).split("}", 1)[0]


def keyframes(name: str) -> str:
    """The body of `@keyframes name`, written on one line in source.css."""
    line = next(
        line for line in css().splitlines() if line.strip().startswith(f"@keyframes {name} {{")
    )
    return line.split("{", 1)[1]


def reduced_blocks() -> list[str]:
    """Every top-level `@media (prefers-reduced-motion: reduce)` block's body."""
    parts = css().split("@media (prefers-reduced-motion: reduce) {")[1:]
    return [part.split("\n}", 1)[0] for part in parts]


def every_template() -> list:
    roots = [settings.BASE_DIR / "templates"]
    roots += [settings.BASE_DIR / app / "templates" for app in ("catalog", "packs", "accounts")]
    return [path for root in roots for path in root.rglob("*.html")]


@pytest.fixture
def pages(client, django_user_model, password):
    """Every page's HTML, signed out and signed in."""
    rendered = [client.get(reverse(name)).content.decode() for name in PUBLIC_PAGES]
    member = Client()
    member.force_login(django_user_model.objects.create_user("motion_member", password=password))
    rendered += [member.get(reverse(name)).content.decode() for name in MEMBER_PAGES]
    return rendered


# ---------- The motion script ----------


def test_the_motion_script_loads_once_on_every_page(pages):
    for html in pages:
        head = html.split("</head>", 1)[0]
        assert len(re.findall(r'<script src="/static/js/motion\.js\?v=\d+" defer>', head)) == 1


def test_the_motion_script_listens_on_the_document():
    """Swapped-in content needs nothing re-bound."""
    motion = script("motion.js")
    for event in ("htmx:beforeSend", "htmx:beforeTransition", "pointermove"):
        assert f'document.addEventListener(\n    "{event}"' in motion or (
            f'document.addEventListener("{event}"' in motion
        )


# ---------- The logo loader ----------


def test_the_loader_is_the_mark_with_a_light_sweep():
    labelled = render_to_string("partials/loader.html", {"label": "Searching", "small": True})
    assert 'class="ax-loader is-small"' in labelled
    assert '<i class="ax-loader-mark" aria-hidden="true"></i>' in labelled
    assert '<span class="ax-loader-label">Searching</span>' in labelled
    bare = render_to_string("partials/loader.html")
    assert '<span class="sr-only">Loading</span>' in bare and "is-small" not in bare
    mark = rule(".ax-loader-mark")
    assert "mask: var(--mark-url) center / contain no-repeat;" in mark
    assert "background: var(--loader-band);" in mark
    assert "animation: loader-sweep 1.3s" in mark and "infinite" in mark
    # Monochrome: the band is grey and ink only.
    band = rule(":root", last=True).split("--loader-band:", 1)[1]
    assert set(re.findall(r"var\((--[\w-]+)\)", band)) == {"--color-fg-muted", "--color-ink"}


def test_the_status_bar_mark_is_the_loader_while_htmx_works(pages):
    """Every htmx request, boosted navigation included, shows the logo loader."""
    for html in pages:
        status_bar = html.split('id="status-bar"', 1)[1]
        assert re.search(
            r'id="status-loader"[^>]*><i class="mark status-mark w-3" aria-hidden="true">',
            status_bar,
        )
    busy = rule("html[data-busy] .status-mark")
    assert "background: var(--loader-band);" in busy and "animation: loader-sweep" in busy
    motion = script("motion.js")
    # From beforeSend to the request's own loadend, shown after 150 ms.
    assert 'xhr.addEventListener(\n      "loadend"' in motion
    assert 'root.dataset.busy = "";' in motion and "delete root.dataset.busy;" in motion
    assert "}, 150);" in motion
    assert 'content.setAttribute("aria-busy", "true")' in motion


def test_pending_shelves_show_the_loader(client, monkeypatch):
    html = client.get(
        reverse("catalog:discover"), {"type": "texture", "q": "brick"}
    ).content.decode()
    shelves = re.findall(r'<section id="shelf-[^"]+"[^>]*aria-busy="true".*?</section>', html, re.S)
    assert len(shelves) == 2
    for shelf in shelves:
        head = shelf.split("</header>", 1)[0]
        assert "ax-loader" in head and '<span class="ax-loader-label">Searching</span>' in head
        # The skeleton tiles hold the layout; the loader isn't on them.
        body = shelf.split("</header>", 1)[1]
        grid = body.split('<ul class="result-grid"', 1)[1].split("</ul>", 1)[0]
        assert "ax-loader" not in grid
        assert grid.count('<span class="result-skeleton-thumb"></span>') == 6
        # A badge floats over their middle with the loader and the provider's name.
        badge = body.split('<div class="shelf-loading-badge" aria-hidden="true">', 1)[1]
        name = re.search(r'<h2 id="[^"]+" class="micro text-fg-strong">([^<]+)</h2>', head)[1]
        assert '<i class="ax-loader-mark" aria-hidden="true"></i>' in badge
        assert f'<span class="ax-loader-label">Searching {name}</span>' in badge


def test_load_more_shows_the_loader_while_it_runs():
    shelf = SimpleNamespace(
        more_id="shelf-ambientcg-more", error=None, has_more=True, next_url="/next", page_size=12
    )
    html = render_to_string("catalog/partials/load_more.html", {"shelf": shelf})
    busy = html.split('class="shelf-more-busy"', 1)[1].split("</button>", 1)[0]
    assert "ax-loader-mark" in busy and "Loading…" in busy
    assert ".shelf-more-button.htmx-request .shelf-more-busy { display: inline-flex; }" in css()


def test_the_picker_and_the_drawer_load_with_the_loader():
    picker = script("card-actions.js")
    assert '<i class="ax-loader-mark" aria-hidden="true"></i>' in picker
    assert "Loading your packs…" in picker
    drawer = script("entry-drawer.js")
    saving = drawer.split('if (state === "saving") {', 1)[1].split("}", 1)[0]
    assert 'mark.className = "ax-loader-mark";' in saving


def test_the_loader_never_sits_on_a_thumbnail():
    """The logo never goes on a provider's image, so a card's corner keeps its pulse."""
    for name in (
        "catalog/partials/result_card.html",
        "catalog/partials/library_card.html",
        "catalog/partials/save_button.html",
        "catalog/partials/save_error.html",
        "catalog/partials/in_library.html",
        "catalog/partials/sound_play.html",
        "packs/partials/gallery_card.html",
        "packs/partials/hero_orbit.html",
    ):
        source = next(path for path in every_template() if path.as_posix().endswith(name))
        text = source.read_text(encoding="utf-8")
        assert "ax-loader" not in text and "partials/loader.html" not in text, name
    assert "animation: shelf-pulse" in rule(
        ".card-actions .htmx-request .card-action, .card-actions .htmx-request.card-action"
    )


def test_no_spinner_classes_are_left():
    for path in every_template():
        text = path.read_text(encoding="utf-8")
        assert not SPINNER.search(text), path
        for classes in re.findall(r'class="([^"]*)"', text):
            assert "spinner" not in classes and "loading" not in classes.split(), path
    for path in (STATIC / "js").glob("*.js"):
        assert not SPINNER.search(path.read_text(encoding="utf-8")), path
    assert not SPINNER.search(css())
    assert not re.search(r"\.(spinner|loading)\b", css())


# ---------- The wordmark and the mark ----------


def test_the_wordmark_wipes_in_and_shines(client):
    html = client.get(reverse("catalog:discover")).content.decode()
    brand = re.search(r'<a [^>]*id="brand-link"[^>]*>.*?</a>', html, re.S).group(0)
    assert '<i class="brand-shine" aria-hidden="true"></i>' in brand
    # The wipe, on a full load only.
    assert "html:not([data-booted]) .brand-link { animation: brand-wipe 0.9s" in css()
    assert "}, 1600);" in script("motion.js") and 'root.dataset.booted = "";' in script("motion.js")
    # The shine: an ink band masked to the wordmark, while the letters dim, in step.
    shine = rule(".brand-shine")
    assert "mask: var(--word-url) center / contain no-repeat;" in shine
    band = rule(".brand-shine::before")
    assert (
        "var(--color-ink)" in band and "animation: brand-shine 12s ease-in-out 3s infinite;" in band
    )
    assert "animation: brand-dim 12s ease-in-out 3s infinite;" in rule(".brand-link img", last=True)
    # Off while the chip is hovered (behind the hover gate) and inverted.
    assert (
        "html[data-pointer] .brand-link:hover .brand-shine, .brand-link:focus-visible .brand-shine "
        "{ visibility: hidden; }" in css()
    )


def test_the_page_mark_cuts_in_and_drifts_behind_the_content():
    assert "html:not([data-booted]) .hero-mark { animation: mark-cut 1.2s" in css()
    supports = css().split("@supports (animation-timeline: scroll()) {", 1)[1].split("\n}", 1)[0]
    assert "#content { scroll-timeline: --page block; }" in supports
    assert "animation: atmosphere-drift linear both; animation-timeline: --page;" in supports
    assert "transform: translateY(24rem);" in keyframes("atmosphere-drift")
    # No giant wordmark comes back (the user had it removed, story 104).
    assert ".watermark" not in css()


# ---------- Spotlight and cards ----------


def test_the_cursor_spotlight_is_monochrome_and_mouse_only():
    spot = rule(f":is({SPOTLIGHT})::before", last=True)
    assert "pointer-events: none;" in spot and "opacity: 0;" in spot
    assert "color-mix(in srgb, var(--color-ink) var(--spot-alpha, 9%), transparent)" in spot
    assert not re.search(r"#[0-9A-Fa-f]{3,8}|--color-(texture|hdri|model|sound)", spot)
    assert f"html[data-pointer] :is({SPOTLIGHT})[data-spot]::before {{ opacity: 1; }}" in css()
    motion = script("motion.js")
    assert f'var SPOTLIGHT = "{SPOTLIGHT}";' in motion
    assert 'event.pointerType !== "mouse" || reduce.matches' in motion
    assert '"--spot-x"' in motion and '"--spot-y"' in motion


def test_cards_blur_up_one_after_another():
    grids = ".result-grid > .result-card, .gallery-grid > .gallery-card, .pack-grid > .pack-card, .pack-rows > .pack-row"
    entry = rule(f":is({grids})")
    assert "animation: card-in 0.5s cubic-bezier(0.2, 0.8, 0.2, 1) backwards;" in entry
    assert "animation-delay: calc(var(--stagger, 0) * 40ms);" in entry
    for position in range(2, 13):
        assert f":nth-child(12n+{position}) {{ --stagger: {position - 1}; }}" in css()
    assert "filter: blur(10px)" in keyframes("card-in")


def test_cards_lift_on_hover_in_monochrome_behind_the_gate():
    cards = ".result-card, .gallery-card, .pack-card"
    lift = rule(f"html[data-pointer] :is({cards}):hover")
    assert "transform: translateY(-4px);" in lift and "z-index: 2;" in lift
    # The strip under a risen card keeps the hover, so it never jitters.
    assert "inset: 100% 0 auto; height: 4px;" in rule(
        f"html[data-pointer] :is({cards}):hover::after"
    )
    shadows = [
        rule("html[data-pointer] .result-card:hover"),
        rule("html[data-pointer] .result-card:hover:has(.result-link:focus-visible)"),
        rule("html[data-pointer] :is(.gallery-card, .pack-card):hover"),
    ]
    shadows += [
        line
        for line in css().splitlines()
        if line.startswith(("html { --lift-shadow:", 'html[data-scheme="light"] { --lift-shadow:'))
    ]
    assert len(shadows) == 5
    for shadow in shadows:
        assert "--lift-shadow" in shadow
        assert not re.search(r"#[0-9A-Fa-f]{3,8}|--color-(texture|hdri|model|sound)", shadow)
    assert "transform: scale(1.07);" in rule(
        "html[data-pointer] .result-card:hover .result-thumb img"
    )
    assert any(
        f"html[data-pointer] :is({cards}):hover," in block and "transform: none;" in block
        for block in reduced_blocks()
    )


def test_library_and_gallery_cards_sit_in_the_animated_grids(member_client, member, make_asset):
    from catalog.models import SavedAsset

    SavedAsset.objects.create(user=member, asset=make_asset(external_id="Bricks001"))
    html = member_client.get(reverse("catalog:library")).content.decode()
    assert re.search(r'<ul class="result-grid"[^>]*>\s*<li class="result-card library-card', html)


# ---------- View Transitions ----------


def test_fragment_swaps_crossfade_in_place(client):
    import json

    html = client.get(reverse("catalog:discover")).content.decode()
    config = json.loads(re.search(r'<meta name="htmx-config" content=\'([^\']+)\'>', html).group(1))
    assert config["globalViewTransitions"] is True
    motion = script("motion.js")
    transition = motion.split('document.addEventListener("htmx:beforeTransition"', 1)[1].split(
        "});", 1
    )[0]
    assert "if (boosted) delete root.dataset.swap;" in transition
    assert 'else root.dataset.swap = "fragment";' in transition
    assert (
        'html[data-swap="fragment"]::view-transition-old(content) { animation: swap-out 0.2s'
        in css()
    )
    assert (
        'html[data-swap="fragment"]::view-transition-new(content) { animation: swap-in 0.2s'
        in css()
    )
    # A crossfade: opacity only, so nothing on the page moves.
    for name in ("swap-out", "swap-in"):
        assert "transform" not in keyframes(name) and "opacity: 0;" in keyframes(name)
    # Boosted navigation keeps its drop and rise.
    assert "::view-transition-new(content) { animation: page-in " in css()


def test_motion_degrades_where_the_browser_lacks_it():
    """htmx starts a View Transition only where document.startViewTransition exists, so
    nothing here calls it; the parallax needs scroll timelines, so it sits behind @supports."""
    for path in (STATIC / "js").glob("*.js"):
        assert "startViewTransition(" not in path.read_text(encoding="utf-8"), path
    outside = css().replace(
        css().split("@supports (animation-timeline: scroll()) {", 1)[1].split("\n}", 1)[0], ""
    )
    assert "animation-timeline: --" not in outside and "scroll-timeline: --" not in outside


# ---------- Reduced motion ----------


def test_reduced_motion_stops_every_animation_and_transition():
    blanket = (
        "*, *::before, *::after { animation: none !important; transition: none !important; "
        "scroll-behavior: auto !important; }"
    )
    assert any(blanket in block for block in reduced_blocks())
    assert any(
        "::view-transition-group(*), ::view-transition-old(*), ::view-transition-new(*) "
        "{ animation: none !important; }" in block
        for block in reduced_blocks()
    )
    # The spotlight isn't lit, and the scripts check the setting too.
    assert any(
        f":is({SPOTLIGHT})::before {{ display: none; }}" in block for block in reduced_blocks()
    )
    assert 'matchMedia("(prefers-reduced-motion: reduce)")' in script("motion.js")
    assert "prefers-reduced-motion" in script("scroll-ruler.js")


def test_reduced_motion_still_shows_the_loader_still():
    """It comes after the loader's own rules, which it has to beat."""
    still = (
        ".ax-loader-mark, html[data-busy] .status-mark { background: var(--color-fg-secondary); }"
    )
    assert any(still in block for block in reduced_blocks())
    assert css().rindex(still) > css().index("html[data-busy] .status-mark {")


@pytest.mark.parametrize(
    ("name", "resting"),
    [
        ("card-in", None),
        ("swap-in", None),
        ("drawer-in", None),
        ("brand-wipe", "clip-path: inset(0 0 0 0);"),
        ("mark-cut", "clip-path: polygon(0 0, 200% 0, 0 200%);"),
    ],
)
def test_entry_animations_end_on_the_resting_style(name, resting):
    """With animation off, content shows in its final state: an entry animation either
    has only a `from` (so it ends on the element's own style) or ends fully shown."""
    body = keyframes(name)
    assert body.lstrip().startswith("from {")
    if resting is None:
        assert " to {" not in body and "%" not in body.split("{", 1)[0]
    else:
        assert f"to {{ {resting} }}" in body


def test_every_animation_names_keyframes_that_exist():
    defined = set(re.findall(r"@keyframes ([\w-]+)", css()))
    used = {
        name for name in re.findall(r"animation:\s*([a-z][\w-]*)", css()) if name not in ("none",)
    }
    assert used and used <= defined, used - defined


def test_the_ruler_and_the_orbit_stay_still_under_reduced_motion():
    """Phase 12 asked for them to stay on the sweep's list."""
    first = reduced_blocks()[0]
    assert ".orbit-ring, .orbit-face { animation: none; }" in first
    assert ".orbit-face, .scroll-ruler-label, .scroll-ruler-tick { transition: none; }" in first
