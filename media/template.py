"""
media/template.py  ·  v2  –  Production Image Template Engine
Guaranteed 9:16 output. Proper grid system. Safe zones. Correct scaling.
Builds: Post (1080x1920) and Story (1080x1920 with looser layout)

Grid spec
─────────────────────────────────────────
Canvas : 1080 x 1920 px
Margin : 56 px (all sides)
Header : y  0  → 240  (h=240)  branding bar
Image  : y 240 → 1680 (h=1440) user photo zone
Footer : y 1680→ 1920 (h=240)  contact bar
Accent line top header / top footer : 4 px

Colours
─────────────────────────────────────────
#0A0E1A  deep navy bg
#00C9C8  medical teal accent
#FFFFFF  primary text
#B0C4C4  secondary text
#000000 at 80% footer overlay
"""

import logging
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

logger = logging.getLogger(__name__)

# ── Canvas constants ──────────────────────────────────────────────────────────
W, H        = 1080, 1920
MARGIN      = 56
HEADER_H    = 240
FOOTER_H    = 240
IMG_TOP     = HEADER_H
IMG_H       = H - HEADER_H - FOOTER_H   # 1440 px
IMG_BOT     = IMG_TOP + IMG_H

# ── Colours ───────────────────────────────────────────────────────────────────
BG          = (10, 14, 26)
TEAL        = (0, 201, 200)
WHITE       = (255, 255, 255)
SUBTEXT     = (176, 196, 196)
FOOTER_BG   = (0, 0, 0, 204)            # 80% opacity
HEADER_TINT = (0, 201, 200, 18)

# ── Brand ─────────────────────────────────────────────────────────────────────
DOCTOR_NAME = "Assoc. Prof. Dr. Özgür Karakoyun"
PHONE       = "+90 545 919 54 13"
WEBSITE     = "www.ozgurkarakoyun.com"
EMAIL       = "info@ozgurkarakoyun.com"


# ── Font loader ───────────────────────────────────────────────────────────────

def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = []
    if bold:
        candidates = [
            "static/fonts/Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        ]
    else:
        candidates = [
            "static/fonts/Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        ]
    for p in candidates:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


# ── Image fitting ─────────────────────────────────────────────────────────────

def _fit_into(img: Image.Image, box_w: int, box_h: int) -> Image.Image:
    """
    Fit img into (box_w x box_h) keeping aspect ratio.
    Fills the box with a blurred + darkened version of the same image as bg.
    Returns an RGBA image exactly (box_w x box_h).
    """
    img = img.convert("RGBA")
    src_w, src_h = img.size

    # ── Blurred background fill ───────────────────────────────────────────────
    bg = img.resize((box_w, box_h), Image.LANCZOS)
    bg = bg.filter(ImageFilter.GaussianBlur(radius=24))
    bg = ImageEnhance.Brightness(bg.convert("RGB")).enhance(0.35).convert("RGBA")
    # Dark overlay on bg
    dark = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 100))
    bg = Image.alpha_composite(bg, dark)

    # ── Foreground: scale to fit ───────────────────────────────────────────────
    scale = min(box_w / src_w, box_h / src_h)
    # Leave 5% safe padding inside the photo zone
    scale *= 0.95
    new_w = max(1, int(src_w * scale))
    new_h = max(1, int(src_h * scale))
    fg = img.resize((new_w, new_h), Image.LANCZOS)

    # Centre paste
    x = (box_w - new_w) // 2
    y = (box_h - new_h) // 2
    bg.paste(fg, (x, y), fg)
    return bg


# ── Draw helpers ──────────────────────────────────────────────────────────────

def _draw_semi_rect(layer: Image.Image, x0: int, y0: int, x1: int, y1: int, color: tuple):
    """Paste a semi-transparent rectangle onto an RGBA layer."""
    rect = Image.new("RGBA", (x1 - x0, y1 - y0), color)
    layer.paste(rect, (x0, y0), rect)


def _text_width(draw: ImageDraw.ImageDraw, text: str, font) -> int:
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0]


def _centered_text(draw: ImageDraw.ImageDraw, y: int, text: str, font, fill):
    w = _text_width(draw, text, font)
    draw.text(((W - w) // 2, y), text, font=font, fill=fill)


# ── Gradient utility ──────────────────────────────────────────────────────────

def _vertical_gradient(canvas: Image.Image, y0: int, y1: int, c0: tuple, c1: tuple):
    """Draw a vertical gradient from c0 to c1 between y0 and y1 on canvas (RGBA)."""
    draw = ImageDraw.Draw(canvas)
    span = max(1, y1 - y0)
    for i in range(span):
        t = i / span
        r = int(c0[0] + (c1[0] - c0[0]) * t)
        g = int(c0[1] + (c1[1] - c0[1]) * t)
        b = int(c0[2] + (c1[2] - c0[2]) * t)
        a = int(c0[3] + (c1[3] - c0[3]) * t)
        draw.line([(0, y0 + i), (W, y0 + i)], fill=(r, g, b, a))


# ── Main builder: POST ────────────────────────────────────────────────────────

def build_image_post(
    input_path: str,
    output_path: str,
    topic: str,
    hook: str = "",
) -> None:
    """
    Build a 1080x1920 branded Instagram post image.
    Guaranteed output size. Safe zones respected.
    """
    # ── Base canvas (RGBA) ────────────────────────────────────────────────────
    canvas = Image.new("RGBA", (W, H), (*BG, 255))

    # ── Subtle top-left decorative arc ────────────────────────────────────────
    arc_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    arc_draw  = ImageDraw.Draw(arc_layer)
    arc_draw.ellipse([-180, -180, 420, 420], outline=(*TEAL, 28), width=60)
    canvas = Image.alpha_composite(canvas, arc_layer)

    # ── Header zone ───────────────────────────────────────────────────────────
    hdr_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    hdr_rect  = Image.new("RGBA", (W, HEADER_H), (*HEADER_TINT,))
    hdr_layer.paste(hdr_rect, (0, 0))
    canvas = Image.alpha_composite(canvas, hdr_layer)

    # Teal accent line bottom of header
    hdr_line = ImageDraw.Draw(canvas)
    hdr_line.rectangle([0, HEADER_H - 4, W, HEADER_H], fill=(*TEAL, 255))

    # ── User image zone ───────────────────────────────────────────────────────
    try:
        user_img = Image.open(input_path).convert("RGBA")
        fitted   = _fit_into(user_img, W, IMG_H)
        canvas.paste(fitted, (0, IMG_TOP), fitted)
    except Exception as exc:
        logger.error(f"User image load failed: {exc}")
        ph = Image.new("RGBA", (W, IMG_H), (20, 32, 48, 255))
        ph_draw = ImageDraw.Draw(ph)
        ph_draw.text(
            (W // 2 - 80, IMG_H // 2),
            "[ Image ]",
            font=_font(48),
            fill=(*SUBTEXT, 180),
        )
        canvas.paste(ph, (0, IMG_TOP))

    # ── Top gradient (header → image fade) ───────────────────────────────────
    grad = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    _vertical_gradient(grad, IMG_TOP, IMG_TOP + 160, (10, 14, 26, 180), (0, 0, 0, 0))
    canvas = Image.alpha_composite(canvas, grad)

    # ── Bottom gradient (image → footer fade) ────────────────────────────────
    grad2 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    _vertical_gradient(grad2, IMG_BOT - 200, IMG_BOT, (0, 0, 0, 0), (0, 0, 0, 200))
    canvas = Image.alpha_composite(canvas, grad2)

    # ── Footer overlay ────────────────────────────────────────────────────────
    ftr_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    _draw_semi_rect(ftr_layer, 0, IMG_BOT, W, H, FOOTER_BG)
    canvas = Image.alpha_composite(canvas, ftr_layer)

    # Teal accent line top of footer
    ftr_draw = ImageDraw.Draw(canvas)
    ftr_draw.rectangle([0, IMG_BOT, W, IMG_BOT + 4], fill=(*TEAL, 255))

    # ── Text draw context ─────────────────────────────────────────────────────
    draw = ImageDraw.Draw(canvas)

    # ── Header: Logo pill ─────────────────────────────────────────────────────
    logo_font = _font(38, bold=True)
    logo_text = "OK"
    lw = _text_width(draw, logo_text, logo_font)
    lx, ly = MARGIN, 28
    draw.rounded_rectangle([lx - 8, ly - 4, lx + lw + 14, ly + 52], radius=10, fill=(*TEAL, 255))
    draw.text((lx + 4, ly + 2), logo_text, font=logo_font, fill=(*BG, 255))

    # ── Header: Doctor name (right-aligned) ───────────────────────────────────
    name_font_sm = _font(28)
    dr_text = "Assoc. Prof. Dr. Özgür Karakoyun"
    drw = _text_width(draw, dr_text, name_font_sm)
    draw.text((W - MARGIN - drw, 32), dr_text, font=name_font_sm, fill=(*SUBTEXT, 230))

    # ── Header: Specialty line ────────────────────────────────────────────────
    spec_font = _font(24)
    spec_text = "Orthopedics & Traumatology"
    spw = _text_width(draw, spec_text, spec_font)
    draw.text((W - MARGIN - spw, 68), spec_text, font=spec_font, fill=(*TEAL, 200))

    # ── Topic title (lower-third over image, above footer) ────────────────────
    title_font = _font(76, bold=True)
    sub_font   = _font(34)

    topic_upper = topic.upper()
    wrapped = textwrap.fill(topic_upper, width=18).split("\n")
    title_y = IMG_BOT - FOOTER_H - 20 - len(wrapped) * 90

    for i, line in enumerate(wrapped[:3]):
        lw2 = _text_width(draw, line, title_font)
        draw.text(((W - lw2) // 2, title_y + i * 90), line, font=title_font, fill=(*WHITE, 255))

    # ── Hook line (below title) ───────────────────────────────────────────────
    if hook:
        hook_font = _font(36)
        hook_wrapped = textwrap.fill(hook, width=38).split("\n")
        hook_y = title_y + len(wrapped) * 90 + 12
        for j, hline in enumerate(hook_wrapped[:2]):
            hw = _text_width(draw, hline, hook_font)
            draw.text(((W - hw) // 2, hook_y + j * 44), hline, font=hook_font, fill=(*TEAL, 220))

    # ── Footer: Left column – doctor name + website ───────────────────────────
    ftr_y    = IMG_BOT + 26
    fname_f  = _font(36, bold=True)
    fdet_f   = _font(26)
    fsub_f   = _font(22)

    draw.text((MARGIN, ftr_y),      DOCTOR_NAME,              font=fname_f, fill=(*WHITE, 255))
    draw.text((MARGIN, ftr_y + 50), f"🌐 {WEBSITE}",         font=fdet_f,  fill=(*TEAL, 230))

    # ── Footer: Right column – phone + email ──────────────────────────────────
    col2 = W // 2 + 20
    draw.text((col2, ftr_y),      f"📞 {PHONE}", font=fdet_f, fill=(*WHITE, 240))
    draw.text((col2, ftr_y + 46), f"✉  {EMAIL}", font=fdet_f, fill=(*SUBTEXT, 210))

    # ── Footer: Disclaimer micro ──────────────────────────────────────────────
    dis_text = "⚕  Medical information only. Consult your doctor."
    dis_f    = _font(22)
    dw       = _text_width(draw, dis_text, dis_f)
    draw.text(
        ((W - dw) // 2, H - 36),
        dis_text,
        font=dis_f,
        fill=(140, 160, 160, 190),
    )

    # ── Save ──────────────────────────────────────────────────────────────────
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    final = canvas.convert("RGB")
    assert final.size == (W, H), f"Canvas size mismatch: {final.size}"
    final.save(str(out), "JPEG", quality=93, optimize=True)
    logger.info(f"Post saved {W}x{H} → {output_path}")


# ── Story builder (lighter layout, more breathing room) ──────────────────────

def build_story_post(
    input_path: str,
    output_path: str,
    topic: str,
    hook: str = "",
) -> None:
    """
    Build a 1080x1920 Story variant.
    Image fills most of the canvas. Minimal UI overlay at top + bottom only.
    """
    STORY_HEADER_H = 160
    STORY_FOOTER_H = 180

    canvas = Image.new("RGBA", (W, H), (*BG, 255))

    # Full-bleed user image
    try:
        user_img = Image.open(input_path).convert("RGBA")
        # For story: fill the full canvas (crop to fill)
        src_w, src_h = user_img.size
        scale = max(W / src_w, H / src_h)
        new_w, new_h = int(src_w * scale), int(src_h * scale)
        filled = user_img.resize((new_w, new_h), Image.LANCZOS)
        x_off = (W - new_w) // 2
        y_off = (H - new_h) // 2
        canvas.paste(filled, (x_off, y_off), filled)
    except Exception as exc:
        logger.warning(f"Story image load failed: {exc}")

    # Top overlay
    top_ovl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    _vertical_gradient(top_ovl, 0, STORY_HEADER_H + 40, (0, 0, 0, 210), (0, 0, 0, 0))
    canvas = Image.alpha_composite(canvas, top_ovl)

    # Bottom overlay
    bot_ovl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    _vertical_gradient(bot_ovl, H - STORY_FOOTER_H - 60, H, (0, 0, 0, 0), (0, 0, 0, 220))
    canvas = Image.alpha_composite(canvas, bot_ovl)

    draw = ImageDraw.Draw(canvas)

    # Top: OK logo + doctor name
    logo_f  = _font(34, bold=True)
    name_f  = _font(26)
    draw.rounded_rectangle([MARGIN - 8, 22, MARGIN + 52, 74], radius=8, fill=(*TEAL, 255))
    draw.text((MARGIN + 6, 24), "OK", font=logo_f, fill=(*BG, 255))
    draw.text((MARGIN + 72, 30), DOCTOR_NAME, font=name_f, fill=(*WHITE, 240))

    # Topic + hook centre-bottom
    tf   = _font(68, bold=True)
    hkf  = _font(32)
    tw   = topic.upper()
    tlw  = _text_width(draw, tw, tf)
    ty   = H - STORY_FOOTER_H - 80 - (80 if hook else 0)
    draw.text(((W - tlw) // 2, ty), tw, font=tf, fill=(*WHITE, 255))

    if hook:
        hkw = _text_width(draw, hook, hkf)
        draw.text(((W - hkw) // 2, ty + 82), hook, font=hkf, fill=(*TEAL, 220))

    # Bottom: website
    web_f = _font(28)
    ww    = _text_width(draw, f"🌐 {WEBSITE}", web_f)
    draw.text(((W - ww) // 2, H - 54), f"🌐 {WEBSITE}", font=web_f, fill=(*TEAL, 230))

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    final = canvas.convert("RGB")
    assert final.size == (W, H), f"Story canvas size mismatch: {final.size}"
    final.save(str(out), "JPEG", quality=93, optimize=True)
    logger.info(f"Story saved {W}x{H} → {output_path}")
