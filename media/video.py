"""
media/video.py  ·  v4
fl_image tabanlı overlay — güvenilir, uzun video desteği

Yaklaşım:
  1. Video/resim yükle
  2. 9:16 boyutuna getir
  3. fl_image ile her kareye PIL overlay uygula
     (header, footer, başlık, altyazı)
  4. MP4 olarak yaz
"""

import logging
import re
import textwrap
import glob
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

W, H           = 1080, 1920
FPS            = 24
MAX_DURATION   = 60
SLIDE_DURATION = 5.0
TITLE_SHOW_S   = 3.0

NAVY       = (23,  68, 124)
DARK       = (10,  26,  48)
LIGHT_BLUE = (68, 180, 231)
RED        = (225, 30,  59)
WHITE      = (255,255, 255)
BLACK      = (0,   0,   0)

DOCTOR_NAME = "Assoc. Prof. Dr. Özgür Karakoyun"
WEBSITE     = "www.ozgurkarakoyun.com"


# ── Font ──────────────────────────────────────────────────────────────────────
_fcache: dict = {}

def _font(size, bold=False):
    key = (size, bold)
    if key in _fcache:
        return _fcache[key]
    paths = (
        ["static/fonts/Bold.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
         "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]
        if bold else
        ["static/fonts/Regular.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
         "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]
    )
    paths += glob.glob("/usr/share/fonts/**/*.ttf", recursive=True)
    for p in paths:
        try:
            f = ImageFont.truetype(p, size)
            _fcache[key] = f
            return f
        except Exception:
            continue
    return ImageFont.load_default()

def _tw(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0]

def _cx(draw, text, font):
    return max(0, (W - _tw(draw, text, font)) // 2)


# ── Script → cümle listesi ────────────────────────────────────────────────────
def _split_script(script: str) -> list[str]:
    sentences = re.split(r'(?<=[.!?])\s+', script.strip())
    return [s.strip() for s in sentences if s.strip()]


# ── Sabit overlay'leri önceden render et ──────────────────────────────────────
def _render_header_footer() -> Image.Image:
    """Header + footer RGBA layer — her frame'e uygulanır."""
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d  = ImageDraw.Draw(ov)

    # Header arka plan
    ov.paste(Image.new("RGBA", (W, 160), (*NAVY, 185)), (0, 0))
    d = ImageDraw.Draw(ov)

    # Header accent çizgi
    for xi in range(W):
        t = xi / W
        r = int(RED[0] + (LIGHT_BLUE[0] - RED[0]) * t)
        g = int(RED[1] + (LIGHT_BLUE[1] - RED[1]) * t)
        b = int(RED[2] + (LIGHT_BLUE[2] - RED[2]) * t)
        d.line([(xi, 155), (xi, 160)], fill=(r, g, b, 255))

    # OK pill
    lf = _font(34, bold=True)
    lw = _tw(d, "OK", lf)
    d.rounded_rectangle([50, 18, 50+lw+20, 96], radius=10, fill=(*RED, 255))
    d.text((58, 22), "OK", font=lf, fill=(*WHITE, 255))

    # Doktor ismi
    nf = _font(26)
    nw = _tw(d, DOCTOR_NAME, nf)
    d.text((W-60-nw, 22), DOCTOR_NAME, font=nf, fill=(*WHITE, 240))
    sf  = _font(21)
    spec = "Orthopedics & Traumatology"
    d.text((W-60-_tw(d, spec, sf), 56), spec, font=sf, fill=(*LIGHT_BLUE, 210))

    # Footer arka plan
    ov.paste(Image.new("RGBA", (W, 100), (0, 0, 0, 205)), (0, H-100))
    d = ImageDraw.Draw(ov)
    for xi in range(W):
        t = xi / W
        r = int(RED[0] + (LIGHT_BLUE[0] - RED[0]) * t)
        g = int(RED[1] + (LIGHT_BLUE[1] - RED[1]) * t)
        b = int(RED[2] + (LIGHT_BLUE[2] - RED[2]) * t)
        d.line([(xi, H-102), (xi, H-98)], fill=(r, g, b, 255))

    wf = _font(26)
    wt = f"🌐  {WEBSITE}"
    d.text(((W-_tw(d, wt, wf))//2, H-68), wt, font=wf, fill=(*LIGHT_BLUE, 230))
    return ov


def _render_title_hook(topic: str, hook: str, alpha: int) -> Image.Image:
    """Başlık + hook RGBA layer."""
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if alpha <= 0:
        return ov
    d = ImageDraw.Draw(ov)

    tf     = _font(50, bold=True)
    hkf    = _font(38)
    LINE_H = 60

    t_lines = textwrap.fill(topic.upper(), width=18).split("\n")[:3]
    h_lines = textwrap.fill(hook, width=36).split("\n")[:2] if hook else []

    block_h = len(t_lines)*LINE_H + (len(h_lines)*46+12 if h_lines else 0)
    ty = (H - block_h) // 2

    for i, line in enumerate(t_lines):
        d.text((_cx(d, line, tf), ty+i*LINE_H), line,
               font=tf, fill=(*WHITE, alpha))

    if h_lines:
        hy = ty + len(t_lines)*LINE_H + 12
        max_hw = max(_tw(d, hl, hkf) for hl in h_lines)
        pad_x, pad_y = 24, 12
        rx  = (W-max_hw)//2 - pad_x
        ry  = hy - pad_y
        rx2 = rx + max_hw + pad_x*2
        ry2 = hy + len(h_lines)*46 + pad_y
        # Dikdörtgen
        bg_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(bg_layer).rounded_rectangle(
            [rx, ry, rx2, ry2], radius=10,
            fill=(255, 255, 255, int(77 * alpha / 255))
        )
        ov = Image.alpha_composite(ov, bg_layer)
        d  = ImageDraw.Draw(ov)
        for j, hl in enumerate(h_lines):
            d.text((_cx(d, hl, hkf), hy+j*46), hl,
                   font=hkf, fill=(*BLACK, alpha))
    return ov


def _render_subtitle(text: str) -> Image.Image:
    """Altyazı RGBA layer."""
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if not text:
        return ov
    d    = ImageDraw.Draw(ov)
    subf = _font(38)
    lines = textwrap.fill(text, width=34).split("\n")[:3]
    SUBH  = 48
    max_sw = max(_tw(d, sl, subf) for sl in lines)
    pad_x, pad_y = 28, 14
    sx  = (W-max_sw)//2 - pad_x
    sy  = H - 120 - len(lines)*SUBH - pad_y*2
    sx2 = sx + max_sw + pad_x*2
    sy2 = sy + len(lines)*SUBH + pad_y*2

    bg = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(bg).rounded_rectangle([sx, sy, sx2, sy2], radius=10, fill=(0,0,0,185))
    ov = Image.alpha_composite(ov, bg)
    d  = ImageDraw.Draw(ov)
    for k, sl in enumerate(lines):
        d.text((_cx(d, sl, subf), sy+pad_y+k*SUBH), sl,
               font=subf, fill=(*WHITE, 255))
    return ov


# ── Frame processor ───────────────────────────────────────────────────────────
def _make_frame_processor(topic, hook, sentences, total_dur):
    """
    fl_image için closure döndürür.
    Her frame'e (numpy RGB array) overlay uygular.
    """
    hf_overlay = _render_header_footer()      # sabit, önceden render
    sent_count  = len(sentences)
    title_start = 0.0
    title_end   = TITLE_SHOW_S + 0.5
    sub_start   = title_end
    sub_per     = (total_dur - sub_start) / max(sent_count, 1) if sent_count else 0

    def process(frame):
        # frame: numpy (H, W, 3) uint8
        img = Image.fromarray(frame, "RGB").convert("RGBA")

        # 1. Header + Footer
        img = Image.alpha_composite(img, hf_overlay)

        return np.array(img.convert("RGB"))

    def process_with_time(get_frame, t):
        frame = get_frame(t)
        img = Image.fromarray(frame, "RGB").convert("RGBA")

        # Header + footer
        img = Image.alpha_composite(img, hf_overlay)

        # Başlık + hook fade
        if t < title_end:
            if t < TITLE_SHOW_S:
                alpha = int(255 * min(1.0, t / 0.5))
            else:
                alpha = int(255 * (1 - (t - TITLE_SHOW_S) / 0.5))
            alpha = max(0, min(255, alpha))
            title_ov = _render_title_hook(topic, hook, alpha)
            img = Image.alpha_composite(img, title_ov)

        # Altyazı
        if sent_count > 0 and sub_per > 0 and t >= sub_start:
            idx = int((t - sub_start) / sub_per)
            idx = min(idx, sent_count - 1)
            sub_ov = _render_subtitle(sentences[idx])
            img = Image.alpha_composite(img, sub_ov)

        return np.array(img.convert("RGB"))

    return process_with_time


# ── 9:16 resize ───────────────────────────────────────────────────────────────
def _resize_to_916(clip):
    """Videoyu 9:16 boyutuna getir, aspect ratio koru, letterbox yok — crop."""
    from moviepy.editor import ColorClip, CompositeVideoClip

    src_aspect = clip.w / clip.h
    tgt_aspect = W / H

    if abs(src_aspect - tgt_aspect) < 0.01:
        return clip.resize((W, H))
    elif src_aspect > tgt_aspect:
        # Yatay video — yüksekliğe göre scale, yanlara crop
        new_h = H
        new_w = int(H * src_aspect)
    else:
        # Dikey video — genişliğe göre scale
        new_w = W
        new_h = int(W / src_aspect)

    resized = clip.resize((new_w, new_h))
    x_center = (new_w - W) // 2
    y_center = (new_h - H) // 2
    return resized.crop(x1=x_center, y1=y_center, x2=x_center+W, y2=y_center+H)


# ══════════════════════════════════════════════════════════════════════════════
# ANA FONKSİYON
# ══════════════════════════════════════════════════════════════════════════════
def build_reel_preview(
    input_path: str,
    output_path: str,
    topic: str,
    hook: str = "",
    script: str = "",
) -> dict:
    try:
        from moviepy.editor import VideoFileClip
    except ImportError:
        logger.warning("MoviePy yok — fallback.")
        return _build_static_fallback(input_path, output_path, topic, hook)

    ext      = Path(input_path).suffix.lower()
    is_video = ext in {".mp4", ".mov", ".avi", ".mkv", ".m4v"}

    try:
        if is_video:
            return _process_video(input_path, output_path, topic, hook, script)
        else:
            return _process_image(input_path, output_path, topic, hook, script)
    except Exception as exc:
        logger.error(f"Reel hatası: {exc}", exc_info=True)
        return _build_static_fallback(input_path, output_path, topic, hook)


def _process_video(input_path, output_path, topic, hook, script):
    from moviepy.editor import VideoFileClip

    logger.info(f"Video işleniyor: {input_path}")
    clip = VideoFileClip(input_path, audio=True)
    duration = min(clip.duration, MAX_DURATION)
    clip = clip.subclip(0, duration)

    # 9:16
    clip = _resize_to_916(clip)

    sentences  = _split_script(script) if script else []
    processor  = _make_frame_processor(topic, hook, sentences, duration)

    final = clip.fl(processor, apply_to=["mask", "video"] if clip.mask else ["video"])
    _write(final, output_path)
    clip.close()
    return {"type": "video", "path": output_path, "fallback": False}


def _process_image(input_path, output_path, topic, hook, script):
    from moviepy.editor import ImageClip

    logger.info(f"Resim → slideshow: {input_path}")
    img = Image.open(input_path).convert("RGB").resize((W, H), Image.LANCZOS)
    arr = np.array(img)

    duration  = SLIDE_DURATION
    sentences = _split_script(script) if script else []
    processor = _make_frame_processor(topic, hook, sentences, duration)

    clip  = ImageClip(arr, duration=duration)
    final = clip.fl(processor)
    _write(final, output_path)
    return {"type": "video", "path": output_path, "fallback": False}


def _write(clip, output_path):
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    clip.write_videofile(
        str(out),
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        preset="ultrafast",
        threads=2,
        logger=None,
    )
    if not out.exists():
        raise FileNotFoundError(f"Video üretilmedi: {out}")
    logger.info(f"Reel {W}x{H} → {output_path} ({out.stat().st_size//1024} KB)")


def _build_static_fallback(input_path, output_path, topic, hook):
    from media.template import build_image_post
    jpg = str(Path(output_path).with_suffix("")) + "_preview.jpg"
    build_image_post(input_path=input_path, output_path=jpg, topic=topic, hook=hook)
    logger.info(f"Fallback JPEG → {jpg}")
    return {"type": "image_fallback", "path": jpg, "fallback": True}
