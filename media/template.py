"""
media/template.py  ·  v3
Production Image Template Engine
Font boyutları büyütüldü, Railway font uyumlu, fallback güçlü.

Grid:
  Canvas : 1080 x 1920
  Header : 0   → 260  (h=260)
  Image  : 260 → 1680 (h=1420)
  Footer : 1680→ 1920 (h=240)
"""

import logging
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from media.logo import load_logo

logger = logging.getLogger(__name__)

W, H       = 1080, 1920
MARGIN     = 60
HEADER_H   = 260
FOOTER_H   = 240
IMG_TOP    = HEADER_H
IMG_H      = H - HEADER_H - FOOTER_H
IMG_BOT    = IMG_TOP + IMG_H

BG         = (10, 14, 26)
TEAL       = (0, 201, 200)
WHITE      = (255, 255, 255)
SUBTEXT    = (160, 190, 190)
FOOTER_BG  = (0, 0, 0, 210)
HEADER_BG  = (0, 40, 50, 40)

DOCTOR_NAME = "Assoc. Prof. Dr. Özgür Karakoyun"
PHONE       = "+90 545 919 54 13"
WEBSITE     = "www.ozgurkarakoyun.com"
EMAIL       = "info@ozgurkarakoyun.com"


# ── Font loader ───────────────────────────────────────────────────────────────

FONT_PATHS_BOLD = [
    "static/fonts/Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "/usr/share/fonts/truetype/crosextra/Carlito-Bold.ttf",
]

FONT_PATHS_REGULAR = [
    "static/fonts/Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    "/usr/share/fonts/truetype/crosextra/Carlito-Regular.ttf",
]

_font_cache: dict = {}

def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    key = (size, bold)
    if key in _font_cache:
        return _font_cache[key]
    paths = FONT_PATHS_BOLD if bold else FONT_PATHS_REGULAR
    for p in paths:
        try:
            f = ImageFont.truetype(p, size)
            _font_cache[key] = f
            return f
        except Exception:
            continue
    # Hard fallback: try any .ttf on the system
    import glob
    for p in glob.glob("/usr/share/fonts/**/*.ttf", recursive=True):
        try:
            f = ImageFont.truetype(p, size)
            logger.warning(f"Using fallback font: {p}")
            _font_cache[key] = f
            return f
        except Exception:
            continue
    logger.error("NO TTF FONT FOUND — text will be invisible. Install fonts-dejavu-core.")
    return ImageFont.load_default()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _tw(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0]

def _th(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[3] - bb[1]

def _cx(draw, text, font):
    """X position to centre text on canvas."""
    return (W - _tw(draw, text, font)) // 2

def _semi(canvas, x0, y0, x1, y1, color):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rect  = Image.new("RGBA", (x1 - x0, y1 - y0), color)
    layer.paste(rect, (x0, y0))
    return Image.alpha_composite(canvas, layer)

def _grad(canvas, y0, y1, c0, c1):
    draw = ImageDraw.Draw(canvas)
    span = max(1, y1 - y0)
    for i in range(span):
        t = i / span
        r = int(c0[0] + (c1[0]-c0[0])*t)
        g = int(c0[1] + (c1[1]-c0[1])*t)
        b = int(c0[2] + (c1[2]-c0[2])*t)
        a = int(c0[3] + (c1[3]-c0[3])*t)
        draw.line([(0, y0+i), (W, y0+i)], fill=(r, g, b, a))

def _fit_into(img, bw, bh):
    img = img.convert("RGBA")
    sw, sh = img.size
    # Blurred fill background
    bg = img.resize((bw, bh), Image.LANCZOS)
    bg = bg.filter(ImageFilter.GaussianBlur(28))
    bg = ImageEnhance.Brightness(bg.convert("RGB")).enhance(0.3).convert("RGBA")
    bg = Image.alpha_composite(bg, Image.new("RGBA", (bw, bh), (0,0,0,80)))
    # Scaled foreground
    scale = min(bw / sw, bh / sh) * 0.92
    nw, nh = max(1, int(sw*scale)), max(1, int(sh*scale))
    fg = img.resize((nw, nh), Image.LANCZOS)
    bg.paste(fg, ((bw-nw)//2, (bh-nh)//2), fg)
    return bg


# ── POST builder ──────────────────────────────────────────────────────────────

def build_image_post(input_path, output_path, topic, hook=""):
    canvas = Image.new("RGBA", (W, H), (*BG, 255))

    # Subtle arc decoration
    arc = Image.new("RGBA", (W, H), (0,0,0,0))
    ImageDraw.Draw(arc).ellipse([-200,-200,440,440], outline=(*TEAL,22), width=70)
    canvas = Image.alpha_composite(canvas, arc)

    # Header tint
    canvas = _semi(canvas, 0, 0, W, HEADER_H, HEADER_BG)
    draw = ImageDraw.Draw(canvas)
    # Header bottom accent line
    draw.rectangle([0, HEADER_H-5, W, HEADER_H], fill=(*TEAL, 255))

    # ── User image ────────────────────────────────────────────────────────────
    try:
        user_img = Image.open(input_path).convert("RGBA")
        fitted   = _fit_into(user_img, W, IMG_H)
        canvas.paste(fitted, (0, IMG_TOP), fitted)
    except Exception as exc:
        logger.error(f"Image load failed: {exc}")
        ph = Image.new("RGBA", (W, IMG_H), (20, 32, 48, 255))
        canvas.paste(ph, (0, IMG_TOP))

    # Gradients
    _grad(canvas, IMG_TOP, IMG_TOP+200, (10,14,26,200), (0,0,0,0))
    _grad(canvas, IMG_BOT-240, IMG_BOT,  (0,0,0,0), (0,0,0,220))

    # Footer overlay
    canvas = _semi(canvas, 0, IMG_BOT, W, H, FOOTER_BG)
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([0, IMG_BOT, W, IMG_BOT+4], fill=(*TEAL,255))

    # ── HEADER content ────────────────────────────────────────────────────────
    # Logo veya OK pill
    logo = load_logo(target_h=110)
    lx, ly = MARGIN, 30
    if logo is not None:
        # Logo paste (RGBA transparan destekli)
        canvas.paste(logo, (lx, ly), logo)
        logo_end_x = lx + logo.width + 16
    else:
        # Fallback: OK pill
        lf = _font(46, bold=True)
        lw = _tw(draw, "OK", lf)
        draw.rounded_rectangle([lx-10, ly-6, lx+lw+16, ly+56], radius=12, fill=(*TEAL,255))
        draw.text((lx+4, ly), "OK", font=lf, fill=(*BG,255))
        logo_end_x = lx + lw + 32

    draw = ImageDraw.Draw(canvas)  # re-acquire after paste

    # Doctor name — right side of header
    nf = _font(30)
    nw = _tw(draw, DOCTOR_NAME, nf)
    draw.text((W-MARGIN-nw, 34), DOCTOR_NAME, font=nf, fill=(*WHITE,240))

    # Specialty
    sf = _font(26)
    spec = "Orthopedics & Traumatology"
    spw = _tw(draw, spec, sf)
    draw.text((W-MARGIN-spw, 76), spec, font=sf, fill=(*TEAL,210))

    # ── Topic title (lower third, above footer) ───────────────────────────────
    title_font = _font(88, bold=True)
    hook_font  = _font(40)

    topic_up  = topic.upper()
    wrapped   = textwrap.fill(topic_up, width=16).split("\n")
    line_h    = 96
    block_h   = len(wrapped) * line_h + (44 if hook else 0)
    title_y   = IMG_BOT - 48 - block_h

    for i, line in enumerate(wrapped[:3]):
        lx2 = _cx(draw, line, title_font)
        draw.text((lx2, title_y + i*line_h), line, font=title_font, fill=(*WHITE,255))

    if hook:
        hy = title_y + len(wrapped)*line_h + 10
        hook_short = textwrap.fill(hook, width=42)
        for j, hl in enumerate(hook_short.split("\n")[:2]):
            hx = _cx(draw, hl, hook_font)
            draw.text((hx, hy + j*48), hl, font=hook_font, fill=(*TEAL,230))

    # ── FOOTER content ────────────────────────────────────────────────────────
    fy     = IMG_BOT + 22
    fnf    = _font(38, bold=True)
    fdf    = _font(30)
    fdisf  = _font(24)

    # Left: name + website
    draw.text((MARGIN, fy),    DOCTOR_NAME,       font=fnf, fill=(*WHITE,255))
    draw.text((MARGIN, fy+52), f"🌐 {WEBSITE}",  font=fdf, fill=(*TEAL,235))

    # Right: phone + email
    col2 = W//2 + 20
    draw.text((col2, fy),    f"📞 {PHONE}",  font=fdf, fill=(*WHITE,240))
    draw.text((col2, fy+48), f"✉  {EMAIL}",  font=fdf, fill=(*SUBTEXT,210))

    # Disclaimer
    dis  = "⚕  Medical information only. Consult your doctor."
    disw = _tw(draw, dis, fdisf)
    draw.text(((W-disw)//2, H-36), dis, font=fdisf, fill=(130,155,155,185))

    # Save
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    final = canvas.convert("RGB")
    assert final.size == (W, H)
    final.save(str(out), "JPEG", quality=93, optimize=True)
    logger.info(f"Post {W}x{H} → {output_path}")


# ── STORY builder ─────────────────────────────────────────────────────────────

def build_story_post(input_path, output_path, topic, hook=""):
    canvas = Image.new("RGBA", (W, H), (*BG, 255))

    # Full-bleed user image
    try:
        user_img = Image.open(input_path).convert("RGBA")
        sw, sh = user_img.size
        scale  = max(W/sw, H/sh)
        nw, nh = int(sw*scale), int(sh*scale)
        filled = user_img.resize((nw, nh), Image.LANCZOS)
        x_off  = (W-nw)//2
        y_off  = (H-nh)//2
        canvas.paste(filled, (x_off, y_off), filled)
    except Exception as exc:
        logger.warning(f"Story image load failed: {exc}")

    # Top + bottom gradients
    _grad(canvas, 0,   320, (0,0,0,220), (0,0,0,0))
    _grad(canvas, H-380, H, (0,0,0,0),   (0,0,0,230))

    draw = ImageDraw.Draw(canvas)

    # Top: logo veya OK pill + name
    logo = load_logo(target_h=90)
    lx2, ly2 = MARGIN, 28
    if logo is not None:
        canvas.paste(logo, (lx2, ly2), logo)
        name_x = lx2 + logo.width + 20
        draw = ImageDraw.Draw(canvas)
    else:
        lf = _font(40, bold=True)
        lw = _tw(draw, "OK", lf)
        draw.rounded_rectangle([lx2-10, ly2, lx2+lw+16, ly2+68], radius=12, fill=(*TEAL,255))
        draw.text((lx2+4, ly2+2), "OK", font=lf, fill=(*BG,255))
        name_x = lx2 + lw + 36

    nf = _font(30)
    draw.text((name_x, 40), DOCTOR_NAME, font=nf, fill=(*WHITE,240))

    # Topic + hook bottom
    tf  = _font(86, bold=True)
    hkf = _font(40)

    topic_up = topic.upper()
    wrapped  = textwrap.fill(topic_up, width=16).split("\n")
    line_h   = 96
    block_h  = len(wrapped)*line_h + (54 if hook else 0)
    ty       = H - 160 - block_h

    for i, line in enumerate(wrapped[:3]):
        lx = _cx(draw, line, tf)
        draw.text((lx, ty + i*line_h), line, font=tf, fill=(*WHITE,255))

    if hook:
        hy = ty + len(wrapped)*line_h + 12
        hook_short = textwrap.fill(hook, width=38)
        for j, hl in enumerate(hook_short.split("\n")[:2]):
            hx = _cx(draw, hl, hkf)
            draw.text((hx, hy + j*50), hl, font=hkf, fill=(*TEAL,230))

    # Website bottom
    wf  = _font(30)
    wt  = f"🌐 {WEBSITE}"
    wwt = _tw(draw, wt, wf)
    draw.text(((W-wwt)//2, H-60), wt, font=wf, fill=(*TEAL,230))

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    final = canvas.convert("RGB")
    assert final.size == (W, H)
    final.save(str(out), "JPEG", quality=93, optimize=True)
    logger.info(f"Story {W}x{H} → {output_path}")
