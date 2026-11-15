"""Unit and integration tests for Phase 1 Fluent 2 UI Widget Kit and theme tokens."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path

import pytest

from ravan.ui.theme import (
    SPACING,
    Palette,
    create_managed_toplevel,
    destroy_managed_toplevel,
    get_active_palette,
    get_dpi_scale,
)
from ravan.ui.widgets import (
    FluentBadge,
    FluentCard,
    FluentEntry,
    FluentPillButton,
    FluentSectionBanner,
    FluentSegmentedControl,
    FluentToggleSwitch,
    get_icon,
    render_icon_image,
    render_rounded_surface,
    render_toggle_switch_image,
    resolve_icon_name,
)


def test_palette_fluent_elevation_tokens() -> None:
    for mode in ("dark", "light", "high_contrast"):
        pal = get_active_palette(mode)
        assert isinstance(pal, Palette)
        assert pal.bg_base == pal.bg
        assert pal.bg_surface == pal.card_bg
        assert pal.bg_elevated.startswith("#")
        assert pal.bg_interactive == pal.input_bg
        assert pal.border_subtle.startswith("#")
        assert pal.border_focus.startswith("#")
    assert SPACING == (4, 8, 12, 16, 24)
    assert get_dpi_scale(None) == 1.0


@pytest.mark.parametrize(
    "icon_name",
    [
        "sparkle",
        "mic",
        "waveform",
        "hub",
        "check",
        "copy",
        "replace",
        "reset",
        "search",
        "close",
        "eye",
        "eye_off",
        "key",
        "settings",
        "bolt",
        "keyboard",
        "shield",
        "sliders",
        "code",
        "cloud",
        "info",
        "feather",
        "palette",
        "brain",
        "rocket",
        "book",
    ],
)
def test_vector_icons_2x_supersampled_rendering(icon_name: str) -> None:
    img = render_icon_image(icon_name, size=20, color="#8ab4f8", dpi=1.0)
    assert img.mode == "RGBA"
    assert img.size == (20, 20)
    # Verify non-empty alpha channel (icon actually drew visible pixels)
    alpha_extrema = img.getchannel("A").getextrema()
    assert alpha_extrema is not None and alpha_extrema[1] > 0

    # Verify DPI scaling produces proportional crisp dimensions
    img_hidpi = render_icon_image(icon_name, size=20, color="#1a73e8", dpi=1.5)
    assert img_hidpi.size == (30, 30)


def test_icon_emoji_alias_resolution() -> None:
    assert resolve_icon_name("⚙️") == "settings"
    assert resolve_icon_name("✨") == "sparkle"
    assert resolve_icon_name("🎤") == "mic"
    assert resolve_icon_name("📦") == "hub"


def test_surface_and_toggle_pillow_renderers() -> None:
    surf = render_rounded_surface(
        width=180,
        height=48,
        radius=10,
        fill_hex="#292b2f",
        border_hex="#36393f",
        bg_hex="#202124",
        accent_bar_hex="#8ab4f8",
        rtl=True,
    )
    assert surf.mode == "RGBA"
    assert surf.size == (180, 48)

    sw_on = render_toggle_switch_image(is_on=True, hovered=False)
    sw_off = render_toggle_switch_image(is_on=False, hovered=False)
    assert sw_on.size == (40, 22)
    assert sw_off.size == (40, 22)
    assert sw_on.tobytes() != sw_off.tobytes()


def test_fluent_widgets_interactive_lifecycle() -> None:
    try:
        top, owned_root = create_managed_toplevel(None)
    except tk.TclError as exc:
        pytest.skip(f"Tkinter display unavailable: {exc}")

    try:
        pal = get_active_palette("dark")
        ic = get_icon("sparkle", size=16, color=pal.accent, master=top)
        assert ic is not None

        banner = FluentSectionBanner(
            top, icon="settings", title="General", subtitle="Subtitle", palette=pal, rtl=True
        )
        banner.pack(fill="x")

        card = FluentCard(top, title="🎨 Appearance", padding=10, palette=pal, rtl=True)
        card.pack(fill="x")
        assert card.body is card

        badge = FluentBadge(card, text="v3.0.0", palette=pal)
        badge.pack()

        # Toggle switch two-way BooleanVar binding
        bvar = tk.BooleanVar(master=top, value=False)
        toggled_count = 0

        def _on_toggle() -> None:
            nonlocal toggled_count
            toggled_count += 1

        sw = FluentToggleSwitch(
            card,
            text="Smart ZWNJ",
            subtitle="Example subtitle",
            variable=bvar,
            command=_on_toggle,
            palette=pal,
            rtl=True,
        )
        sw.pack(fill="x")
        sw._on_click()
        assert bvar.get() is True
        assert toggled_count == 1
        bvar.set(False)
        assert bvar.get() is False

        # Pill button invoke and state config
        clicked = 0
        btn = FluentPillButton(
            card,
            text="Apply",
            icon="check",
            variant="primary",
            palette=pal,
            command=lambda: None,
        )
        btn.configure(command=lambda: _inc())

        def _inc() -> None:
            nonlocal clicked
            clicked += 1

        btn.pack()
        btn.invoke()
        assert clicked == 1
        btn.configure(state="disabled")
        btn.invoke()
        assert clicked == 1

        # Segmented control
        svar = tk.StringVar(master=top, value="vertical")
        seg = FluentSegmentedControl(
            card,
            options=[("vertical", "Vertical"), ("horizontal", "Horizontal")],
            variable=svar,
            palette=pal,
        )
        seg.pack()
        seg._select("horizontal")
        assert svar.get() == "horizontal"

        # FluentEntry placeholder lifecycle
        evar = tk.StringVar(master=top, value="")
        entry = FluentEntry(
            card,
            textvariable=evar,
            placeholder="دستور دلخواه...",
            palette=pal,
            rtl=True,
            leading_icon="search",
            clearable=True,
            password=True,
        )
        entry.pack(fill="x")
        # While showing placeholder, .get() MUST return "" (never raw placeholder text!)
        assert entry._showing_placeholder is True
        assert entry.get() == ""

        # Focus in clears placeholder
        entry._on_focus_in()
        assert entry._showing_placeholder is False
        entry.entry.insert(0, "سلام")
        entry._on_key_release()
        assert entry.get() == "سلام"
        assert evar.get() == "سلام"

        # Clear resets and restores placeholder when unfocused
        entry.clear()
        entry._on_focus_out()
        assert entry.get() == ""
        assert entry._showing_placeholder is True
    finally:
        destroy_managed_toplevel(top, owned_root)


def test_phase1_modules_respect_line_ceiling() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    phase1_files = [
        "ravan/ui/theme.py",
        "ravan/ui/theme_palettes.py",
        "ravan/ui/theme_prediction_styles.py",
        "ravan/ui/theme_dwm.py",
        "ravan/ui/widgets/__init__.py",
        "ravan/ui/widgets/icons.py",
        "ravan/ui/widgets/surface.py",
        "ravan/ui/widgets/controls.py",
        "ravan/ui/settings.py",
        "ravan/ui/settings_preview.py",
        "ravan/ui/settings_builder.py",
        "ravan/ui/settings_general.py",
        "ravan/ui/settings_prediction.py",
        "ravan/ui/settings_tabs_misc.py",
        "ravan/ui/settings_learning.py",
    ]
    for rel in phase1_files:
        path = repo_root / rel
        line_count = len(path.read_text(encoding="utf-8").splitlines())
        assert line_count <= 425, f"{rel} has {line_count} lines (exceeds Phase 1 modular ceiling)"


def test_i18n_dotted_subkey_resolution_and_locale_cleanliness() -> None:
    from ravan.core.i18n import get_locale, load_locale, set_locale, t

    prev = get_locale()
    try:
        set_locale("en")
        val_en = t("settings.placement.bottom_right")
        assert val_en == "Bottom right — above the tray icons"

        set_locale("fa")
        val_fa = t("settings.placement.bottom_right")
        assert val_fa == "پایین راست — بالای آیکون‌های تری"
        assert "?" not in t("settings.tab_profiles")
        assert "?" not in t("sel_tb.convert")

        for lang in ("en", "fa"):
            data = load_locale(lang)
            for section, entries in data.items():
                if isinstance(entries, dict):
                    for key, text in entries.items():
                        if isinstance(text, str):
                            assert "??" not in text, f"Corrupted mojibake in {lang}.{section}.{key}: {text!r}"
    finally:
        set_locale(prev)
