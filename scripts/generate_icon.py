"""Generate modern multi-resolution application icon for Ravaan."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


def create_master_icon(size: int = 1024) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    pad = size * 0.08
    r = size * 0.22

    # 1. Subtle drop shadow
    shadow_mask = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow_mask)
    sdraw.rounded_rectangle(
        [pad, pad + size * 0.035, size - pad, size - pad + size * 0.035],
        radius=r,
        fill=(15, 23, 42, 110),
    )
    shadow_blurred = shadow_mask.filter(ImageFilter.GaussianBlur(size * 0.04))
    img.paste(shadow_blurred, (0, 0), shadow_blurred)

    # 2. Rich vibrant vertical gradient
    grad = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(grad)
    for y in range(size):
        ratio = y / size
        if ratio < 0.5:
            t = ratio * 2
            red = int(29 * (1 - t) + 37 * t)
            green = int(78 * (1 - t) + 99 * t)
            blue = int(216 * (1 - t) + 235 * t)
        else:
            t = (ratio - 0.5) * 2
            red = int(37 * (1 - t) + 14 * t)
            green = int(99 * (1 - t) + 165 * t)
            blue = int(235 * (1 - t) + 233 * t)
        gdraw.line([(0, y), (size, y)], fill=(red, green, blue, 255))

    mask = Image.new("L", (size, size), 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.rounded_rectangle([pad, pad, size - pad, size - pad], radius=r, fill=255)

    card = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    card.paste(grad, (0, 0), mask)

    # 3. Inner glass edge highlight (Fluent design acrylic rim)
    hdraw = ImageDraw.Draw(card)
    hdraw.rounded_rectangle(
        [pad + 2, pad + 2, size - pad - 2, size - pad - 2],
        radius=r - 1,
        outline=(255, 255, 255, 80),
        width=max(2, int(size * 0.007)),
    )

    # 4. Stylized Persian letter «ر»
    font_size = int(size * 0.48)
    font = None
    for fn in [
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/tahomabd.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ]:
        if Path(fn).is_file():
            try:
                font = ImageFont.truetype(fn, font_size)
                break
            except Exception:
                pass
    if font is None:
        font = ImageFont.load_default()

    # Soft glowing backdrop
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    text_pos = (size * 0.52, size * 0.44)
    glow_draw.text(text_pos, "ر", fill=(56, 189, 248, 160), font=font, anchor="mm")
    glow = glow.filter(ImageFilter.GaussianBlur(size * 0.025))
    card.paste(glow, (0, 0), glow)

    # Crisp white text
    cdraw = ImageDraw.Draw(card)
    cdraw.text(text_pos, "ر", fill=(255, 255, 255, 255), font=font, anchor="mm")

    # 5. Sleek glowing typing caret beam
    cx = size * 0.35
    cy_top = size * 0.28
    cy_bot = size * 0.48
    cw = max(3, int(size * 0.024))
    caret_glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    cg_draw = ImageDraw.Draw(caret_glow)
    cg_draw.rounded_rectangle(
        [cx - cw, cy_top - cw * 0.5, cx + cw, cy_bot + cw * 0.5],
        radius=cw,
        fill=(56, 189, 248, 180),
    )
    caret_glow = caret_glow.filter(ImageFilter.GaussianBlur(size * 0.015))
    card.paste(caret_glow, (0, 0), caret_glow)

    cdraw = ImageDraw.Draw(card)
    cdraw.rounded_rectangle(
        [cx - cw / 2, cy_top, cx + cw / 2, cy_bot],
        radius=cw / 2,
        fill=(255, 255, 255, 255),
    )

    # 6. Dynamic sparkle/spark dot (autocomplete spark)
    sp_x, sp_y = size * 0.70, size * 0.28
    sp_r = size * 0.028
    cdraw.ellipse(
        [sp_x - sp_r, sp_y - sp_r, sp_x + sp_r, sp_y + sp_r],
        fill=(56, 189, 248, 255),
    )
    cdraw.ellipse(
        [sp_x - sp_r * 0.5, sp_y - sp_r * 0.5, sp_x + sp_r * 0.5, sp_y + sp_r * 0.5],
        fill=(255, 255, 255, 255),
    )

    img.paste(card, (0, 0), card)
    return img


def generate_ico(output_path: Path) -> None:
    master = create_master_icon(1024)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    master.save(
        output_path,
        format="ICO",
        sizes=[
            (256, 256),
            (128, 128),
            (64, 64),
            (48, 48),
            (32, 32),
            (16, 16),
        ],
    )
    print(f"Generated multi-resolution ICO at: {output_path}")


if __name__ == "__main__":
    target = Path(__file__).resolve().parent.parent / "ravan" / "data" / "icon.ico"
    generate_ico(target)
