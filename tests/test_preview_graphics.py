"""Tests for high-fidelity prediction box graphics renderer."""

from __future__ import annotations

from ravan.ui.preview_graphics import render_style_chassis

ALL_STYLES = [
    "macos",
    "modern",
    "fluent",
    "compact",
    "glass",
    "classic",
    "material",
    "ios",
    "minimal",
    "neon",
]


def test_render_all_styles_rgba():
    for style in ALL_STYLES:
        img = render_style_chassis(style=style, width=260, height=216, is_dark=True)
        assert img.size == (260, 216)
        assert img.mode == "RGBA"


def test_render_custom_colors():
    custom = {
        "bg": "#0D1B2A",
        "border": "#415A77",
        "highlight": "#1B263B",
        "accent": "#778DA9",
    }
    img = render_style_chassis(style="macos", width=280, height=110, custom_colors=custom)
    assert img.size == (280, 110)


def test_render_light_mode():
    for style in ("macos", "classic", "modern"):
        img = render_style_chassis(style=style, width=240, height=100, is_dark=False)
        assert img.size == (240, 100)


def test_render_horizontal_layout_distinct_from_vertical():
    for style in ALL_STYLES:
        img_v = render_style_chassis(style=style, width=260, height=216, layout="vertical")
        img_h = render_style_chassis(style=style, width=276, height=64, layout="horizontal")
        assert img_h.size == (276, 64)
        assert img_h.tobytes() != img_v.resize((276, 64)).tobytes()

