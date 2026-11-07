"""The axcenity theme is the only source of colour."""

import re

import pytest
from django.conf import settings

SOURCE_CSS = settings.BASE_DIR / "styles" / "source.css"

# The editor's dark palette (Axcenity Engine, crates/editor/src/theme.rs).
EDITOR_PALETTE = {
    "#171717",  # app_bg
    "#1E1E1E",  # panel
    "#242424",  # surface
    "#292929",  # elevated
    "#191919",  # inset
    "#2A2A2A",  # control
    "#323232",  # control_hover
    "#3A3A3A",  # control_active
    "#303030",  # border
    "#424242",  # border_strong
    "#E8E8EA",  # text
    "#FAFAFA",  # text_strong
    "#A1A1AA",  # text_secondary
    "#8E8E96",  # text_weak
    "#63636B",  # text_muted
    "#4CC38A",  # success
    "#E5B454",  # warning
    "#F07178",  # error
}
TYPE_COLOURS = {"texture": "#F2A15A", "hdri": "#6C8CFF", "model": "#4CC38A", "sound": "#A48AFF"}
# The light theme: a light storm grey (user request, 2026-11-06). It began as the
# engine's light palette (theme.rs, Palette::new with dark = false), which the user
# found too bright; the surfaces are now a cool mid grey, the text and lines darker.
LIGHT_PALETTE = {
    "app": "#BEC0C2",
    "panel": "#CACCCE",
    "surface": "#D3D5D7",
    "elevated": "#DCDEE0",
    "inset": "#C4C6C8",
    "control": "#BABCBE",
    "control-hover": "#B2B4B6",
    "control-active": "#A9ABAD",
    "line": "#B5B7B9",
    "line-strong": "#9FA1A3",
    "fg": "#1F2022",
    "fg-strong": "#111214",
    "fg-secondary": "#3D3F43",
    "fg-weak": "#45474B",
    "fg-muted": "#6E7075",
    "shade": "#2B2D31",
    "ink": "#18181B",
}
LIGHT_STATUS = {"success": "#145A36", "warning": "#6B4800", "error": "#931F1F"}
# The engine's on-light accents for the four types (4.5:1 on white).
LIGHT_TYPE_COLOURS = {
    "texture": "#A8460B",
    "hdri": "#3451D1",
    "model": "#1C7547",
    "sound": "#6741D9",
}
# Decorative vivid colours for the ambient glow behind each page, one trio per
# page. They're the only colour besides type, and may be used nowhere else.
# (Named "pastels" from their first version; the user asked for brighter.)
PAGE_PASTELS = {
    "home": {"#FF4FA3", "#FFC23D", "#2EE6C5"},
    "discover": {"#2ED8FF", "#B04DFF", "#FF5CC8"},
    "library": {"#FFD93D", "#FF6A4D", "#FF3D8B"},
    "packs": {"#9BF03B", "#2FC8FF", "#C15CFF"},
    "account": {"#FF5C8A", "#8F5CFF", "#3EE6E0"},
    "settings": {"#4DE1FF", "#FF7AD9", "#B8FF4D"},
    "attribution": {"#FFE14D", "#FF4D6D", "#4DFFB8"},
}
ALL_PASTELS = set().union(*PAGE_PASTELS.values())
ALLOWED = (
    EDITOR_PALETTE
    | set(TYPE_COLOURS.values())
    | {"#FFFFFF", "#000000"}
    | ALL_PASTELS
    | set(LIGHT_PALETTE.values())
    | set(LIGHT_STATUS.values())
    | set(LIGHT_TYPE_COLOURS.values())
)


@pytest.fixture(scope="module")
def css():
    return SOURCE_CSS.read_text(encoding="utf-8")


def test_tailwind_default_palette_is_reset(css):
    theme_block = css.split("@theme {", 1)[1]
    assert "--color-*: initial;" in theme_block


def test_daisyui_builtin_themes_are_off(css):
    assert re.search(r'@plugin "daisyui" \{\s*themes: false;\s*\}', css)


def test_axcenity_is_the_only_and_default_theme(css):
    names = re.findall(r"^\s*name: \"([^\"]+)\";", css, re.M)
    assert names == ["axcenity"]
    theme = css.split('@plugin "daisyui/theme" {', 1)[1].split("}", 1)[0]
    assert "default: true;" in theme
    assert "color-scheme: dark;" in theme


def test_every_colour_is_in_the_axcenity_palette(css):
    stray = {h.upper() for h in re.findall(r"#[0-9A-Fa-f]{3,8}\b", css)} - ALLOWED
    assert not stray, f"colours outside the axcenity palette: {sorted(stray)}"
    assert not re.search(r"\b(rgb|rgba|hsl|hsla|oklch|oklab)\(", css)


def test_primary_buttons_are_white_with_dark_text(css):
    assert "--color-primary: #FAFAFA;" in css
    assert "--color-primary-content: #171717;" in css


@pytest.mark.parametrize(("kind", "hex_value"), TYPE_COLOURS.items())
def test_type_colours_are_design_tokens(css, kind, hex_value):
    assert f"--color-{kind}: {hex_value};" in css


def test_chrome_tokens_are_monochrome(css):
    theme = css.split('@plugin "daisyui/theme" {', 1)[1].split("}", 1)[0]
    for token in ("base-100", "base-200", "base-300", "primary", "secondary", "accent", "neutral"):
        value = re.search(rf"--color-{token}: (#[0-9A-Fa-f]{{6}});", theme).group(1)
        r, g, b = (int(value[i : i + 2], 16) for i in (1, 3, 5))
        assert max(r, g, b) - min(r, g, b) <= 4, f"{token} {value} is not grey"


def test_every_page_has_a_drop_glow_palette(css):
    for page, pastels in PAGE_PASTELS.items():
        rule = re.search(rf'#content\[data-drop="{page}"\]\s*\{{([^}}]*)\}}', css)
        assert rule, f"no drop palette for {page}"
        assert {h.upper() for h in re.findall(r"#[0-9A-Fa-f]{6}", rule.group(1))} == pastels


def test_pastels_appear_only_in_the_drop_glow_rules(css):
    for line in css.splitlines():
        hexes = {h.upper() for h in re.findall(r"#[0-9A-Fa-f]{6}", line)}
        if hexes & ALL_PASTELS:
            assert line.startswith("#content[data-drop="), line


def test_pastels_are_never_type_colours():
    assert not ALL_PASTELS & set(TYPE_COLOURS.values())
    assert not ALL_PASTELS & EDITOR_PALETTE


@pytest.fixture(scope="module")
def light_block(css):
    block = css.split('html[data-scheme="light"] {', 1)[1]
    return block.split("\n}", 1)[0]


def test_light_mode_is_chosen_on_html(css, light_block):
    """<html data-scheme="light"> turns the site light: the member's choice, or the
    system's when they chose System (base.html resolves it before first paint)."""
    assert '&, & [data-theme="axcenity"] {' in light_block
    assert "color-scheme: light;" in light_block
    # No media query of its own: System is resolved in base.html, so Light and Dark
    # can override the computer's setting.
    assert "@media (prefers-color-scheme" not in css


@pytest.mark.parametrize(("token", "hex_value"), LIGHT_PALETTE.items())
def test_light_mode_uses_the_storm_grey_palette(light_block, token, hex_value):
    assert f"--color-{token}: {hex_value};" in light_block


@pytest.mark.parametrize(("kind", "hex_value"), LIGHT_TYPE_COLOURS.items())
def test_light_mode_has_on_light_type_colours(light_block, kind, hex_value):
    assert f"--color-{kind}: {hex_value};" in light_block


def test_light_mode_flips_primary_buttons_and_contrast_tokens(light_block):
    assert "--color-primary: #18181B;" in light_block
    assert "--color-primary-content: #FFFFFF;" in light_block
    assert "--color-ink: #18181B;" in light_block
    assert "--color-on-ink: #FFFFFF;" in light_block
    for status, hex_value in LIGHT_STATUS.items():
        assert f"--color-{status}: {hex_value};" in light_block


def test_light_mode_keeps_the_chrome_monochrome(light_block):
    for token in ("base-100", "base-200", "base-300", "primary", "secondary", "neutral"):
        value = re.search(rf"--color-{token}: (#[0-9A-Fa-f]{{6}});", light_block).group(1)
        r, g, b = (int(value[i : i + 2], 16) for i in (1, 3, 5))
        assert max(r, g, b) - min(r, g, b) <= 4, f"{token} {value} is not grey"


def _luminance(hex_value: str) -> float:
    channels = [int(hex_value[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(a: str, b: str) -> float:
    high, low = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def test_light_mode_is_a_storm_grey_not_white():
    """The surfaces are a mid grey, so the theme is no longer bright white."""
    for token in ("app", "panel", "surface", "elevated", "inset"):
        assert _luminance(LIGHT_PALETTE[token]) < 0.75, token


@pytest.mark.parametrize("background", ["app", "panel", "surface", "inset"])
def test_light_mode_text_keeps_its_contrast_on_the_grey(background):
    surface = LIGHT_PALETTE[background]
    for token in ("fg", "fg-strong", "fg-secondary", "fg-weak"):
        assert _contrast(LIGHT_PALETTE[token], surface) >= 4.5, (token, background)
    for status, hex_value in LIGHT_STATUS.items():
        assert _contrast(hex_value, surface) >= 4.5, (status, background)
    # The type colours are only ever icons, which need 3:1.
    for kind, hex_value in LIGHT_TYPE_COLOURS.items():
        assert _contrast(hex_value, surface) >= 3, (kind, background)


def test_light_mode_inverts_the_logo_and_tints_the_glow(light_block):
    assert "--logo-filter: invert(1);" in light_block
    assert "--logo-filter-hover: none;" in light_block
    # Screen blending would wash the glow out on white.
    assert "& .ambient-drop { mix-blend-mode: multiply; }" in light_block


def test_every_block_in_the_stylesheet_is_closed_once(css):
    """A stray line once closed @layer components early, and Tailwind refused the file."""
    depth = 0
    for number, line in enumerate(re.sub(r"/\*.*?\*/", "", css, flags=re.S).splitlines(), 1):
        depth += line.count("{") - line.count("}")
        assert depth >= 0, f"source.css closes a block that isn't open near line {number}"
    assert depth == 0
