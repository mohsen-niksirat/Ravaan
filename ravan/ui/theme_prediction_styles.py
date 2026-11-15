"""Prediction popup design presets and WCAG contrast helpers."""

from __future__ import annotations

from dataclasses import dataclass, replace

from ravan.ui.theme_palettes import Palette, get_active_palette, get_macos_palette


@dataclass(frozen=True)
class PredictionStyleTokens:
    name: str
    palette: Palette
    corner_radius: float = 8.0
    row_padding_y: int = 4
    row_padding_x: int = 10
    show_separators: bool = False
    separator_color: str = ""
    badge_style: str = "plain"  # "plain" | "circle" | "cyan" | "none"
    selected_row_style: str = "fill"  # "fill" | "leading_bar" | "pill" | "bold_only" | "neon"
    accent_bar_color: str = ""
    show_hint_bar: bool = True
    show_grip: bool = True
    text_align: str = "w"  # "w" | "center"
    confidence_meter_always: bool = False
    border_width: int = 1
    border_color: str = ""
    border_relief: str = "flat"
    alpha: float = 0.95
    acrylic: bool = False
    layout: str = "vertical"  # "vertical" | "horizontal"


def get_fluent_palette(mode: str = "auto") -> Palette:
    """Windows 11 Fluent / Mica palette with subtle elevation and Windows blue accents."""
    base = get_active_palette(mode)
    if base.name == "high_contrast":
        return base
    if base.name == "light":
        return Palette(
            name="fluent_light", bg="#F3F3F3", fg="#1B1B1B", subtext="#5D5D5D", card_bg="#FFFFFF",
            accent="#0067C0", border="#E5E5E5", highlight="#FFFFFF", highlight_fg="#1B1B1B",
            alpha=0.96, corner_radius=8.0, accent_hover="#0078D4", card_border="#E5E5E5",
            input_bg="#FFFFFF", button_bg="#FFFFFF", button_hover="#EDEBE9", badge_bg="#EFF6FC",
            badge_fg="#0067C0", glow="#0067C0",
        )
    return Palette(
        name="fluent_dark", bg="#2C2C2C", fg="#FFFFFF", subtext="#A0A0A0", card_bg="#383838",
        accent="#4CC2FF", border="#454545", highlight="#383838", highlight_fg="#FFFFFF",
        alpha=0.96, corner_radius=8.0, accent_hover="#70D1FF", card_border="#454545",
        input_bg="#262626", button_bg="#383838", button_hover="#444444", badge_bg="#2C2C2C",
        badge_fg="#4CC2FF", glow="#4CC2FF",
    )


def get_material_palette(mode: str = "auto") -> Palette:
    """Google Material You expressive tonal palette."""
    base = get_active_palette(mode)
    if base.name == "high_contrast":
        return base
    if base.name == "light":
        return Palette(
            name="material_light", bg="#ECE6F0", fg="#1D1B20", subtext="#49454F", card_bg="#E8DEF8",
            accent="#6750A4", border="#ECE6F0", highlight="#E8DEF8", highlight_fg="#1D1B20",
            alpha=0.96, corner_radius=20.0, accent_hover="#7F67BE", card_border="#ECE6F0",
            input_bg="#F7F2FA", button_bg="#E8DEF8", button_hover="#D9CCE8", badge_bg="#EADDFF",
            badge_fg="#6750A4", glow="#6750A4",
        )
    return Palette(
        name="material_dark", bg="#211A26", fg="#E6E1E5", subtext="#CAC4D0", card_bg="#4A4458",
        accent="#D0BCFF", border="#211A26", highlight="#4A4458", highlight_fg="#FFFFFF",
        alpha=0.96, corner_radius=20.0, accent_hover="#E8DEF8", card_border="#211A26",
        input_bg="#1D192B", button_bg="#4A4458", button_hover="#5C556C", badge_bg="#383244",
        badge_fg="#D0BCFF", glow="#D0BCFF",
    )


def get_ios_palette(mode: str = "auto") -> Palette:
    """MacBook & iOS floating panel style."""
    base = get_active_palette(mode)
    if base.name == "high_contrast":
        return base
    if base.name == "light":
        return Palette(
            name="ios_light", bg="#F5F5F7", fg="#1D1D1F", subtext="#86868B", card_bg="#FFFFFF",
            accent="#007AFF", border="#D2D2D7", highlight="#007AFF", highlight_fg="#FFFFFF",
            alpha=0.95, corner_radius=16.0, accent_hover="#0051A8", card_border="#E5E5EA",
            input_bg="#FFFFFF", button_bg="#E5E5EA", button_hover="#D1D1D6", badge_bg="#E5E5EA",
            badge_fg="#007AFF", glow="#007AFF",
        )
    return Palette(
        name="ios_dark", bg="#1E1E22", fg="#F5F5F7", subtext="#98989D", card_bg="#2C2C30",
        accent="#0A84FF", border="#3A3A40", highlight="#0A84FF", highlight_fg="#FFFFFF",
        alpha=0.94, corner_radius=16.0, accent_hover="#3395FF", card_border="#3A3A40",
        input_bg="#161618", button_bg="#2C2C30", button_hover="#3A3A3E", badge_bg="#2C2C32",
        badge_fg="#0A84FF", glow="#0A84FF",
    )


def get_minimal_palette(mode: str = "auto") -> Palette:
    """Linear / Notion monochrome styling."""
    base = get_active_palette(mode)
    if base.name == "high_contrast":
        return base
    if base.name == "light":
        return Palette(
            name="minimal_light", bg="#FFFFFF", fg="#111111", subtext="#888888", card_bg="#F8F8F8",
            accent="#666666", border="#FFFFFF", highlight="#F5F5F5", highlight_fg="#000000",
            alpha=0.98, corner_radius=4.0, accent_hover="#444444", card_border="#FFFFFF",
            input_bg="#FAFAFA", button_bg="#F2F2F2", button_hover="#E6E6E6", badge_bg="#F0F0F0",
            badge_fg="#555555", glow="#888888",
        )
    return Palette(
        name="minimal_dark", bg="#000000", fg="#E0E0E0", subtext="#666666", card_bg="#111111",
        accent="#888888", border="#000000", highlight="#1A1A1A", highlight_fg="#FFFFFF",
        alpha=0.98, corner_radius=4.0, accent_hover="#AAAAAA", card_border="#000000",
        input_bg="#0A0A0A", button_bg="#161616", button_hover="#222222", badge_bg="#111111",
        badge_fg="#888888", glow="#666666",
    )


def get_neon_palette(mode: str = "auto") -> Palette:
    """Dark cyberpunk / gaming palette."""
    return Palette(
        name="neon", bg="#080B12", fg="#00FF66", subtext="#548A6A", card_bg="#121826",
        accent="#FF007F", border="#FF007F", highlight="#2A0820", highlight_fg="#FFFFFF",
        alpha=0.98, corner_radius=6.0, accent_hover="#FF3399", card_border="#FF007F",
        input_bg="#0E131E", button_bg="#180B1E", button_hover="#261030", badge_bg="#26081E",
        badge_fg="#FF007F", glow="#FF007F",
    )


def get_modern_palette(mode: str = "auto") -> Palette:
    """Modern cosmic violet / indigo palette."""
    base = get_active_palette(mode)
    if base.name == "high_contrast":
        return base
    if base.name == "light":
        return Palette(
            name="modern_light", bg="#F5F0FF", fg="#22123B", subtext="#6B5B82", card_bg="#EDE4FC",
            accent="#8A2BE2", border="#DDD0F5", highlight="#8A2BE2", highlight_fg="#FFFFFF",
            alpha=0.96, corner_radius=12.0, badge_bg="#E2D4F8", badge_fg="#8A2BE2", glow="#8A2BE2",
        )
    return Palette(
        name="modern_dark", bg="#181028", fg="#F3E8FF", subtext="#A894C4", card_bg="#26183C",
        accent="#C77DFF", border="#3D2860", highlight="#8A2BE2", highlight_fg="#FFFFFF",
        alpha=0.96, corner_radius=12.0, badge_bg="#352054", badge_fg="#C77DFF", glow="#8A2BE2",
    )


def get_glass_palette(mode: str = "auto") -> Palette:
    """Translucent frosted Aero glass palette."""
    return Palette(
        name="glass", bg="#182230", fg="#FFFFFF", subtext="#8FA6BC", card_bg="#223044",
        accent="#64B5F6", border="#7A9AB8", highlight="#2E466B", highlight_fg="#FFFFFF",
        alpha=0.68, corner_radius=10.0, badge_bg="#203046", badge_fg="#64B5F6", glow="#64B5F6",
    )


def get_classic_palette(mode: str = "auto") -> Palette:
    """Traditional Windows classic desktop styling."""
    return Palette(
        name="classic", bg="#D4D0C8", fg="#000000", subtext="#555555", card_bg="#ECE9D8",
        accent="#0A246A", border="#808080", highlight="#0A246A", highlight_fg="#FFFFFF",
        alpha=1.0, corner_radius=0.0, card_border="#FFFFFF", badge_bg="#D4D0C8",
        badge_fg="#0A246A", glow="#0A246A",
    )


def _raw_prediction_style(name: str = "macos", mode: str = "auto") -> PredictionStyleTokens:
    """Return raw visual design tokens for the specified prediction UI style."""
    raw_name = (name or "macos").strip().lower()
    base_palette = get_active_palette(mode)
    is_dark = base_palette.name in ("dark", "high_contrast") or (
        mode not in ("light", "high_contrast") and base_palette.name == "dark"
    )

    if raw_name == "fluent":
        pal = get_fluent_palette(mode)
        return PredictionStyleTokens(
            name="fluent", palette=pal, corner_radius=8.0, row_padding_y=5, row_padding_x=10,
            show_separators=True, separator_color="#35373E" if is_dark else "#E8E8E8",
            badge_style="plain", selected_row_style="leading_bar", accent_bar_color="#4CC2FF",
            border_width=2 if is_dark else 1, border_color="#4CC2FF" if is_dark else "#0078D4",
            alpha=pal.alpha,
        )
    if raw_name == "material":
        pal = get_material_palette(mode)
        return PredictionStyleTokens(
            name="material", palette=pal, corner_radius=20.0, row_padding_y=6, row_padding_x=14,
            show_separators=True, separator_color="#383244" if is_dark else "#D9CCE8",
            badge_style="circle", selected_row_style="pill", border_width=2,
            border_color="#4B4655" if is_dark else "#CAC4D0", alpha=pal.alpha,
        )
    if raw_name == "ios":
        pal = get_ios_palette(mode)
        return PredictionStyleTokens(
            name="ios", palette=pal, corner_radius=16.0, row_padding_y=6, row_padding_x=14,
            show_separators=True, separator_color="#2D2D30" if is_dark else "#E5E5EA",
            badge_style="circle", selected_row_style="pill", border_width=1,
            border_color=pal.border, alpha=pal.alpha, acrylic=True,
        )
    if raw_name == "minimal":
        pal = get_minimal_palette(mode)
        return PredictionStyleTokens(
            name="minimal", palette=pal, corner_radius=4.0, row_padding_y=4, row_padding_x=10,
            show_separators=True, separator_color="#242428" if is_dark else "#EAEAEA",
            badge_style="keycap", selected_row_style="fill", accent_bar_color="#A0A0B0",
            border_width=2, border_color="#323238" if is_dark else "#D0D0D8", alpha=pal.alpha,
        )
    if raw_name == "neon":
        pal = get_neon_palette(mode)
        return PredictionStyleTokens(
            name="neon", palette=pal, corner_radius=6.0, row_padding_y=4, row_padding_x=10,
            show_separators=True, separator_color="#200B1A", badge_style="cyan",
            selected_row_style="neon", accent_bar_color="#FF007F", confidence_meter_always=True,
            border_width=1, border_color="#FF007F", alpha=pal.alpha,
        )
    if raw_name == "modern":
        pal = get_modern_palette(mode)
        return PredictionStyleTokens(
            name="modern", palette=pal, corner_radius=12.0, row_padding_y=5, row_padding_x=12,
            show_separators=True, separator_color="#46286E" if is_dark else "#DDD0F5",
            badge_style="plain", selected_row_style="pill", border_width=2,
            border_color="#8A2BE2", alpha=pal.alpha,
        )
    if raw_name == "compact":
        pal = get_active_palette(mode)
        return PredictionStyleTokens(
            name="compact", palette=pal, corner_radius=4.0, row_padding_y=3, row_padding_x=8,
            show_separators=True, separator_color="#28282E" if is_dark else "#E0E0E5",
            badge_style="plain", selected_row_style="fill", show_grip=False,
            border_width=1, border_color=pal.border, alpha=pal.alpha,
        )
    if raw_name == "glass":
        pal = get_glass_palette(mode)
        return PredictionStyleTokens(
            name="glass", palette=pal, corner_radius=10.0, row_padding_y=5, row_padding_x=12,
            show_separators=True, separator_color="#3C5573", badge_style="plain",
            selected_row_style="pill", border_width=2, border_color="#8AB4D8",
            alpha=pal.alpha, acrylic=True,
        )
    if raw_name == "classic":
        pal = get_classic_palette(mode)
        return PredictionStyleTokens(
            name="classic", palette=pal, corner_radius=0.0, row_padding_y=3, row_padding_x=8,
            show_separators=False, badge_style="plain", selected_row_style="fill",
            border_width=2, border_color="#808080", border_relief="raised", alpha=1.0,
        )

    pal = get_macos_palette(mode)
    return PredictionStyleTokens(
        name="macos", palette=pal, corner_radius=12.0, row_padding_y=5, row_padding_x=14,
        show_separators=True, separator_color="#36363C" if is_dark else "#D6D6DA",
        badge_style="plain", selected_row_style="fill", border_width=1,
        border_color=pal.border, alpha=0.96, acrylic=True,
    )


def _relative_luminance(hex_color: str) -> float:
    """Compute WCAG 2.1 relative luminance (0.0 dark .. 1.0 light) for '#rrggbb'."""
    try:
        rgb = int(hex_color.strip().lstrip("#"), 16)
        r, g, b = ((rgb >> 16) & 0xFF) / 255.0, ((rgb >> 8) & 0xFF) / 255.0, (rgb & 0xFF) / 255.0
    except (ValueError, AttributeError):
        return 0.0

    def _lin(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def _contrast_ratio(hex_a: str, hex_b: str) -> float:
    la, lb = _relative_luminance(hex_a), _relative_luminance(hex_b)
    lighter, darker = (la, lb) if la >= lb else (lb, la)
    return (lighter + 0.05) / (darker + 0.05)


def _accessible_highlight_fg(highlight_hex: str, preferred_fg: str | None) -> str:
    """Ensure selected-row text stays legible on bright/neon custom highlight colors."""
    if preferred_fg and _contrast_ratio(highlight_hex, preferred_fg) >= 3.0:
        return preferred_fg
    return "#11111B" if _relative_luminance(highlight_hex) > 0.40 else "#FFFFFF"


def _distinct_from_colorkey(hex_color: str, key_color: str) -> str:
    """Ensure a widget surface color never matches the Win32 LWA_COLORKEY transparency color."""
    if not hex_color or not key_color or hex_color.strip().lower() != key_color.strip().lower():
        return hex_color
    try:
        rgb = int(hex_color.strip().lstrip("#"), 16)
        r, g, b = (rgb >> 16) & 0xFF, (rgb >> 8) & 0xFF, rgb & 0xFF
        step = 6 if r < 245 and g < 245 and b < 245 else -6
        return f"#{max(0, min(255, r + step)):02X}{max(0, min(255, g + step)):02X}{max(0, min(255, b + step)):02X}"
    except (ValueError, AttributeError):
        return hex_color


def get_prediction_style(
    name: str = "macos",
    mode: str = "auto",
    custom_colors: dict[str, str] | None = None,
    layout: str = "vertical",
) -> PredictionStyleTokens:
    """Return complete visual & layout design tokens for the specified prediction UI style."""
    tokens = _raw_prediction_style(name, mode)

    if custom_colors:
        c_bg, c_fg = custom_colors.get("bg"), custom_colors.get("fg")
        c_accent, c_border = custom_colors.get("accent"), custom_colors.get("border")
        c_highlight, c_highlight_fg = custom_colors.get("highlight"), custom_colors.get("highlight_fg")

        orig_pal = tokens.palette
        eff_bg = c_bg or orig_pal.bg
        eff_card_bg = c_bg or orig_pal.card_bg
        eff_highlight = c_highlight or orig_pal.highlight
        if tokens.acrylic:
            eff_card_bg = _distinct_from_colorkey(eff_card_bg, eff_bg)
            eff_highlight = _distinct_from_colorkey(eff_highlight, eff_bg)

        eff_highlight_fg = _accessible_highlight_fg(eff_highlight, c_highlight_fg or orig_pal.highlight_fg)
        custom_pal = Palette(
            name=f"{orig_pal.name}_custom", bg=eff_bg, fg=c_fg or orig_pal.fg,
            subtext=orig_pal.subtext, card_bg=eff_card_bg, accent=c_accent or orig_pal.accent,
            border=c_border or orig_pal.border, highlight=eff_highlight, highlight_fg=eff_highlight_fg,
            alpha=orig_pal.alpha, corner_radius=orig_pal.corner_radius,
            accent_hover=c_accent or orig_pal.accent_hover, card_border=c_border or orig_pal.card_border,
            input_bg=eff_card_bg, button_bg=eff_card_bg, button_hover=eff_highlight,
            badge_bg=eff_card_bg, badge_fg=c_accent or orig_pal.badge_fg, glow=c_accent or orig_pal.glow,
        )
        tokens = replace(
            tokens,
            palette=custom_pal,
            border_color=c_border if tokens.border_width > 0 else (c_border or tokens.border_color),
            accent_bar_color=c_accent if tokens.accent_bar_color else "",
            separator_color=c_border if tokens.show_separators else tokens.separator_color,
        )

    if layout == "horizontal":
        return replace(
            tokens,
            layout="horizontal",
            show_separators=True,
            separator_color=tokens.separator_color or tokens.border_color or tokens.palette.border,
            row_padding_y=max(3, min(tokens.row_padding_y, 6)),
            row_padding_x=max(10, tokens.row_padding_x),
        )
    return replace(tokens, layout="vertical")
