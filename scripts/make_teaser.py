#!/usr/bin/env python3
"""
Ravaan 30-Second Commercial Teaser Video Generator (V2 - Pro Persian Edition)
Features:
  - 100% Crisp Persian Typography using Vazirmatn (Zero tofu boxes or missing glyphs)
  - Studio-quality Persian Neural Voiceover (گوینده اختصاصی با edge-tts)
  - Calming, pleasant background ambient music (موسیقی آرامش‌بخش پس‌زمینه)
  - Hand-crafted vector iconography (No font emoji square issues)
  - Generates three 10-second Full HD (1080p, 30fps) clips and concatenates into 30s master teaser.
"""

import os
import sys

# Ensure UTF-8 output encoding on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import math
import asyncio
import subprocess
import numpy as np
from scipy.io import wavfile
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display
import edge_tts

WIDTH = 1920
HEIGHT = 1080
FPS = 30
SAMPLE_RATE = 44100

# High-fidelity Vazirmatn fonts (Standard Persian fonts with full ligature support)
FONT_BOLD = "Vazirmatn-Bold.ttf"
FONT_MEDIUM = "Vazirmatn-Medium.ttf"
FONT_REGULAR = "Vazirmatn-Regular.ttf"
FONT_SEGOE = r"C:\Windows\Fonts\segoeui.ttf"
FONT_SEGOE_BOLD = r"C:\Windows\Fonts\segoeuib.ttf"

OUT_DIR = os.path.abspath("media/teaser")
os.makedirs(OUT_DIR, exist_ok=True)

def reshape_fa(text):
    """Reshape and reorder Persian/Arabic text for correct RTL rendering without glyph loss."""
    if not text:
        return ""
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)

def get_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        # Fallback to Windows default
        return ImageFont.truetype(r"C:\Windows\Fonts\tahoma.ttf", size)

def ease_out_quad(t):
    return 1 - (1 - t) * (1 - t)

def ease_in_out_quad(t):
    return 2 * t * t if t < 0.5 else 1 - math.pow(-2 * t + 2, 2) / 2

def ease_out_back(t):
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * math.pow(t - 1, 3) + c1 * math.pow(t - 1, 2)

# Load real application assets
POPUP_IMG_PATH = "media_popup.png" if os.path.exists("media_popup.png") else os.path.join(OUT_DIR, "media_popup.png")
TRAY_IMG_PATH = "media_tray.png" if os.path.exists("media_tray.png") else os.path.join(OUT_DIR, "media_tray.png")
ICON_IMG_PATH = "ravan/data/icon.ico"

# Cache user uploaded assets if available
U1 = r"C:/Users/MOHSEN/.gemini/antigravity/brain/df837e01-188c-455c-a3b4-a8483b359500/.user_uploaded/media_1793209841311_f7da81bc.png"
U2 = r"C:/Users/MOHSEN/.gemini/antigravity/brain/df837e01-188c-455c-a3b4-a8483b359500/.user_uploaded/media_1793209827285_25250c32.png"

POPUP_IMG = Image.open(U1).convert("RGBA") if os.path.exists(U1) else None
TRAY_IMG = Image.open(U2).convert("RGBA") if os.path.exists(U2) else None
ICON_IMG = Image.open(ICON_IMG_PATH).convert("RGBA") if os.path.exists(ICON_IMG_PATH) else None

def create_base_canvas(t, clip_idx):
    """Creates a base background image with soft soothing ambient glow and animated particles."""
    canvas = Image.new("RGBA", (WIDTH, HEIGHT), (12, 17, 28, 255))
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    
    if clip_idx == 1:
        pulse = 0.5 + 0.5 * math.sin(t * 2.0)
        ov_draw.ellipse([WIDTH*0.6, HEIGHT*0.2, WIDTH*1.2, HEIGHT*0.9], fill=(120, 25, 45, int(30 + 15*pulse)))
        ov_draw.ellipse([-WIDTH*0.2, HEIGHT*0.3, WIDTH*0.4, HEIGHT*1.1], fill=(20, 35, 75, 40))
    elif clip_idx == 2:
        shift = math.sin(t * 1.2) * 40
        ov_draw.ellipse([WIDTH*0.5 + shift, -100, WIDTH*1.1 + shift, 600], fill=(14, 116, 220, 45))
        ov_draw.ellipse([-100, HEIGHT*0.5, 700, HEIGHT*1.2], fill=(6, 182, 212, 40))
    else:
        ov_draw.ellipse([WIDTH*0.4, -200, WIDTH*1.2, 700], fill=(16, 185, 129, 40))
        ov_draw.ellipse([-100, HEIGHT*0.4, 800, HEIGHT*1.2], fill=(99, 102, 241, 35))
        
    np.random.seed(42)
    num_particles = 30
    for i in range(num_particles):
        base_x = (i * 137.5) % WIDTH
        base_y = (i * 73.1) % HEIGHT
        speed = 12 + (i % 4) * 6
        y = (base_y - t * speed) % HEIGHT
        x = (base_x + math.sin(t + i) * 15) % WIDTH
        size = 2 + (i % 3)
        alpha = int(35 + 25 * math.sin(t * 1.8 + i))
        color = (180, 220, 255, alpha) if clip_idx != 3 else (160, 255, 200, alpha)
        ov_draw.ellipse([x, y, x + size, y + size], fill=color)
        
    for gy in range(HEIGHT - 120, HEIGHT, 25):
        alpha = int(12 * (gy - (HEIGHT - 120)) / 120)
        ov_draw.line([(0, gy), (WIDTH, gy)], fill=(100, 150, 220, alpha), width=1)
        
    canvas = Image.alpha_composite(canvas, overlay)
    return canvas

def draw_glass_card(draw, box, fill=(20, 26, 42, 220), border_color=(255, 255, 255, 40), radius=20, border_width=2):
    x1, y1, x2, y2 = box
    draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=fill, outline=border_color, width=border_width)

def draw_top_bar(canvas, title_text, category_badge=None, badge_color=(6, 182, 212)):
    draw = ImageDraw.Draw(canvas)
    if ICON_IMG:
        ico_small = ICON_IMG.resize((48, 48), Image.Resampling.LANCZOS)
        canvas.paste(ico_small, (WIDTH - 120, 40), ico_small)
        
    font_brand = get_font(FONT_BOLD, 30)
    b_text = reshape_fa("روان | Ravaan")
    draw.text((WIDTH - 135, 45), b_text, font=font_brand, fill=(240, 245, 255), anchor="ra")
    
    if category_badge:
        font_badge = get_font(FONT_MEDIUM, 22)
        badge_shaped = reshape_fa(category_badge)
        bbox = font_badge.getbbox(badge_shaped)
        bw = bbox[2] - bbox[0] + 40
        bh = 40
        draw.rounded_rectangle([80, 42, 80 + bw, 42 + bh], radius=20, fill=(*badge_color, 45), outline=(*badge_color, 160), width=1)
        draw.text((80 + bw // 2, 42 + bh // 2), badge_shaped, font=font_badge, fill=(255, 255, 255), anchor="mm")

def draw_vector_warning_badge(draw, cx, cy, size=24):
    """Draws a crisp vector warning triangle."""
    pts = [(cx, cy - size), (cx - size, cy + size - 4), (cx + size, cy + size - 4)]
    draw.polygon(pts, fill=(239, 68, 68, 255))
    font_ex = get_font(FONT_BOLD, int(size * 1.1))
    draw.text((cx, cy + 2), "!", font=font_ex, fill=(255, 255, 255), anchor="mm")

def draw_vector_lock(draw, cx, cy, color=(52, 211, 153, 255), size=1.0):
    """Draws a crisp vector security padlock."""
    # Shackle
    w = int(22 * size)
    h = int(24 * size)
    draw.arc([cx - w, cy - int(44 * size), cx + w, cy - int(4 * size)], start=180, end=0, fill=color, width=max(4, int(7 * size)))
    # Body
    bw = int(34 * size)
    bh = int(26 * size)
    draw.rounded_rectangle([cx - bw, cy - int(12 * size), cx + bw, cy + int(38 * size)], radius=int(8 * size), fill=color)
    # Keyhole
    draw.ellipse([cx - int(6 * size), cy + int(4 * size), cx + int(6 * size), cy + int(16 * size)], fill=(12, 32, 28, 255))
    draw.polygon([(cx - int(4*size), cy + int(10*size)), (cx + int(4*size), cy + int(10*size)), 
                  (cx + int(5*size), cy + int(26*size)), (cx - int(5*size), cy + int(26*size))], fill=(12, 32, 28, 255))

# ==============================================================================
# CLIP 1: THE PROBLEM (0 - 10s)
# ==============================================================================
def render_frame_clip1(t):
    canvas = create_base_canvas(t, 1)
    draw = ImageDraw.Draw(canvas)
    draw_top_bar(canvas, "روان", "بخش اول: چالش‌های تایپ فارسی در ویندوز", badge_color=(239, 68, 68))
    
    if t < 3.2:
        # Scene 1.1: Hook Question
        p = min(1.0, t / 0.8)
        alpha = int(255 * ease_out_quad(p))
        y_offset = int((1.0 - ease_out_quad(p)) * 30)
        
        font_q1 = get_font(FONT_BOLD, 52)
        font_q2 = get_font(FONT_REGULAR, 36)
        
        q1 = reshape_fa("چند بار تا حالا برات پیش اومده؟")
        q2 = reshape_fa("موقع چت، کار یا نگارش متن‌های مهم در ویندوز...")
        
        draw.text((WIDTH // 2, 390 + y_offset), q1, font=font_q1, fill=(255, 255, 255, alpha), anchor="mm")
        draw.text((WIDTH // 2, 480 + y_offset), q2, font=font_q2, fill=(203, 213, 225, alpha), anchor="mm")
        
        draw.ellipse([WIDTH//2 - 40, 250 + y_offset, WIDTH//2 + 40, 330 + y_offset], fill=(239, 68, 68, 30), outline=(239, 68, 68, 180), width=2)
        draw_vector_warning_badge(draw, WIDTH // 2, 290 + y_offset, size=20)
        
    elif t < 7.2:
        # Scene 1.2: The Wrong Layout (sghl ugd;l)
        local_t = t - 3.2
        full_wrong = "sghl ugd;l! phgjl ziyn?"
        chars_typed = min(len(full_wrong), int(local_t * 9))
        current_text = full_wrong[:chars_typed]
        
        draw_glass_card(draw, [280, 200, WIDTH - 280, 480], fill=(18, 23, 38, 240), border_color=(75, 85, 99, 120))
        
        draw.rounded_rectangle([280, 200, WIDTH - 280, 255], radius=20, fill=(30, 38, 60, 255))
        draw.ellipse([305, 222, 321, 238], fill=(239, 68, 68, 200))
        draw.ellipse([335, 222, 351, 238], fill=(245, 158, 11, 200))
        draw.ellipse([365, 222, 381, 238], fill=(16, 185, 129, 200))
        
        font_win = get_font(FONT_SEGOE, 22)
        draw.text((WIDTH // 2, 227), "Chat - Message Input", font=font_win, fill=(156, 163, 175), anchor="mm")
        
        font_code = get_font(FONT_SEGOE_BOLD, 44)
        draw.text((320, 330), current_text, font=font_code, fill=(248, 113, 113))
        
        if int(t * 4) % 2 == 0:
            c_bbox = font_code.getbbox(current_text)
            c_x = 320 + (c_bbox[2] - c_bbox[0] if current_text else 0) + 5
            draw.line([(c_x, 325), (c_x, 375)], fill=(255, 255, 255), width=3)
            
        if local_t > 1.4:
            slam_p = min(1.0, (local_t - 1.4) / 0.5)
            slam_e = ease_out_back(slam_p)
            card_y = int(540 + (1.0 - slam_e) * 80)
            
            draw_glass_card(draw, [280, card_y, WIDTH - 280, card_y + 240], fill=(45, 15, 25, 245), border_color=(239, 68, 68, 180), radius=18)
            
            font_alert_title = get_font(FONT_BOLD, 38)
            font_alert_sub = get_font(FONT_REGULAR, 28)
            
            a_title = reshape_fa("کیبورد روی انگلیسی جا مونده بود!")
            a_sub1 = reshape_fa("خواستی بنویسی: «سلام علیکم! حالت چطوره؟»")
            a_sub2 = reshape_fa("اما کلی وقتت تلف شد و حالا مجبوری کل متن رو پاک کنی...")
            
            draw_vector_warning_badge(draw, WIDTH - 330, card_y + 55, size=18)
            draw.text((WIDTH - 365, card_y + 55), a_title, font=font_alert_title, fill=(254, 202, 202), anchor="ra")
            draw.text((WIDTH - 330, card_y + 115), a_sub1, font=font_alert_sub, fill=(252, 165, 165), anchor="ra")
            draw.text((WIDTH - 330, card_y + 170), a_sub2, font=font_alert_sub, fill=(226, 232, 240), anchor="ra")
            
    else:
        # Scene 1.3: ZWNJ & Spacing
        local_t = t - 7.2
        font_header = get_font(FONT_BOLD, 46)
        h_text = reshape_fa("دردسر نیم‌فاصله‌ها و غلط‌های املایی تکراری!")
        draw.text((WIDTH // 2, 230), h_text, font=font_header, fill=(255, 255, 255), anchor="mm")
        
        examples = [
            ("می روم", "می‌روم", "نیم‌فاصله خودکار افعال"),
            ("کتاب ها", "کتاب‌ها", "نیم‌فاصله جمع‌ها"),
            ("دست انداز", "دست‌انداز", "ترکیب‌های مرکب")
        ]
        
        for idx, (wrong, right, desc) in enumerate(examples):
            cx = 380 + idx * 400
            cy = 440
            
            draw_glass_card(draw, [cx - 170, cy - 100, cx + 170, cy + 130], fill=(22, 28, 45, 220), border_color=(239, 68, 68, 90))
            
            font_w = get_font(FONT_BOLD, 40)
            font_r = get_font(FONT_BOLD, 36)
            font_d = get_font(FONT_REGULAR, 22)
            
            w_fa = reshape_fa(wrong)
            r_fa = reshape_fa(right)
            d_fa = reshape_fa(desc)
            
            draw.text((cx, cy - 40), w_fa, font=font_w, fill=(248, 113, 113), anchor="mm")
            draw.line([(cx - 70, cy - 40), (cx + 70, cy - 40)], fill=(239, 68, 68), width=3)
            
            draw.text((cx, cy + 30), f"✓ {r_fa}", font=font_r, fill=(52, 211, 153), anchor="mm")
            draw.text((cx, cy + 85), d_fa, font=font_d, fill=(148, 163, 184), anchor="mm")
            
        if local_t > 1.2:
            font_call = get_font(FONT_BOLD, 34)
            c_text = reshape_fa("اما وقتشه که با این مشکلات برای همیشه خداحافظی کنی!")
            draw.text((WIDTH // 2, 730), c_text, font=font_call, fill=(56, 189, 248), anchor="mm")
            
    return canvas.convert("RGB")

# ==============================================================================
# CLIP 2: THE SOLUTION & CORE FEATURES (0 - 10s)
# ==============================================================================
def render_frame_clip2(t):
    canvas = create_base_canvas(t, 2)
    draw = ImageDraw.Draw(canvas)
    draw_top_bar(canvas, "روان", "بخش دوم: معرفی دستیار هوشمند روان", badge_color=(6, 182, 212))
    
    if t < 3.5:
        p = min(1.0, t / 0.8)
        scale = 0.8 + 0.2 * ease_out_back(p)
        
        if ICON_IMG:
            target_size = int(180 * scale)
            ico_res = ICON_IMG.resize((target_size, target_size), Image.Resampling.LANCZOS)
            glow_size = target_size + 80
            draw.ellipse([WIDTH//2 - glow_size//2, 330 - glow_size//2, WIDTH//2 + glow_size//2, 330 + glow_size//2], fill=(6, 182, 212, 35))
            canvas.paste(ico_res, (WIDTH//2 - target_size//2, 330 - target_size//2), ico_res)
            
        font_title = get_font(FONT_BOLD, 68)
        font_sub = get_font(FONT_MEDIUM, 38)
        font_tag = get_font(FONT_REGULAR, 26)
        
        t1 = reshape_fa("روان | Ravaan")
        t2 = reshape_fa("دستیار هوشمند و فوق‌سریع تایپ فارسی در ویندوز")
        t3 = reshape_fa("نسخه ۲.۵.۰ — بومی، فوق‌سبک و بدون مزاحمت")
        
        draw.text((WIDTH // 2, 490), t1, font=font_title, fill=(255, 255, 255), anchor="mm")
        draw.text((WIDTH // 2, 570), t2, font=font_sub, fill=(147, 197, 253), anchor="mm")
        draw.text((WIDTH // 2, 640), t3, font=font_tag, fill=(203, 213, 225), anchor="mm")
        
    elif t < 7.5:
        font_h = get_font(FONT_BOLD, 42)
        h_text = reshape_fa("پیش‌بینی هوشمند کلمات بعدی با سرعت نور!")
        draw.text((WIDTH // 2, 160), h_text, font=font_h, fill=(255, 255, 255), anchor="mm")
        
        draw_glass_card(draw, [240, 220, WIDTH - 240, 420], fill=(16, 22, 38, 230), border_color=(56, 189, 248, 120))
        
        font_typed_label = get_font(FONT_REGULAR, 24)
        draw.text((WIDTH - 280, 250), reshape_fa("متن در حال تایپ:"), font=font_typed_label, fill=(148, 163, 184), anchor="ra")
        
        font_typed = get_font(FONT_BOLD, 54)
        typed_str = "س"
        draw.text((WIDTH - 280, 330), reshape_fa(typed_str), font=font_typed, fill=(255, 255, 255), anchor="ra")
        
        if POPUP_IMG:
            pop_w, pop_h = POPUP_IMG.size
            disp_w = int(pop_w * 0.95)
            disp_h = int(pop_h * 0.95)
            pop_res = POPUP_IMG.resize((disp_w, disp_h), Image.Resampling.LANCZOS)
            
            pop_x = WIDTH // 2 - disp_w // 2
            pop_y = 440
            
            draw_glass_card(draw, [pop_x - 10, pop_y - 10, pop_x + disp_w + 10, pop_y + disp_h + 10], fill=(10, 15, 30, 250), border_color=(6, 182, 212, 180), radius=16)
            canvas.paste(pop_res, (pop_x, pop_y), pop_res)
            
        pills = [
            ("تاخیر زیر ۱۰ میلی‌ثانیه", (6, 182, 212)),
            ("تبدیل فوری کیبورد اشتباه", (168, 85, 247)),
            ("نیم‌فاصله خودکار بدون کلید اضافه", (34, 197, 94))
        ]
        
        for idx, (p_text, p_color) in enumerate(pills):
            px = 350 + idx * 420
            py = 800
            
            font_p = get_font(FONT_BOLD, 24)
            p_fa = reshape_fa(f"✓ {p_text}")
            draw_glass_card(draw, [px - 180, py - 30, px + 180, py + 30], fill=(20, 26, 45, 220), border_color=(*p_color, 160), radius=30)
            draw.text((px, py), p_fa, font=font_p, fill=(255, 255, 255), anchor="mm")
            
    else:
        font_h = get_font(FONT_BOLD, 46)
        h_text = reshape_fa("کاملاً نامرئی، سبک و بدون ایجاد وقفه در تایپ!")
        draw.text((WIDTH // 2, 200), h_text, font=font_h, fill=(255, 255, 255), anchor="mm")
        
        draw_glass_card(draw, [320, 290, WIDTH - 320, 680], fill=(18, 24, 40, 235), border_color=(59, 130, 246, 120))
        
        if TRAY_IMG:
            canvas.paste(TRAY_IMG, (380, 360), TRAY_IMG)
            
        font_bullet_t = get_font(FONT_BOLD, 32)
        font_bullet_s = get_font(FONT_REGULAR, 26)
        
        bullets = [
            ("✓ بدون دزدیدن فوکوس پنجره فعال", "پوینتر کیبورد در هر برنامه‌ای بدون کوچک‌ترین اختلال حفظ می‌شود."),
            ("✓ پایش سبک حافظه (زیر ۳۵ مگابایت رم)", "هیچ بار پردازشی به سیستم یا بازی وارد نمی‌کند."),
            ("✓ گزینه‌های پیشرفته شخصی‌سازی", "تنظیم فاصله خودکار، تاخیر، کلیدهای میانبر و ظاهر باکس.")
        ]
        
        for idx, (b_title, b_sub) in enumerate(bullets):
            by = 360 + idx * 95
            draw.text((WIDTH - 360, by), reshape_fa(b_title), font=font_bullet_t, fill=(56, 189, 248), anchor="ra")
            draw.text((WIDTH - 360, by + 40), reshape_fa(b_sub), font=font_bullet_s, fill=(203, 213, 225), anchor="ra")
            
    return canvas.convert("RGB")

# ==============================================================================
# CLIP 3: SUPERPOWERS, PRIVACY & OUTRO (0 - 10s)
# ==============================================================================
def render_frame_clip3(t):
    canvas = create_base_canvas(t, 3)
    draw = ImageDraw.Draw(canvas)
    draw_top_bar(canvas, "روان", "بخش سوم: امکانات جادویی و حریم خصوصی", badge_color=(16, 185, 129))
    
    if t < 4.0:
        font_h = get_font(FONT_BOLD, 44)
        h_text = reshape_fa("امکانات شگفت‌انگیز: تبدیل عدد به حروف و تاریخ روز")
        draw.text((WIDTH // 2, 170), h_text, font=font_h, fill=(255, 255, 255), anchor="mm")
        
        # Card 1: 1500000# -> یک میلیون و پانصد هزار تومان
        draw_glass_card(draw, [260, 250, WIDTH - 260, 470], fill=(20, 30, 45, 240), border_color=(245, 158, 11, 160))
        
        font_c1_t = get_font(FONT_REGULAR, 24)
        draw.text((WIDTH - 300, 280), reshape_fa("تایپ عدد با کاراکتر # در هر کجا:"), font=font_c1_t, fill=(203, 213, 225), anchor="ra")
        
        font_code_num = get_font(FONT_SEGOE_BOLD, 46)
        font_arrow = get_font(FONT_SEGOE_BOLD, 40)
        font_res_fa = get_font(FONT_BOLD, 42)
        
        draw.text((320, 370), "1500000#", font=font_code_num, fill=(251, 191, 36))
        draw.text((640, 370), "➔", font=font_arrow, fill=(156, 163, 175))
        draw.text((WIDTH - 300, 370), reshape_fa("یک میلیون و پانصد هزار تومان"), font=font_res_fa, fill=(52, 211, 153), anchor="ra")
        
        # Card 2: Date & Shortcut
        draw_glass_card(draw, [260, 510, WIDTH - 260, 720], fill=(20, 30, 45, 240), border_color=(56, 189, 248, 140))
        
        font_c2_t = get_font(FONT_REGULAR, 24)
        draw.text((WIDTH - 300, 540), reshape_fa("توسعه فوری تاریخ و کلیدهای میانبر:"), font=font_c2_t, fill=(203, 213, 225), anchor="ra")
        
        draw.text((320, 625), reshape_fa("امروز/"), font=get_font(FONT_BOLD, 40), fill=(56, 189, 248))
        draw.text((540, 625), "➔", font=font_arrow, fill=(156, 163, 175))
        draw.text((WIDTH - 300, 625), reshape_fa("چهارشنبه ۹ اردیبهشت ۱۴۰۵"), font=font_res_fa, fill=(147, 197, 253), anchor="ra")
        
        font_tag_sub = get_font(FONT_REGULAR, 26)
        draw.text((WIDTH // 2, 790), reshape_fa("میانبر Ctrl+Alt+N برای تبدیل فوری اعداد انگلیسی به فارسی و بالعکس"), font=font_tag_sub, fill=(226, 232, 240), anchor="mm")
        
    elif t < 7.2:
        draw_glass_card(draw, [320, 200, WIDTH - 320, 750], fill=(12, 32, 28, 245), border_color=(16, 185, 129, 180), radius=24)
        
        # Vector padlock icon
        draw.ellipse([WIDTH//2 - 60, 245, WIDTH//2 + 60, 365], fill=(16, 185, 129, 35), outline=(16, 185, 129, 200), width=3)
        draw_vector_lock(draw, WIDTH // 2, 305, color=(52, 211, 153, 255), size=1.0)
        
        font_priv_title = get_font(FONT_BOLD, 50)
        font_priv_sub1 = get_font(FONT_BOLD, 34)
        font_priv_sub2 = get_font(FONT_REGULAR, 28)
        
        draw.text((WIDTH // 2, 420), reshape_fa("۱۰۰٪ آفلاین — امنیت کامل و تضمین‌شده"), font=font_priv_title, fill=(255, 255, 255), anchor="mm")
        draw.text((WIDTH // 2, 510), reshape_fa("صفر ارسال داده به اینترنت (Zero Telemetry)"), font=font_priv_sub1, fill=(52, 211, 153), anchor="mm")
        
        draw.text((WIDTH // 2, 595), reshape_fa("هیچ پسورد، متن یا کلیدی از سیستم شما خارج نمی‌شود."), font=font_priv_sub2, fill=(203, 213, 225), anchor="mm")
        draw.text((WIDTH // 2, 650), reshape_fa("تمامی پردازش‌ها و مدل لغوی کلمات به صورت ۱۰۰٪ محلی در سیستم شماست."), font=font_priv_sub2, fill=(148, 163, 184), anchor="mm")
        
    else:
        draw_glass_card(draw, [280, 160, WIDTH - 280, 800], fill=(16, 22, 38, 250), border_color=(6, 182, 212, 180), radius=28)
        
        if ICON_IMG:
            ico_large = ICON_IMG.resize((140, 140), Image.Resampling.LANCZOS)
            canvas.paste(ico_large, (WIDTH // 2 - 70, 210), ico_large)
            
        font_f_title = get_font(FONT_BOLD, 62)
        font_f_tagline = get_font(FONT_MEDIUM, 38)
        font_f_cta = get_font(FONT_BOLD, 42)
        font_f_repo = get_font(FONT_SEGOE_BOLD, 36)
        
        draw.text((WIDTH // 2, 400), reshape_fa("روان | تجربه‌ای روان از نوشتن به زبان فارسی"), font=font_f_title, fill=(255, 255, 255), anchor="mm")
        draw.text((WIDTH // 2, 480), reshape_fa("رایگان • متن‌باز (Open Source) • ویژه ویندوز ۱۰ و ۱۱"), font=font_f_tagline, fill=(147, 197, 253), anchor="mm")
        
        draw.rounded_rectangle([WIDTH//2 - 280, 560, WIDTH//2 + 280, 640], radius=40, fill=(6, 182, 212, 230), outline=(255, 255, 255, 180), width=2)
        draw.text((WIDTH // 2, 597), reshape_fa("همین حالا رایگان دانلود کنید"), font=font_f_cta, fill=(10, 15, 30), anchor="mm")
        
        draw.text((WIDTH // 2, 710), "github.com/mohsen-niksirat/Ravaan", font=font_f_repo, fill=(226, 232, 240), anchor="mm")
        
    return canvas.convert("RGB")

# ==============================================================================
# AUDIO GENERATION & DUCKING ENGINE (VOICEOVER + CALM MUSIC)
# ==============================================================================
NARRATION_SCRIPTS = {
    1: "تا حالا برات پیش اومده که تند تند تایپ کنی و ببینی کیبورد روی انگلیسی جا مونده؟ یا از دردسر نیم‌فاصله‌ها خسته شده باشی؟",
    2: "اینجا روان به کمکت میاد! پیش‌بینی لحظه‌ای کلمات، اصلاح خودکار کیبورد و درج نیم‌فاصله‌ها، بدون افت سرعت.",
    3: "تبدیل جادویی عدد به حروف، تاریخ روز و امنیت صد در صدی آفلاین. همین حالا روان رو رایگان امتحان کنید!"
}

async def generate_voiceover(clip_idx, text):
    """Generates studio-quality Persian neural narration via Microsoft Edge Neural TTS."""
    voice_path = os.path.join(OUT_DIR, f"voice_{clip_idx}.wav")
    rate = "+10%" if clip_idx != 2 else "+14%"
    comm = edge_tts.Communicate(text, "fa-IR-FaridNeural", rate=rate)
    tmp_mp3 = os.path.join(OUT_DIR, f"tmp_voice_{clip_idx}.mp3")
    await comm.save(tmp_mp3)
    # Convert to 44.1kHz mono wav
    subprocess.run(["ffmpeg", "-y", "-i", tmp_mp3, "-ar", str(SAMPLE_RATE), "-ac", "1", voice_path], capture_output=True)
    try:
        os.remove(tmp_mp3)
    except Exception:
        pass
    return voice_path

def synthesize_calm_background_track(duration=10.0, clip_idx=1):
    """Synthesizes gentle, pleasant, relaxing ambient background chords."""
    total_samples = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, total_samples, endpoint=False)
    
    # Warm chords tailored per section
    if clip_idx == 1:
        # Reflective/Mellow: Am9 -> Dm7
        chord1 = [220.00, 261.63, 329.63, 392.00] # Am7
        chord2 = [196.00, 246.94, 293.66, 349.23] # G7
    elif clip_idx == 2:
        # Inspiring/Uplifting: Cmaj7 -> Fmaj7
        chord1 = [261.63, 329.63, 392.00, 493.88] # Cmaj7
        chord2 = [174.61, 220.00, 261.63, 329.63] # Fmaj7
    else:
        # Harmonious Resolution: Fmaj7 -> C add9
        chord1 = [174.61, 220.00, 261.63, 329.63] # Fmaj7
        chord2 = [261.63, 293.66, 329.63, 392.00] # Cadd9
        
    bg = np.zeros(total_samples, dtype=np.float32)
    half = total_samples // 2
    
    for seg_idx, chord in enumerate([chord1, chord2]):
        start = seg_idx * half
        end = (seg_idx + 1) * half
        tc = t[start:end] - (seg_idx * (duration / 2.0))
        seg_dur = duration / 2.0
        
        # Smooth organic bell/rhodes envelope
        env = np.sin(np.pi * tc / seg_dur) ** 1.3
        
        wave = np.zeros(len(tc))
        for f in chord:
            # Fundamental + warm octave + soft shimmer
            wave += np.sin(2 * np.pi * f * tc) * 0.22
            wave += np.sin(2 * np.pi * (f * 0.5) * tc) * 0.12 # warmth
            wave += np.sin(2 * np.pi * (f * 2.0) * tc) * 0.04 # air
            # subtle tremolo
            wave *= (1.0 + 0.04 * np.sin(2 * np.pi * 3.0 * tc))
            
        bg[start:end] += wave * env
        
    # Gentle normalization to soft background level
    max_val = np.max(np.abs(bg))
    if max_val > 0:
        bg = (bg / max_val) * 0.18
    return bg

def build_mixed_audio(clip_idx, duration=10.0):
    """Combines Persian voiceover and calming ambient background music with professional ducking."""
    total_samples = int(SAMPLE_RATE * duration)
    mixed = np.zeros(total_samples, dtype=np.float32)
    
    # 1. Calming background music
    bg_music = synthesize_calm_background_track(duration, clip_idx)
    
    # 2. Generate voiceover
    text = NARRATION_SCRIPTS[clip_idx]
    voice_path = asyncio.run(generate_voiceover(clip_idx, text))
    
    # Read voiceover wav
    sr_v, v_data = wavfile.read(voice_path)
    v_norm = v_data.astype(np.float32) / 32768.0
    
    # Position narration starting at 0.5s for clean natural lead-in
    lead_in = int(0.5 * SAMPLE_RATE)
    v_len = min(len(v_norm), total_samples - lead_in)
    
    # Duck music where voiceover is active
    ducking_mask = np.ones(total_samples, dtype=np.float32)
    ducking_mask[lead_in : lead_in + v_len] = 0.55 # 45% ducking during speech
    
    # Smooth ducking transitions
    smooth_len = int(0.2 * SAMPLE_RATE)
    ducking_mask = np.convolve(ducking_mask, np.ones(smooth_len)/smooth_len, mode='same')
    
    # Combine
    mixed = (bg_music * ducking_mask)
    mixed[lead_in : lead_in + v_len] += (v_norm[:v_len] * 0.92)
    
    # Fade in / fade out at clip boundaries
    fade_len = int(0.15 * SAMPLE_RATE)
    mixed[:fade_len] *= np.linspace(0, 1, fade_len)
    mixed[-fade_len:] *= np.linspace(1, 0, fade_len)
    
    # Final master normalization
    m_max = np.max(np.abs(mixed))
    if m_max > 0:
        mixed = (mixed / m_max) * 0.90
        
    out_audio = os.path.join(OUT_DIR, f"mixed_clip{clip_idx}.wav")
    wavfile.write(out_audio, SAMPLE_RATE, (mixed * 32767).astype(np.int16))
    return out_audio

# ==============================================================================
# VIDEO RENDERING & ENCODING PIPELINE
# ==============================================================================
def render_clip(clip_idx):
    """Renders a single 10-second clip (300 frames) and encodes via ffmpeg."""
    clip_name = f"clip{clip_idx}"
    out_mp4 = os.path.join(OUT_DIR, f"{clip_name}.mp4")

    print(f"\n[+] Generating Persian voiceover & calming music for {clip_name}...")
    audio_wav = build_mixed_audio(clip_idx, duration=10.0)
    
    print(f"[+] Rendering {clip_name} (10.0s @ {FPS}fps = {int(10.0 * FPS)} frames)...")
    
    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{WIDTH}x{HEIGHT}",
        "-pix_fmt", "rgb24",
        "-r", str(FPS),
        "-i", "-",
        "-i", audio_wav,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        out_mp4
    ]
    
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    
    total_frames = int(10.0 * FPS)
    render_func = [render_frame_clip1, render_frame_clip2, render_frame_clip3][clip_idx - 1]
    
    for frame_idx in range(total_frames):
        t = frame_idx / FPS
        frame = render_func(t)
        proc.stdin.write(frame.tobytes())
        if frame_idx % 60 == 0 or frame_idx == total_frames - 1:
            print(f"    Frame {frame_idx + 1}/{total_frames} (t = {t:.2f}s)")
            
    proc.stdin.close()
    stderr = proc.stderr.read().decode("utf-8", errors="ignore")
    proc.wait()
    
    if proc.returncode != 0:
        print(f"Error encoding {clip_name}: {stderr}")
        raise RuntimeError(f"FFmpeg failed for {clip_name}")
        
    print(f"[OK] {clip_name}.mp4 generated successfully: {out_mp4}")
    return out_mp4

def concatenate_clips(clips, final_output):
    """Concatenates the 3 10-second clips into a 30-second final video."""
    print(f"\n[+] Concatenating {len(clips)} clips into {final_output}...")
    list_file = os.path.join(OUT_DIR, "concat_list.txt")
    with open(list_file, "w", encoding="utf-8") as f:
        for c in clips:
            f.write(f"file '{c.replace(os.sep, '/')}'\n")
            
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", list_file,
        "-c", "copy",
        final_output
    ]
    
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Concat copy failed, trying re-encoding: {res.stderr}")
        cmd_reencode = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", list_file,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-c:a", "aac",
            "-b:a", "192k",
            final_output
        ]
        res = subprocess.run(cmd_reencode, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"FFmpeg concat re-encode failed: {res.stderr}")
            
    print(f"[OK] Final 30-Second Teaser Video created: {final_output}")
    return final_output

def main():
    print("=== Ravaan 30-Second Teaser Generation (V2) Started ===")
    clips = []
    for i in range(1, 4):
        clip_path = render_clip(i)
        clips.append(clip_path)
        
    final_output = os.path.join(OUT_DIR, "ravaan_teaser_30s.mp4")
    concatenate_clips(clips, final_output)
    print("\n=== ALL TASKS COMPLETED SUCCESSFULLY ===")

if __name__ == "__main__":
    main()
