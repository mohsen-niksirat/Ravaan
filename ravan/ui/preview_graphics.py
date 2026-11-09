"""High-fidelity visual asset renderer for Ravaan prediction box styles.

Generates anti-aliased 2x supersampled card backdrops with true gradients,
specular reflection sheens, macOS traffic lights, Win32 classic 3D beveled
title bars, Material You circular chips, and neon glow effects.
"""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFilter


def _hex_to_rgb(hex_str: str, default: tuple[int, int, int] = (30, 30, 34)) -> tuple[int, int, int]:
    try:
        clean = hex_str.strip().lstrip("#")
        if len(clean) == 3:
            clean = "".join(c * 2 for c in clean)
        num = int(clean, 16)
        return (num >> 16) & 0xFF, (num >> 8) & 0xFF, num & 0xFF
    except Exception:
        return default


def render_style_chassis(
    style: str = "macos",
    width: int = 260,
    height: int = 216,
    is_dark: bool = True,
    custom_colors: dict[str, str] | None = None,
    layout: str = "vertical",
) -> Image.Image:
    """Render a pixel-perfect, anti-aliased chassis backdrop for the prediction box.

    Uses 2x supersampling to produce smooth curved corners, gradients, and specular highlights.
    All 10 styles match the authentic OS/theme visual language with all 5 candidate rows.
    """
    scale = 2
    sw, sh = width * scale, height * scale
    img = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    margin = 8 * scale
    card_w = sw - 2 * margin
    card_h = sh - 2 * margin
    box_rect = [margin, margin, margin + card_w, margin + card_h]

    # Row 1 geometry
    r1_top = margin + 26 * scale
    r1_h = 28 * scale
    r1_bot = r1_top + r1_h

    # Handle custom colors override if specified
    if custom_colors:
        c_bg = _hex_to_rgb(custom_colors.get("bg", "#202024"))
        c_border = _hex_to_rgb(custom_colors.get("border", "#3A3A42"))
        c_hi = _hex_to_rgb(custom_colors.get("highlight", "#0A84FF"))
        c_accent = _hex_to_rgb(custom_colors.get("accent", "#0A84FF"))

        r = 14 * scale
        draw.rounded_rectangle(box_rect, radius=r, fill=(*c_bg, 245), outline=(*c_border, 255), width=2 * scale)
        # Highlight card for row 1
        r1_rect = [margin + 6 * scale, r1_top, margin + card_w - 6 * scale, r1_bot]
        draw.rounded_rectangle(r1_rect, radius=8 * scale, fill=(*c_hi, 235))
        # Accent indicator
        draw.rounded_rectangle(
            [margin + 8 * scale, r1_top + 3 * scale, margin + 12 * scale, r1_bot - 3 * scale],
            radius=2 * scale,
            fill=(*c_accent, 255),
        )
        for i in range(1, 5):
            dy = r1_bot + i * 26 * scale
            draw.line([margin + 12 * scale, dy, margin + card_w - 12 * scale, dy], fill=(*c_border, 120), width=1)
        return img.resize((width, height), Image.Resampling.LANCZOS)

    # ─────────────────────────────────────────────────────────────
    # 1. macOS: Frosted glass + Apple traffic lights (🔴 🟡 🟢)
    # ─────────────────────────────────────────────────────────────
    if style == "macos":
        r = 14 * scale
        # Soft elevation drop shadow
        shadow = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(shadow)
        s_draw.rounded_rectangle(
            [box_rect[0] + 2 * scale, box_rect[1] + 4 * scale, box_rect[2] + 2 * scale, box_rect[3] + 4 * scale],
            radius=r,
            fill=(0, 0, 0, 110),
        )
        shadow = shadow.filter(ImageFilter.GaussianBlur(4 * scale))
        img = Image.alpha_composite(shadow, img)
        draw = ImageDraw.Draw(img)

        # Body chassis
        bg_col = (36, 36, 40, 240) if is_dark else (245, 245, 247, 240)
        border_col = (72, 72, 78, 255) if is_dark else (210, 210, 215, 255)
        draw.rounded_rectangle(box_rect, radius=r, fill=bg_col, outline=border_col, width=2)

        # Traffic lights (Red, Yellow, Green) on top-left
        tl_y = margin + 12 * scale
        dots = [
            (margin + 14 * scale, tl_y, (255, 95, 86)),   # Close red
            (margin + 26 * scale, tl_y, (255, 189, 46)),  # Min yellow
            (margin + 38 * scale, tl_y, (39, 201, 63)),   # Max green
        ]
        dot_r = 4 * scale
        for cx, cy, col in dots:
            draw.ellipse([cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r], fill=col, outline=(0, 0, 0, 60), width=1)

        # Selected row: Apple System Blue pill
        draw.rounded_rectangle(
            [margin + 6 * scale, r1_top, margin + card_w - 6 * scale, r1_bot],
            radius=8 * scale,
            fill=(0, 122, 255, 255),
        )
        # Dividers between rows
        for i in range(1, 5):
            dy = r1_bot + i * 26 * scale
            draw.line([margin + 12 * scale, dy, margin + card_w - 12 * scale, dy], fill=(50, 50, 56, 180), width=1)

    # ─────────────────────────────────────────────────────────────
    # 2. Modern: Cosmic Purple-to-Indigo Gradient + Glow
    # ─────────────────────────────────────────────────────────────
    elif style == "modern":
        r = 16 * scale
        # Ambient violet outer glow
        glow = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
        g_draw = ImageDraw.Draw(glow)
        g_draw.rounded_rectangle(box_rect, radius=r, outline=(138, 43, 226, 170), width=6 * scale)
        glow = glow.filter(ImageFilter.GaussianBlur(5 * scale))
        img = Image.alpha_composite(glow, img)
        draw = ImageDraw.Draw(img)

        # Rich vertical linear gradient
        base = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
        b_draw = ImageDraw.Draw(base)
        for y in range(box_rect[1], box_rect[3]):
            ratio = (y - box_rect[1]) / card_h
            red = int(58 * (1 - ratio) + 16 * ratio)
            green = int(18 * (1 - ratio) + 8 * ratio)
            blue = int(98 * (1 - ratio) + 38 * ratio)
            b_draw.line([(box_rect[0], y), (box_rect[2], y)], fill=(red, green, blue, 250))

        mask = Image.new("L", (sw, sh), 0)
        m_draw = ImageDraw.Draw(mask)
        m_draw.rounded_rectangle(box_rect, radius=r, fill=255)
        img.paste(base, (0, 0), mask)

        # Outer border
        draw.rounded_rectangle(box_rect, radius=r, outline=(168, 85, 247, 220), width=2 * scale)

        # Selected row: Royal amethyst gradient card with subtle glow border
        draw.rounded_rectangle(
            [margin + 6 * scale, r1_top, margin + card_w - 6 * scale, r1_bot],
            radius=9 * scale,
            fill=(138, 43, 226, 240),
            outline=(192, 132, 252, 240),
            width=2,
        )
        for i in range(1, 5):
            dy = r1_bot + i * 26 * scale
            draw.line([margin + 14 * scale, dy, margin + card_w - 14 * scale, dy], fill=(70, 40, 110, 150), width=1)

    # ─────────────────────────────────────────────────────────────
    # 3. Fluent: Windows 11 Mica + Cyan Ice Border + Accent Bar
    # ─────────────────────────────────────────────────────────────
    elif style == "fluent":
        r = 10 * scale
        # Body chassis
        draw.rounded_rectangle(
            box_rect,
            radius=r,
            fill=(30, 32, 36, 250),
            outline=(76, 194, 255, 240),
            width=2 * scale,
        )
        # Windows logo ⊞ mark on top-left
        win_x = margin + 10 * scale
        win_y = margin + 8 * scale
        w_sz = 3 * scale
        for dx, dy in [(0, 0), (w_sz + 2, 0), (0, w_sz + 2), (w_sz + 2, w_sz + 2)]:
            draw.rectangle([win_x + dx, win_y + dy, win_x + dx + w_sz, win_y + dy + w_sz], fill=(96, 205, 255))

        # Selected row
        draw.rounded_rectangle(
            [margin + 5 * scale, r1_top, margin + card_w - 5 * scale, r1_bot],
            radius=6 * scale,
            fill=(44, 48, 56, 255),
        )
        # Prominent vertical cyan accent bar on the left edge
        draw.rounded_rectangle(
            [margin + 5 * scale, r1_top + 3 * scale, margin + 9 * scale, r1_bot - 3 * scale],
            radius=2 * scale,
            fill=(76, 194, 255, 255),
        )
        for i in range(1, 5):
            dy = r1_bot + i * 26 * scale
            draw.line([margin + 8 * scale, dy, margin + card_w - 8 * scale, dy], fill=(50, 54, 62, 220), width=1)

    # ─────────────────────────────────────────────────────────────
    # 4. Compact: Minimal Dark Carbon Chassis
    # ─────────────────────────────────────────────────────────────
    elif style == "compact":
        draw.rectangle(box_rect, fill=(18, 18, 20, 255), outline=(55, 55, 62, 255), width=1 * scale)
        r1_top_c = r1_top - 4 * scale
        r1_bot_c = r1_bot - 4 * scale
        draw.rectangle(
            [margin + 2 * scale, r1_top_c, margin + card_w - 2 * scale, r1_bot_c],
            fill=(36, 36, 42, 255),
        )
        for i in range(1, 5):
            dy = r1_bot_c + i * 25 * scale
            draw.line([margin + 4 * scale, dy, margin + card_w - 4 * scale, dy], fill=(40, 40, 46, 255), width=1)

    # ─────────────────────────────────────────────────────────────
    # 5. Glass: Aero Frosted Glass + Specular Reflection Sheen
    # ─────────────────────────────────────────────────────────────
    elif style == "glass":
        r = 14 * scale
        draw.rounded_rectangle(
            box_rect,
            radius=r,
            fill=(24, 34, 48, 210),
            outline=(138, 180, 216, 230),
            width=2 * scale,
        )
        # Specular reflection sheen (upper half)
        sheen = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(sheen)
        s_draw.polygon(
            [
                (box_rect[0], box_rect[1]),
                (box_rect[2], box_rect[1]),
                (box_rect[2], box_rect[1] + 36 * scale),
                (box_rect[0], box_rect[1] + 72 * scale),
            ],
            fill=(255, 255, 255, 38),
        )
        mask = Image.new("L", (sw, sh), 0)
        m_draw = ImageDraw.Draw(mask)
        m_draw.rounded_rectangle(box_rect, radius=r, fill=255)
        img.paste(sheen, (0, 0), mask)

        # Bright specular top rim highlight line
        draw.line(
            [box_rect[0] + 16 * scale, box_rect[1] + 1 * scale, box_rect[2] - 16 * scale, box_rect[1] + 1 * scale],
            fill=(235, 245, 255, 240),
            width=2 * scale,
        )

        # Selected row: Glassy blue card
        draw.rounded_rectangle(
            [margin + 6 * scale, r1_top, margin + card_w - 6 * scale, r1_bot],
            radius=8 * scale,
            fill=(59, 110, 156, 140),
            outline=(160, 210, 255, 190),
            width=1 * scale,
        )
        for i in range(1, 5):
            dy = r1_bot + i * 26 * scale
            draw.line([margin + 12 * scale, dy, margin + card_w - 12 * scale, dy], fill=(60, 85, 115, 150), width=1)

    # ─────────────────────────────────────────────────────────────
    # 6. Classic: Authentic Win32 Retro Windows 98 Chassis
    # ─────────────────────────────────────────────────────────────
    elif style == "classic":
        # Chassis: Windows 98 battleship grey #D4D0C8
        draw.rectangle(box_rect, fill=(212, 208, 200, 255))
        # 3D raised border: white highlight top/left, dark shadow bottom/right
        bw = 2 * scale
        x0, y0, x1, y1 = box_rect
        draw.line([(x0, y0), (x1, y0)], fill=(255, 255, 255), width=bw)
        draw.line([(x0, y0), (x0, y1)], fill=(255, 255, 255), width=bw)
        draw.line([(x1 - 1, y0), (x1 - 1, y1)], fill=(64, 64, 64), width=bw)
        draw.line([(x0, y1 - 1), (x1, y1 - 1)], fill=(64, 64, 64), width=bw)

        # Solid Win32 Navy title bar at top
        tb_h = 16 * scale
        draw.rectangle([x0 + bw, y0 + bw, x1 - bw, y0 + bw + tb_h], fill=(10, 36, 106))

        # Title bar caption buttons: _ [] X on the right side
        btn_y = y0 + bw + 2 * scale
        btn_w, btn_h = 11 * scale, 12 * scale
        btn_rx = x1 - bw - 4 * scale

        # 'X' close button
        bx = btn_rx - btn_w
        draw.rectangle([bx, btn_y, bx + btn_w, btn_y + btn_h], fill=(212, 208, 200), outline=(255, 255, 255), width=1)
        cx, cy = bx + btn_w // 2, btn_y + btn_h // 2
        draw.line([(cx - 2 * scale, cy - 2 * scale), (cx + 2 * scale, cy + 2 * scale)], fill=(0, 0, 0), width=1)
        draw.line([(cx - 2 * scale, cy + 2 * scale), (cx + 2 * scale, cy - 2 * scale)], fill=(0, 0, 0), width=1)

        # '□' max button
        bx = bx - btn_w - 2 * scale
        draw.rectangle([bx, btn_y, bx + btn_w, btn_y + btn_h], fill=(212, 208, 200), outline=(255, 255, 255), width=1)
        draw.rectangle([bx + 2 * scale, btn_y + 2 * scale, bx + btn_w - 2 * scale, btn_y + btn_h - 2 * scale], outline=(0, 0, 0), width=1)

        # Selected row: Solid Win32 Navy selection
        r1_top_c = y0 + bw + tb_h + 4 * scale
        r1_bot_c = r1_top_c + 24 * scale
        draw.rectangle([x0 + bw + 2 * scale, r1_top_c, x1 - bw - 2 * scale, r1_bot_c], fill=(10, 36, 106))

    # ─────────────────────────────────────────────────────────────
    # 7. Material: Google Material You (M3) + Tonal Pill + Chips
    # ─────────────────────────────────────────────────────────────
    elif style == "material":
        r = 18 * scale
        # Soft elevation shadow
        shadow = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(shadow)
        s_draw.rounded_rectangle(
            [box_rect[0] + 2 * scale, box_rect[1] + 5 * scale, box_rect[2] + 2 * scale, box_rect[3] + 5 * scale],
            radius=r,
            fill=(0, 0, 0, 110),
        )
        shadow = shadow.filter(ImageFilter.GaussianBlur(5 * scale))
        img = Image.alpha_composite(shadow, img)
        draw = ImageDraw.Draw(img)

        # Material 3 surface
        draw.rounded_rectangle(box_rect, radius=r, fill=(34, 32, 40, 245), outline=(75, 70, 85, 220), width=2 * scale)

        # Selected row: Full rounded tonal pill
        draw.rounded_rectangle(
            [margin + 6 * scale, r1_top, margin + card_w - 6 * scale, r1_bot],
            radius=14 * scale,
            fill=(62, 56, 76, 255),
        )
        # Filled circular badge chips (chip for row 1 and rows 2-5)
        cx = margin + 18 * scale
        cr = 7 * scale
        c1_cy = r1_top + 14 * scale
        draw.ellipse([cx - cr, c1_cy - cr, cx + cr, c1_cy + cr], fill=(0, 122, 255, 255))
        for i in range(1, 5):
            cy_i = r1_bot + i * 26 * scale - 12 * scale
            draw.ellipse([cx - cr, cy_i - cr, cx + cr, cy_i + cr], fill=(55, 52, 65, 255))

    # ─────────────────────────────────────────────────────────────
    # 8. iOS: Apple iOS Smooth Squircle + System Blue Pill
    # ─────────────────────────────────────────────────────────────
    elif style == "ios":
        r = 16 * scale
        draw.rounded_rectangle(
            box_rect,
            radius=r,
            fill=(28, 28, 30, 245),
            outline=(65, 65, 72, 220),
            width=2 * scale,
        )
        # Selected row: Apple System Blue rounded pill
        draw.rounded_rectangle(
            [margin + 6 * scale, r1_top, margin + card_w - 6 * scale, r1_bot],
            radius=12 * scale,
            fill=(0, 122, 255, 255),
        )
        for i in range(1, 5):
            dy = r1_bot + i * 26 * scale
            draw.line([margin + 12 * scale, dy, margin + card_w - 12 * scale, dy], fill=(45, 45, 48, 200), width=1)

    # ─────────────────────────────────────────────────────────────
    # 9. Minimal: Code Terminal + Keycap Badges
    # ─────────────────────────────────────────────────────────────
    elif style == "minimal":
        draw.rectangle(box_rect, fill=(16, 16, 18, 255), outline=(50, 50, 56, 255), width=2 * scale)
        r1_top_m = r1_top - 2 * scale
        r1_bot_m = r1_bot - 2 * scale
        draw.rectangle([margin + 4 * scale, r1_top_m, margin + card_w - 4 * scale, r1_bot_m], fill=(30, 30, 36, 255))
        # Keycap boxes [1] .. [5]
        kc_x = margin + 10 * scale
        for i in range(5):
            kc_y = r1_top_m + i * 26 * scale + 4 * scale
            bg_col = (48, 48, 56) if i == 0 else (26, 26, 30)
            draw.rectangle([kc_x, kc_y, kc_x + 14 * scale, kc_y + 16 * scale], fill=bg_col, outline=(70, 70, 80), width=1)

    # ─────────────────────────────────────────────────────────────
    # 10. Neon: Cyberpunk Hot Magenta Glow + Electric Green
    # ─────────────────────────────────────────────────────────────
    elif style == "neon":
        r = 14 * scale
        # Glowing magenta bloom
        glow = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
        g_draw = ImageDraw.Draw(glow)
        g_draw.rounded_rectangle(box_rect, radius=r, outline=(255, 0, 127, 210), width=6 * scale)
        glow = glow.filter(ImageFilter.GaussianBlur(5 * scale))
        img = Image.alpha_composite(glow, img)
        draw = ImageDraw.Draw(img)

        # Deep black/purple chassis
        draw.rounded_rectangle(
            box_rect,
            radius=r,
            fill=(12, 4, 18, 255),
            outline=(255, 0, 127, 255),
            width=3 * scale,
        )
        # Selected row: Dark magenta card with neon outline
        draw.rounded_rectangle(
            [margin + 6 * scale, r1_top, margin + card_w - 6 * scale, r1_bot],
            radius=8 * scale,
            fill=(46, 6, 36, 255),
            outline=(255, 0, 127, 230),
            width=2 * scale,
        )
        for i in range(1, 5):
            dy = r1_bot + i * 26 * scale
            draw.line([margin + 10 * scale, dy, margin + card_w - 10 * scale, dy], fill=(40, 10, 32, 200), width=1)

    # LANCZOS antialiased downsampling to target size
    return img.resize((width, height), Image.Resampling.LANCZOS)
