"""
media/template.py  ·  v7
CVS Health Hub Palette + Gradient

  LIGHT_BLUE  #44B4E7  — açık mavi (hook, aksan, link)
  NAVY        #17447C  — lacivert (gradient sol, header)
  RED         #E11E3B  — kırmızı (çizgiler, pill, vurgu)
  WHITE       #FFFFFF  — ana metin
  DARK        #0A1A30  — gradient sağ (navy'den koyu)

Gradient stratejisi:
  Canvas BG  : Lacivert (#17447C) sol → Koyu (#0A1A30) sağ
  Accent hat : Kırmızı (#E11E3B) sol → Açık Mavi (#44B4E7) sağ
  Overlay    : şeffaf lacivert tint
"""

import logging, textwrap, glob
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from media.logo import load_logo

logger = logging.getLogger(__name__)

W, H      = 1080, 1920
MARGIN    = 64
HEADER_H  = 280
FOOTER_H  = 300
IMG_TOP   = HEADER_H
IMG_H     = H - HEADER_H - FOOTER_H
IMG_BOT   = IMG_TOP + IMG_H

# ── Palette ───────────────────────────────────────────────────────────────────
LIGHT_BLUE = (68,  180, 231)   # #44B4E7
NAVY       = (23,   68, 124)   # #17447C
RED        = (225,  30,  59)   # #E11E3B
WHITE      = (255, 255, 255)   # #FFFFFF
DARK       = (10,   26,  48)   # #0A1A30  (gradient sonu)
SUBTEXT    = (160, 200, 230)   # açık mavi-gri

FOOTER_BG  = (8, 18, 36, 228)
HEADER_BG  = (23, 68, 124, 40)

DOCTOR_NAME = "Assoc. Prof. Dr. Özgür Karakoyun"
PHONE       = "+90 545 919 54 13"
WEBSITE     = "www.ozgurkarakoyun.com"
EMAIL       = "info@ozgurkarakoyun.com"


# ── Font ──────────────────────────────────────────────────────────────────────
_cache: dict = {}
def _font(size, bold=False):
    key = (size, bold)
    if key in _cache: return _cache[key]
    paths = (["static/fonts/Bold.ttf",
               "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
               "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]
              if bold else
              ["static/fonts/Regular.ttf",
               "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
               "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"])
    paths += glob.glob("/usr/share/fonts/**/*.ttf", recursive=True)
    for p in paths:
        try:
            f = ImageFont.truetype(p, size)
            _cache[key] = f; return f
        except Exception: continue
    return ImageFont.load_default()


# ── Yardımcılar ───────────────────────────────────────────────────────────────
def _tw(draw, text, font):
    bb = draw.textbbox((0,0), text, font=font)
    return bb[2] - bb[0]

def _cx(draw, text, font):
    return max(0, (W - _tw(draw, text, font)) // 2)

def _semi(canvas, x0, y0, x1, y1, color):
    layer = Image.new("RGBA", (W,H), (0,0,0,0))
    layer.paste(Image.new("RGBA", (x1-x0,y1-y0), color), (x0,y0))
    return Image.alpha_composite(canvas, layer)

def _vgrad(canvas, y0, y1, c0, c1):
    """Dikey gradient şerit."""
    draw = ImageDraw.Draw(canvas)
    span = max(1, y1-y0)
    for i in range(span):
        t = i/span
        rgba = tuple(int(c0[j]+(c1[j]-c0[j])*t) for j in range(4))
        draw.line([(0,y0+i),(W,y0+i)], fill=rgba)

def _hgrad_canvas(canvas, c_left, c_right):
    """Yatay gradient — tüm canvas sol→sağ."""
    draw = ImageDraw.Draw(canvas)
    for xi in range(W):
        t = xi/W
        r = int(c_left[0]+(c_right[0]-c_left[0])*t)
        g = int(c_left[1]+(c_right[1]-c_left[1])*t)
        b = int(c_left[2]+(c_right[2]-c_left[2])*t)
        draw.line([(xi,0),(xi,H)], fill=(r,g,b,255))

def _accent_line(draw, y, thickness=5):
    """Kırmızı → Açık Mavi gradient accent çizgisi."""
    for xi in range(W):
        t = xi/W
        r = int(RED[0]+(LIGHT_BLUE[0]-RED[0])*t)
        g = int(RED[1]+(LIGHT_BLUE[1]-RED[1])*t)
        b = int(RED[2]+(LIGHT_BLUE[2]-RED[2])*t)
        draw.line([(xi,y),(xi,y+thickness)], fill=(r,g,b,255))

def _fit_into(img, bw, bh):
    """
    Resmi header-footer arası alana TAMAMEN doldur — piksel boşluğu yok.
    """
    img = img.convert("RGB").convert("RGBA")
    resized = img.resize((bw, bh), Image.LANCZOS)
    # Tüm pikseller opak olsun
    r, g, b, a = resized.split()
    a = a.point(lambda x: 255)
    return Image.merge("RGBA", (r, g, b, a))

def _logo_or_pill(canvas, draw, x, y, pill_h=108, logo_h=96):
    logo = load_logo(target_h=logo_h)
    if logo is not None:
        canvas.paste(logo, (x,y), logo)
        return x + logo.width + 20
    lf = _font(int(pill_h*0.40), bold=True)
    lw = _tw(draw, "OK", lf)
    # Kırmızı pill, beyaz yazı
    draw.rounded_rectangle([x-10,y-6,x+lw+18,y+pill_h-12],
                            radius=12, fill=(*RED,255))
    draw.text((x+4, y+4), "OK", font=lf, fill=(*WHITE,255))
    return x + lw + 32


# ══════════════════════════════════════════════════════════════════════════════
# POST
# ══════════════════════════════════════════════════════════════════════════════
def build_image_post(input_path, output_path, topic, hook=""):
    canvas = Image.new("RGBA", (W,H), (*NAVY,255))

    # ── Arka plan: Lacivert sol → Koyu sağ ───────────────────────────────────
    _hgrad_canvas(canvas, NAVY, DARK)

    # ── Dekoratif elementler ──────────────────────────────────────────────────
    dec = Image.new("RGBA", (W,H), (0,0,0,0))
    d2  = ImageDraw.Draw(dec)
    # Sol üst büyük arc — açık mavi
    d2.ellipse([-260,-260,440,440], outline=(*LIGHT_BLUE,18), width=100)
    # Sağ alt küçük arc — kırmızı
    d2.ellipse([W-200,H-200,W+400,H+400], outline=(*RED,14), width=60)
    # Sol kenar ince şerit — lacivert/mavi
    d2.rectangle([0,0,6,H], fill=(*LIGHT_BLUE,60))
    canvas = Image.alpha_composite(canvas, dec)

    # Header lacivert tint
    canvas = _semi(canvas, 0, 0, W, HEADER_H, HEADER_BG)
    draw = ImageDraw.Draw(canvas)

    # Header alt accent çizgisi: Kırmızı → Açık Mavi
    _accent_line(draw, HEADER_H-5, thickness=5)

    # ── Kullanıcı görseli ─────────────────────────────────────────────────────
    try:
        user_img = Image.open(input_path).convert("RGBA")
        fitted   = _fit_into(user_img, W, IMG_H)
        canvas.paste(fitted.convert('RGB'), (0,IMG_TOP))  # tam opak, maske yok
    except Exception as exc:
        logger.error(f"Görsel: {exc}")
        canvas.paste(Image.new("RGBA",(W,IMG_H),(10,20,40,255)), (0,IMG_TOP))

    # Görsel: header-footer arası tam dolu, fade yok

    # Footer overlay
    canvas = _semi(canvas, 0, IMG_BOT, W, H, FOOTER_BG)
    draw = ImageDraw.Draw(canvas)

    # Footer üst accent çizgisi: Kırmızı → Açık Mavi
    _accent_line(draw, IMG_BOT, thickness=5)

    # ── HEADER İçeriği ────────────────────────────────────────────────────────
    next_x = _logo_or_pill(canvas, draw, MARGIN, 34, pill_h=108, logo_h=96)
    draw = ImageDraw.Draw(canvas)

    nf = _font(36)
    nw = _tw(draw, DOCTOR_NAME, nf)
    draw.text((W-MARGIN-nw, 36), DOCTOR_NAME, font=nf, fill=(*WHITE,248))

    sf = _font(28)
    spec = "Orthopedics & Traumatology"
    draw.text((W-MARGIN-_tw(draw,spec,sf), 86), spec, font=sf, fill=(*LIGHT_BLUE,215))

    # ── Başlık + Hook ─────────────────────────────────────────────────────────
    title_f = _font(50, bold=True)
    hook_f  = _font(42)

    t_lines  = textwrap.fill(topic.upper(), width=14).split("\n")[:3]
    LINE_H   = 58
    h_lines  = textwrap.fill(hook, width=38).split("\n")[:2] if hook else []
    HOOK_H   = 56
    SAFE_GAP = 95

    block_h = len(t_lines)*LINE_H + (len(h_lines)*HOOK_H+20 if h_lines else 0)
    title_y = max(IMG_TOP+60, IMG_BOT - SAFE_GAP - block_h)

    for i, line in enumerate(t_lines):
        draw.text((_cx(draw,line,title_f), title_y+i*LINE_H),
                  line, font=title_f, fill=(*WHITE,255))

    if h_lines:
        hy = title_y + len(t_lines)*LINE_H + 16
        # Hook bloğunun toplam yüksekliğini hesapla
        hook_block_h = len(h_lines) * HOOK_H
        max_hw = max(_tw(draw, hl, hook_f) for hl in h_lines)
        pad_x, pad_y = 28, 14
        rect_x = (W - max_hw) // 2 - pad_x
        rect_y = hy - pad_y
        rect_x2 = rect_x + max_hw + pad_x * 2
        rect_y2 = hy + hook_block_h + pad_y
        # %30 transparan beyaz dikdörtgen
        hook_bg = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(hook_bg).rounded_rectangle(
            [rect_x, rect_y, rect_x2, rect_y2],
            radius=10, fill=(255, 255, 255, 77)  # 77 = %30 opacity
        )
        canvas = Image.alpha_composite(canvas, hook_bg)
        draw = ImageDraw.Draw(canvas)
        for j, hl in enumerate(h_lines):
            draw.text((_cx(draw, hl, hook_f), hy + j * HOOK_H),
                      hl, font=hook_f, fill=(0, 0, 0, 255))  # siyah

    # ── FOOTER — 3 satır, üst üste gelmiyor ──────────────────────────────────
    fy  = IMG_BOT + 18
    fnf = _font(42, bold=True)
    fdf = _font(30)
    disf= _font(24)

    # Satır 1: İsim ortada
    draw.text(((W-_tw(draw,DOCTOR_NAME,fnf))//2, fy),
              DOCTOR_NAME, font=fnf, fill=(*WHITE,255))

    # İnce açık mavi ayraç çizgisi
    fy_line = fy + 54
    draw.rectangle([MARGIN, fy_line, W-MARGIN, fy_line+1],
                   fill=(*LIGHT_BLUE, 70))

    # Satır 2: Tel sol | Web sağ
    fy2 = fy_line + 14
    draw.text((MARGIN, fy2), f"📞  {PHONE}", font=fdf, fill=(*WHITE,235))
    web_t = f"🌐  {WEBSITE}"
    draw.text((W-MARGIN-_tw(draw,web_t,fdf), fy2),
              web_t, font=fdf, fill=(*LIGHT_BLUE,235))

    # Satır 3: Email ortada
    fy3 = fy2 + 48
    em_t = f"✉   {EMAIL}"
    draw.text(((W-_tw(draw,em_t,fdf))//2, fy3),
              em_t, font=fdf, fill=(*SUBTEXT,210))

    # Disclaimer
    dis = "⚕  Medical information only. Consult your doctor."
    draw.text(((W-_tw(draw,dis,disf))//2, H-32),
              dis, font=disf, fill=(100,140,180,185))

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(str(out), "JPEG", quality=94, optimize=True)
    logger.info(f"Post {W}x{H} → {output_path}")


# ══════════════════════════════════════════════════════════════════════════════
# STORY
# ══════════════════════════════════════════════════════════════════════════════
def build_story_post(input_path, output_path, topic, hook=""):
    canvas = Image.new("RGBA", (W,H), (*NAVY,255))
    _hgrad_canvas(canvas, NAVY, DARK)

    # Görsel: header-footer arası tam dolu
    STORY_HEADER_H = 170   # accent çizgi + logo alanı
    STORY_FOOTER_H = 80    # website alanı
    IMG_ZONE_TOP   = STORY_HEADER_H
    IMG_ZONE_H     = H - STORY_HEADER_H - STORY_FOOTER_H
    try:
        user_img = Image.open(input_path).convert("RGB")
        fitted   = user_img.resize((W, IMG_ZONE_H), Image.LANCZOS)
        canvas.paste(fitted, (0, IMG_ZONE_TOP))
    except Exception as exc:
        logger.warning(f"Story görsel: {exc}")
        canvas.paste(Image.new("RGB",(W,IMG_ZONE_H),(10,20,40)), (0,IMG_ZONE_TOP))

    # Sadece üst ve alt metin okunabilirliği için hafif overlay
    _vgrad(canvas, 0,               STORY_HEADER_H+40, (10,26,48,220), (0,0,0,0))
    _vgrad(canvas, H-STORY_FOOTER_H-60, H,             (0,0,0,0),      (10,26,48,230))

    # Sol/sağ kenar şeritler
    dec = Image.new("RGBA",(W,H),(0,0,0,0))
    ImageDraw.Draw(dec).rectangle([0,0,6,H], fill=(*RED,180))
    ImageDraw.Draw(dec).rectangle([W-6,0,W,H], fill=(*LIGHT_BLUE,120))
    canvas = Image.alpha_composite(canvas, dec)

    draw = ImageDraw.Draw(canvas)
    _accent_line(draw, 155, thickness=4)

    # Logo / pill + isim
    next_x = _logo_or_pill(canvas, draw, MARGIN, 28, pill_h=96, logo_h=86)
    draw = ImageDraw.Draw(canvas)
    draw.text((next_x, 40), DOCTOR_NAME, font=_font(32), fill=(*WHITE,240))

    # Başlık + Hook
    tf      = _font(50, bold=True)
    hkf     = _font(42)
    t_lines = textwrap.fill(topic.upper(), width=14).split("\n")[:3]
    LINE_H  = 58
    h_lines = textwrap.fill(hook, width=36).split("\n")[:2] if hook else []
    HOOK_H  = 58

    block_h = len(t_lines)*LINE_H + (len(h_lines)*HOOK_H+18 if h_lines else 0)
    ty = H - 180 - block_h

    for i, line in enumerate(t_lines):
        draw.text((_cx(draw,line,tf), ty+i*LINE_H), line, font=tf, fill=(*WHITE,255))

    if h_lines:
        hy = ty + len(t_lines)*LINE_H + 14
        hook_block_h = len(h_lines) * HOOK_H
        max_hw = max(_tw(draw, hl, hkf) for hl in h_lines)
        pad_x, pad_y = 28, 14
        rect_x  = (W - max_hw) // 2 - pad_x
        rect_y  = hy - pad_y
        rect_x2 = rect_x + max_hw + pad_x * 2
        rect_y2 = hy + hook_block_h + pad_y
        hook_bg = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(hook_bg).rounded_rectangle(
            [rect_x, rect_y, rect_x2, rect_y2],
            radius=10, fill=(255, 255, 255, 77)
        )
        canvas = Image.alpha_composite(canvas, hook_bg)
        draw = ImageDraw.Draw(canvas)
        for j, hl in enumerate(h_lines):
            draw.text((_cx(draw, hl, hkf), hy + j * HOOK_H),
                      hl, font=hkf, fill=(0, 0, 0, 255))

    wf = _font(32)
    wt = f"🌐  {WEBSITE}"
    draw.text(((W-_tw(draw,wt,wf))//2, H-52), wt, font=wf, fill=(*LIGHT_BLUE,230))

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(str(out), "JPEG", quality=94, optimize=True)
    logger.info(f"Story {W}x{H} → {output_path}")
