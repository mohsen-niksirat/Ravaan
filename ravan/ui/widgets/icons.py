"""2x DPI-supersampled anti-aliased vector icons drawn with Pillow."""

from __future__ import annotations

import math
import tkinter as tk
import weakref
from functools import lru_cache

from PIL import Image, ImageDraw, ImageTk

# Map legacy emoji strings or aliases to canonical vector icon names
ICON_ALIASES: dict[str, str] = {
    "⚙️": "settings",
    "⚙": "settings",
    "general": "settings",
    "⚡": "bolt",
    "autofix": "bolt",
    "🔮": "sparkle",
    "✨": "sparkle",
    "prediction": "sparkle",
    "⌨️": "keyboard",
    "⌨": "keyboard",
    "hotkeys": "keyboard",
    "🚫": "shield",
    "exclusions": "shield",
    "🎯": "sliders",
    "profiles": "sliders",
    "📝": "code",
    "snippets": "code",
    "☁️": "cloud",
    "☁": "cloud",
    "sync": "cloud",
    "ℹ️": "info",
    "ℹ": "info",
    "about": "info",
    "🪶": "feather",
    "brand": "feather",
    "🔍": "search",
    "📦": "hub",
    "package": "hub",
    "🎤": "mic",
    "🎙️": "mic",
    "🔄": "replace",
    "↺": "reset",
    "📋": "copy",
    "✔": "check",
    "✓": "check",
    "✕": "close",
    "🔑": "key",
    "🎨": "palette",
    "🧠": "brain",
    "🚀": "rocket",
    "✍️": "pen",
    "📚": "book",
}


def resolve_icon_name(name_or_emoji: str) -> str:
    """Resolve an icon name or legacy emoji glyph to a canonical vector icon identifier."""
    clean = (name_or_emoji or "").strip()
    return ICON_ALIASES.get(clean, clean.lower() if clean else "sparkle")


def _parse_rgba(hex_color: str, alpha: int = 255) -> tuple[int, int, int, int]:
    try:
        h = hex_color.strip().lstrip("#")
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        rgb = int(h[:6], 16)
        return ((rgb >> 16) & 0xFF, (rgb >> 8) & 0xFF, rgb & 0xFF, alpha)
    except Exception:
        return (138, 180, 248, alpha)


@lru_cache(maxsize=512)
def render_icon_image(
    name: str,
    size: int = 16,
    color: str = "#8ab4f8",
    dpi: float = 1.0,
) -> Image.Image:
    """Render a crisp 2x-supersampled RGBA Pillow icon downsampled with LANCZOS."""
    canon = resolve_icon_name(name)
    target_px = max(12, int(round(size * max(1.0, dpi))))
    ss = target_px * 2  # 2x supersampling canvas
    img = Image.new("RGBA", (ss, ss), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    col = _parse_rgba(color, 255)
    col_soft = _parse_rgba(color, 150)
    lw = max(2, int(round(ss * 0.095)))

    cx, cy = ss / 2.0, ss / 2.0
    m = ss * 0.14  # outer margin

    if canon == "sparkle":
        # 4-point curved star + small top-right accent star
        def _star_pts(sx: float, sy: float, r_out: float, r_in: float) -> list[tuple[float, float]]:
            pts: list[tuple[float, float]] = []
            for i in range(8):
                ang = i * (math.pi / 4.0) - (math.pi / 2.0)
                r = r_out if i % 2 == 0 else r_in
                pts.append((sx + math.cos(ang) * r, sy + math.sin(ang) * r))
            return pts

        draw.polygon(_star_pts(cx - ss * 0.04, cy + ss * 0.04, ss * 0.34, ss * 0.11), fill=col)
        draw.polygon(_star_pts(cx + ss * 0.24, cy - ss * 0.24, ss * 0.14, ss * 0.05), fill=col_soft)

    elif canon == "mic":
        # Capsule head + U-holder + stem
        cap_w = ss * 0.26
        draw.rounded_rectangle(
            [cx - cap_w / 2, m, cx + cap_w / 2, cy + ss * 0.06],
            radius=cap_w / 2,
            outline=col,
            width=lw,
        )
        arc_r = ss * 0.25
        draw.arc(
            [cx - arc_r, cy - arc_r * 0.7, cx + arc_r, cy + arc_r * 0.9],
            start=0,
            end=180,
            fill=col,
            width=lw,
        )
        draw.line([(cx, cy + arc_r * 0.9), (cx, ss - m)], fill=col, width=lw)
        draw.line([(cx - ss * 0.16, ss - m), (cx + ss * 0.16, ss - m)], fill=col, width=lw)

    elif canon == "waveform":
        # 5 vertical acoustic bars
        heights = [0.28, 0.56, 0.78, 0.48, 0.30]
        spacing = (ss - 2 * m) / 4.0
        for idx, h_ratio in enumerate(heights):
            bx = m + idx * spacing
            bh = (ss * h_ratio) / 2.0
            draw.line([(bx, cy - bh), (bx, cy + bh)], fill=col, width=max(2, lw))

    elif canon == "hub":
        # Isometric hexagon package cube
        r = ss * 0.36
        pts = [
            (cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a)))
            for a in (-90, -30, 30, 90, 150, 210)
        ]
        draw.polygon(pts, outline=col, width=lw)
        draw.line([pts[5], (cx, cy), pts[1]], fill=col, width=lw)
        draw.line([(cx, cy), pts[3]], fill=col, width=lw)

    elif canon == "check":
        p1 = (ss * 0.20, cy + ss * 0.02)
        p2 = (ss * 0.42, ss * 0.72)
        p3 = (ss * 0.80, ss * 0.26)
        draw.line([p1, p2, p3], fill=col, width=max(3, lw + 1), joint="curve")

    elif canon == "copy":
        draw.rounded_rectangle(
            [ss * 0.30, ss * 0.30, ss * 0.82, ss * 0.84],
            radius=ss * 0.08,
            outline=col,
            width=lw,
        )
        draw.arc(
            [ss * 0.16, ss * 0.16, ss * 0.66, ss * 0.68],
            start=180,
            end=270,
            fill=col_soft,
            width=lw,
        )
        draw.line([(ss * 0.16, ss * 0.26), (ss * 0.16, ss * 0.62)], fill=col_soft, width=lw)
        draw.line([(ss * 0.26, ss * 0.16), (ss * 0.62, ss * 0.16)], fill=col_soft, width=lw)

    elif canon in ("replace", "reset"):
        r = ss * 0.32
        draw.arc([cx - r, cy - r, cx + r, cy + r], start=35, end=315, fill=col, width=lw)
        ax = cx + r * math.cos(math.radians(315))
        ay = cy + r * math.sin(math.radians(315))
        draw.polygon(
            [(ax, ay - ss * 0.10), (ax + ss * 0.12, ay + ss * 0.04), (ax - ss * 0.06, ay + ss * 0.08)],
            fill=col,
        )

    elif canon == "search":
        r = ss * 0.24
        scx, scy = cx - ss * 0.06, cy - ss * 0.06
        draw.ellipse([scx - r, scy - r, scx + r, scy + r], outline=col, width=lw)
        draw.line(
            [(scx + r * 0.72, scy + r * 0.72), (ss - m, ss - m)],
            fill=col,
            width=max(3, lw + 1),
        )

    elif canon == "close":
        d = ss * 0.24
        draw.line([(cx - d, cy - d), (cx + d, cy + d)], fill=col, width=lw)
        draw.line([(cx + d, cy - d), (cx - d, cy + d)], fill=col, width=lw)

    elif canon in ("eye", "eye_off"):
        draw.arc([m, cy - ss * 0.22, ss - m, cy + ss * 0.22], start=190, end=350, fill=col, width=lw)
        draw.arc([m, cy - ss * 0.22, ss - m, cy + ss * 0.22], start=10, end=170, fill=col, width=lw)
        pr = ss * 0.09
        draw.ellipse([cx - pr, cy - pr, cx + pr, cy + pr], fill=col)
        if canon == "eye_off":
            draw.line([(m + 2, ss - m - 2), (ss - m - 2, m + 2)], fill=col, width=lw)

    elif canon == "key":
        r = ss * 0.16
        kcx = m + r + ss * 0.04
        draw.ellipse([kcx - r, cy - r, kcx + r, cy + r], outline=col, width=lw)
        draw.line([(kcx + r, cy), (ss - m, cy)], fill=col, width=lw)
        draw.line([(ss - m - ss * 0.12, cy), (ss - m - ss * 0.12, cy + ss * 0.14)], fill=col, width=lw)
        draw.line([(ss - m, cy), (ss - m, cy + ss * 0.14)], fill=col, width=lw)

    elif canon == "settings":
        r_outer = ss * 0.34
        r_inner = ss * 0.13
        for i in range(8):
            ang = math.radians(i * 45)
            x1 = cx + math.cos(ang) * (r_outer * 0.68)
            y1 = cy + math.sin(ang) * (r_outer * 0.68)
            x2 = cx + math.cos(ang) * r_outer
            y2 = cy + math.sin(ang) * r_outer
            draw.line([(x1, y1), (x2, y2)], fill=col, width=max(3, lw + 1))
        r_mid = r_outer * 0.72
        draw.ellipse([cx - r_mid, cy - r_mid, cx + r_mid, cy + r_mid], outline=col, width=lw)
        draw.ellipse([cx - r_inner, cy - r_inner, cx + r_inner, cy + r_inner], fill=col_soft)

    elif canon == "bolt":
        pts = [
            (cx + ss * 0.06, m),
            (cx - ss * 0.22, cy + ss * 0.04),
            (cx + ss * 0.02, cy + ss * 0.04),
            (cx - ss * 0.08, ss - m),
            (cx + ss * 0.24, cy - ss * 0.04),
            (cx, cy - ss * 0.04),
        ]
        draw.polygon(pts, fill=col)

    elif canon == "keyboard":
        draw.rounded_rectangle(
            [m, cy - ss * 0.24, ss - m, cy + ss * 0.26],
            radius=ss * 0.08,
            outline=col,
            width=lw,
        )
        for rx in (0.28, 0.43, 0.57, 0.72):
            for ry in (cy - ss * 0.10, cy + ss * 0.02):
                draw.ellipse([ss * rx - 2, ry - 2, ss * rx + 2, ry + 2], fill=col)
        draw.line([(ss * 0.32, cy + ss * 0.14), (ss * 0.68, cy + ss * 0.14)], fill=col, width=lw)

    elif canon == "shield":
        r = ss * 0.34
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=col, width=lw)
        d = r * 0.68
        draw.line([(cx - d, cy - d), (cx + d, cy + d)], fill=col, width=lw)

    elif canon == "sliders":
        for idx, (y_off, kx) in enumerate(((-0.22, 0.35), (0.0, 0.66), (0.22, 0.45))):
            y = cy + ss * y_off
            draw.line([(m, y), (ss - m, y)], fill=col_soft if idx == 1 else col, width=lw)
            kr = ss * 0.075
            kx_px = ss * kx
            draw.ellipse([kx_px - kr, y - kr, kx_px + kr, y + kr], fill=col)

    elif canon == "code":
        # `< / >` brackets
        y_top, y_bot = cy - ss * 0.20, cy + ss * 0.20
        draw.line([(ss * 0.34, y_top), (ss * 0.16, cy), (ss * 0.34, y_bot)], fill=col, width=lw)
        draw.line([(ss * 0.66, y_top), (ss * 0.84, cy), (ss * 0.66, y_bot)], fill=col, width=lw)
        draw.line([(ss * 0.55, y_top - 2), (ss * 0.45, y_bot + 2)], fill=col_soft, width=lw)

    elif canon == "cloud":
        draw.rounded_rectangle(
            [m + ss * 0.04, cy - ss * 0.02, ss - m - ss * 0.04, cy + ss * 0.24],
            radius=ss * 0.12,
            fill=col,
        )
        draw.ellipse([ss * 0.26, cy - ss * 0.22, ss * 0.62, cy + ss * 0.14], fill=col)
        draw.ellipse([ss * 0.48, cy - ss * 0.16, ss * 0.76, cy + ss * 0.14], fill=col)

    elif canon == "info":
        r = ss * 0.35
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=col, width=lw)
        draw.line([(cx, cy - ss * 0.04), (cx, cy + ss * 0.18)], fill=col, width=lw)
        dr = max(2.0, lw * 0.65)
        draw.ellipse([cx - dr, cy - ss * 0.18 - dr, cx + dr, cy - ss * 0.18 + dr], fill=col)

    elif canon in ("feather", "pen"):
        pts = [
            (ss - m, m),
            (cx + ss * 0.22, cy + ss * 0.08),
            (cx - ss * 0.12, ss - m - ss * 0.06),
            (m + ss * 0.04, ss - m),
            (m + ss * 0.10, cx + ss * 0.12),
            (cy - ss * 0.08, cx - ss * 0.22),
        ]
        draw.polygon(pts, fill=col_soft, outline=col)
        draw.line([(m, ss - m), (ss - m - ss * 0.08, m + ss * 0.08)], fill=col, width=lw)

    elif canon == "palette":
        # Artist palette oval with thumb notch and color dots
        r = ss * 0.40
        draw.ellipse([cx - r, cy - r * 0.90, cx + r, cy + r * 0.90], fill=col_soft, outline=col, width=lw)
        dot_r = max(1.8, ss * 0.07)
        for dx, dy in [(-0.18, -0.10), (0.0, -0.20), (0.18, -0.10), (0.20, 0.10)]:
            px, py = cx + ss * dx, cy + ss * dy
            draw.ellipse([px - dot_r, py - dot_r, px + dot_r, py + dot_r], fill=col)
        hole_r = max(2.0, ss * 0.09)
        hx, hy = cx - ss * 0.14, cy + ss * 0.14
        draw.ellipse([hx - hole_r, hy - hole_r, hx + hole_r, hy + hole_r], fill=(0, 0, 0, 0), outline=col, width=max(1, lw - 1))

    elif canon == "brain":
        # Stylized neural brain halves with nodes
        lw_thin = max(1, lw - 1)
        draw.arc([cx - ss * 0.36, cy - ss * 0.32, cx + ss * 0.02, cy + ss * 0.32], 90, 270, fill=col, width=lw)
        draw.arc([cx - ss * 0.02, cy - ss * 0.32, cx + ss * 0.36, cy + ss * 0.32], 270, 90, fill=col, width=lw)
        draw.line([(cx, cy - ss * 0.28), (cx, cy + ss * 0.28)], fill=col, width=lw_thin)
        node_r = max(1.6, ss * 0.065)
        for nx, ny in [(-0.18, -0.10), (0.18, -0.10), (-0.16, 0.12), (0.16, 0.12)]:
            draw.ellipse([cx + ss * nx - node_r, cy + ss * ny - node_r, cx + ss * nx + node_r, cy + ss * ny + node_r], fill=col)

    elif canon == "rocket":
        # Angled minimal rocket body + flame
        body = [
            (ss - m, m),
            (cx + ss * 0.20, cy - ss * 0.02),
            (cx - ss * 0.06, cy + ss * 0.24),
            (cx - ss * 0.24, cy + ss * 0.06),
            (cx + ss * 0.02, cy - ss * 0.20),
        ]
        draw.polygon(body, fill=col_soft, outline=col)
        draw.line([(m + ss * 0.04, ss - m - ss * 0.04), (cx - ss * 0.16, cy + ss * 0.16)], fill=col, width=lw)
        pr = max(1.6, ss * 0.065)
        px, py = cx + ss * 0.08, cy - ss * 0.08
        draw.ellipse([px - pr, py - pr, px + pr, py + pr], fill=col)

    elif canon == "book":
        # Open book pages
        draw.polygon([(cx, cy - ss * 0.22), (cx - ss * 0.38, cy - ss * 0.30), (cx - ss * 0.38, cy + ss * 0.24), (cx, cy + ss * 0.32)], fill=col_soft, outline=col)
        draw.polygon([(cx, cy - ss * 0.22), (cx + ss * 0.38, cy - ss * 0.30), (cx + ss * 0.38, cy + ss * 0.24), (cx, cy + ss * 0.32)], fill=col_soft, outline=col)
        draw.line([(cx, cy - ss * 0.22), (cx, cy + ss * 0.32)], fill=col, width=lw)

    else:
        # Default geometric diamond/circle badge
        r = ss * 0.32
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=col, width=lw)
        ir = ss * 0.12
        draw.ellipse([cx - ir, cy - ir, cx + ir, cy + ir], fill=col)

    return img.resize((target_px, target_px), Image.Resampling.LANCZOS)


_PHOTO_CACHE: dict[tuple[int, str, int, str, float], ImageTk.PhotoImage] = {}
_HOOKED_ROOTS: dict[int, weakref.ref[tk.Misc]] = {}


def _interp_key(master: tk.Misc) -> int:
    return int(master.tk.interpaddr()) if hasattr(master, "tk") else id(master)


def clear_icon_cache(master: tk.Misc | None = None, *, tk_key: int | None = None) -> None:
    """Evict cached PhotoImages for a destroyed Tk interpreter, or clear all entries."""
    if tk_key is None and master is not None:
        try:
            tk_key = _interp_key(master)
        except Exception:
            tk_key = id(master)
    if tk_key is None:
        _PHOTO_CACHE.clear()
        _HOOKED_ROOTS.clear()
        return
    for key in [k for k in _PHOTO_CACHE if k[0] == tk_key]:
        _PHOTO_CACHE.pop(key, None)
    _HOOKED_ROOTS.pop(tk_key, None)


def _bind_root_eviction(root: tk.Misc, tk_key: int) -> None:
    if tk_key in _HOOKED_ROOTS:
        return
    try:
        owner = root._root() if hasattr(root, "_root") else root.winfo_toplevel()  # type: ignore[attr-defined]
    except Exception:
        owner = root
    try:
        ref = weakref.ref(owner, lambda _r, k=tk_key: clear_icon_cache(tk_key=k))
        _HOOKED_ROOTS[tk_key] = ref
        owner.bind(
            "<Destroy>",
            lambda ev, r=ref, k=tk_key: clear_icon_cache(tk_key=k) if getattr(ev, "widget", None) is r() else None,
            add="+",
        )
    except Exception:
        pass


def get_icon(
    name: str, size: int = 16, color: str = "#8ab4f8", dpi: float = 1.0, master: tk.Misc | None = None,
) -> ImageTk.PhotoImage | None:
    """Return a cached `ImageTk.PhotoImage` for the requested vector icon."""
    root = master or getattr(tk, "_default_root", None)
    if root is None:
        return None
    try:
        if not root.winfo_exists():
            return None
        tk_key = _interp_key(root)
    except Exception:
        return None
    _bind_root_eviction(root, tk_key)
    dpi_r = round(max(1.0, float(dpi)), 2)
    cache_key = (tk_key, resolve_icon_name(name), int(size), color.lower(), dpi_r)
    if (cached := _PHOTO_CACHE.get(cache_key)) is not None:
        return cached
    try:
        photo = ImageTk.PhotoImage(render_icon_image(cache_key[1], size=size, color=color, dpi=dpi_r), master=root)
        if len(_PHOTO_CACHE) > 256:
            _PHOTO_CACHE.clear()
        _PHOTO_CACHE[cache_key] = photo
        return photo
    except Exception:
        return None
