"""
media/video.py  ·  v3
Gerçek MP4 Reels üretimi — MoviePy + PIL tabanlı overlay

Desteklenen input:
  • Video  (MP4/MOV/AVI) → 9:16'ya resize, overlay ekle
  • Resim  (JPG/PNG)     → slideshow, her resim 4 sn, Ken Burns efekti

Overlay sistemi:
  • Header  : Logo/isim sabit
  • Başlık + Hook : İlk 3 saniye fade-in
  • Script altyazı: Cümle cümle, zamanlı
  • Footer  : Website sabit

PIL text rendering kullanır → ImageMagick gerekmez.
"""

import logging
import os
import textwrap
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

logger = logging.getLogger(__name__)

# ── Sabitler ──────────────────────────────────────────────────────────────────
W, H           = 1080, 1920
FPS            = 24
MAX_DURATION   = 60     # saniye
SLIDE_DURATION = 4.0    # resim başına saniye
TITLE_SHOW_S   = 3.0    # başlık gösterim süresi

# ── Renk Paleti ───────────────────────────────────────────────────────────────
NAVY       = (23,  68, 124)
DARK       = (10,  26,  48)
LIGHT_BLUE = (68, 180, 231)
RED        = (225, 30,  59)
WHITE      = (255,255, 255)
BLACK      = (0,   0,   0)

DOCTOR_NAME = "Assoc. Prof. Dr. Özgür Karakoyun"
WEBSITE     = "www.ozgurkarakoyun.com"

# ── Font ──────────────────────────────────────────────────────────────────────
import glob as _glob
_fcache: dict = {}

def _font(size, bold=False):
    key = (size, bold)
    if key in _fcache: return _fcache[key]
    paths = (["static/fonts/Bold.ttf",
               "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
               "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]
              if bold else
              ["static/fonts/Regular.ttf",
               "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
               "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"])
    paths += _glob.glob("/usr/share/fonts/**/*.ttf", recursive=True)
    for p in paths:
        try:
            f = ImageFont.truetype(p, size); _fcache[key] = f; return f
        except: continue
    return ImageFont.load_default()

def _tw(draw, text, font):
    bb = draw.textbbox((0,0), text, font=font)
    return bb[2]-bb[0]

def _cx(draw, text, font):
    return max(0, (W-_tw(draw,text,font))//2)


# ── Script → cümle listesi ────────────────────────────────────────────────────
def _split_script(script: str, n_slides: int = 1) -> list[str]:
    """Script'i cümlelere böl, her slide'a dağıt."""
    import re
    sentences = re.split(r'(?<=[.!?])\s+', script.strip())
    sentences = [s.strip() for s in sentences if s.strip()]
    return sentences


# ── Frame üretici: branded overlay ───────────────────────────────────────────
def _make_overlay(
    topic: str,
    hook: str,
    subtitle: str = "",
    show_title: bool = True,
    title_alpha: int = 255,
) -> np.ndarray:
    """
    Şeffaf RGBA overlay frame üretir (PIL → numpy).
    Canvas: W x H, RGBA.
    """
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw    = ImageDraw.Draw(overlay)

    # ── Header (sabit) ────────────────────────────────────────────────────────
    # Header arka plan
    header_bg = Image.new("RGBA", (W, 160), (*NAVY, 180))
    overlay.paste(header_bg, (0, 0), header_bg)

    # Accent çizgi
    for xi in range(W):
        t = xi/W
        r = int(RED[0]+(LIGHT_BLUE[0]-RED[0])*t)
        g = int(RED[1]+(LIGHT_BLUE[1]-RED[1])*t)
        b = int(RED[2]+(LIGHT_BLUE[2]-RED[2])*t)
        draw.line([(xi,155),(xi,160)], fill=(r,g,b,255))

    # Logo pill
    lf = _font(36, bold=True)
    lw = _tw(draw, "OK", lf)
    draw.rounded_rectangle([50,18,50+lw+20,100], radius=10, fill=(*RED,255))
    draw.text((58, 22), "OK", font=lf, fill=(*WHITE,255))

    # Doktor ismi
    nf  = _font(28)
    nw  = _tw(draw, DOCTOR_NAME, nf)
    draw.text((W-60-nw, 22), DOCTOR_NAME, font=nf, fill=(*WHITE,240))

    # Uzmanlık
    sf  = _font(22)
    spec = "Orthopedics & Traumatology"
    draw.text((W-60-_tw(draw,spec,sf), 60), spec, font=sf, fill=(*LIGHT_BLUE,210))

    # ── Footer (sabit) ────────────────────────────────────────────────────────
    foot_bg = Image.new("RGBA", (W, 100), (0, 0, 0, 200))
    overlay.paste(foot_bg, (0, H-100), foot_bg)
    for xi in range(W):
        t = xi/W
        r = int(RED[0]+(LIGHT_BLUE[0]-RED[0])*t)
        g = int(RED[1]+(LIGHT_BLUE[1]-RED[1])*t)
        b = int(RED[2]+(LIGHT_BLUE[2]-RED[2])*t)
        draw.line([(xi,H-102),(xi,H-98)], fill=(r,g,b,255))

    wf = _font(28)
    wt = f"🌐  {WEBSITE}"
    draw.text(((W-_tw(draw,wt,wf))//2, H-72), wt, font=wf, fill=(*LIGHT_BLUE,230))

    # ── Başlık + Hook (fade-in) ───────────────────────────────────────────────
    if show_title and title_alpha > 0:
        tf  = _font(50, bold=True)
        hkf = _font(38)

        t_lines = textwrap.fill(topic.upper(), width=18).split("\n")[:3]
        LINE_H  = 60
        h_lines = textwrap.fill(hook, width=36).split("\n")[:2] if hook else []

        block_h = len(t_lines)*LINE_H + (len(h_lines)*46+12 if h_lines else 0)
        ty = (H - block_h) // 2

        for i, line in enumerate(t_lines):
            lx = _cx(draw, line, tf)
            draw.text((lx, ty+i*LINE_H), line, font=tf,
                      fill=(*WHITE, title_alpha))

        if h_lines:
            hy = ty + len(t_lines)*LINE_H + 12
            max_hw = max(_tw(draw,hl,hkf) for hl in h_lines)
            pad_x, pad_y = 24, 12
            rx  = (W-max_hw)//2 - pad_x
            ry  = hy - pad_y
            rx2 = rx + max_hw + pad_x*2
            ry2 = hy + len(h_lines)*46 + pad_y
            hook_bg = Image.new("RGBA",(W,H),(0,0,0,0))
            ImageDraw.Draw(hook_bg).rounded_rectangle(
                [rx,ry,rx2,ry2], radius=10,
                fill=(255,255,255,int(77*title_alpha/255)))
            overlay = Image.alpha_composite(overlay, hook_bg)
            draw    = ImageDraw.Draw(overlay)
            for j, hl in enumerate(h_lines):
                draw.text((_cx(draw,hl,hkf), hy+j*46), hl, font=hkf,
                          fill=(*BLACK, title_alpha))

    # ── Altyazı ───────────────────────────────────────────────────────────────
    if subtitle:
        subf    = _font(40)
        sub_lines = textwrap.fill(subtitle, width=34).split("\n")[:3]
        SUBH    = 50
        max_sw  = max(_tw(draw,sl,subf) for sl in sub_lines)
        pad_x, pad_y = 30, 16
        sx  = (W-max_sw)//2 - pad_x
        sy  = H - 120 - len(sub_lines)*SUBH - pad_y*2
        sx2 = sx + max_sw + pad_x*2
        sy2 = sy + len(sub_lines)*SUBH + pad_y*2

        sub_bg = Image.new("RGBA",(W,H),(0,0,0,0))
        ImageDraw.Draw(sub_bg).rounded_rectangle(
            [sx,sy,sx2,sy2], radius=10, fill=(0,0,0,180))
        overlay = Image.alpha_composite(overlay, sub_bg)
        draw    = ImageDraw.Draw(overlay)
        for k, sl in enumerate(sub_lines):
            draw.text((_cx(draw,sl,subf), sy+pad_y+k*SUBH), sl,
                      font=subf, fill=(*WHITE,255))

    return np.array(overlay)


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
    """
    Gerçek MP4 Reels üretir.
    Hem video hem de resim input'u destekler.
    """
    try:
        from moviepy.editor import VideoFileClip
        _has_moviepy = True
    except ImportError:
        _has_moviepy = False

    if not _has_moviepy:
        logger.warning("MoviePy yok — fallback JPEG.")
        return _build_static_fallback(input_path, output_path, topic, hook)

    ext = Path(input_path).suffix.lower()
    is_video = ext in {".mp4", ".mov", ".avi", ".mkv", ".m4v"}

    try:
        if is_video:
            return _build_from_video(input_path, output_path, topic, hook, script)
        else:
            return _build_from_image(input_path, output_path, topic, hook, script)
    except Exception as exc:
        logger.error(f"Reel build failed: {exc}")
        return _build_static_fallback(input_path, output_path, topic, hook)


# ── Video input ───────────────────────────────────────────────────────────────
def _build_from_video(input_path, output_path, topic, hook, script):
    from moviepy.editor import VideoFileClip, CompositeVideoClip, ImageClip

    logger.info(f"Video reel: {input_path}")
    clip = VideoFileClip(input_path)
    duration = min(clip.duration, MAX_DURATION)
    clip = clip.subclip(0, duration)

    # 9:16'ya resize
    src_aspect = clip.w / clip.h
    tgt_aspect = W / H
    if src_aspect > tgt_aspect:
        new_w, new_h = W, int(W/src_aspect)
    else:
        new_h, new_w = H, int(H*src_aspect)

    clip = clip.resize((new_w, new_h))
    # Siyah arka plan üzerine ortala
    from moviepy.editor import ColorClip
    bg = ColorClip((W,H), color=DARK, duration=duration)
    clip = clip.set_position(("center","center"))

    sentences  = _split_script(script) if script else []
    sub_layers = _make_subtitle_clips(sentences, duration)
    overlay_layer = _make_title_overlay_clip(topic, hook, duration)

    layers = [bg, clip, overlay_layer] + sub_layers
    final  = CompositeVideoClip(layers, size=(W,H))
    _write_video(final, output_path)
    clip.close()
    return {"type":"video","path":output_path,"fallback":False}


# ── Resim → Slideshow ─────────────────────────────────────────────────────────
def _build_from_image(input_path, output_path, topic, hook, script):
    from moviepy.editor import ImageClip, CompositeVideoClip, concatenate_videoclips

    logger.info(f"Slideshow reel: {input_path}")

    img    = Image.open(input_path).convert("RGB")
    img_9  = img.resize((W, H), Image.LANCZOS)
    frames = [img_9]   # Tek resim şimdilik; çoklu resim için liste genişletilebilir

    sentences    = _split_script(script) if script else []
    sub_dur      = SLIDE_DURATION
    total_dur    = len(frames) * SLIDE_DURATION

    slide_clips = []
    for i, frame in enumerate(frames):
        arr  = np.array(frame.convert("RGB"))
        clip = ImageClip(arr, duration=SLIDE_DURATION)
        # Hafif Ken Burns: yavaş zoom
        clip = clip.resize(lambda t: 1 + 0.03*(t/SLIDE_DURATION))
        clip = clip.set_position("center")
        slide_clips.append(clip)

    from moviepy.editor import CompositeVideoClip, ColorClip
    bg       = ColorClip((W,H), color=DARK, duration=total_dur)
    main     = concatenate_videoclips(slide_clips).set_position("center")
    ov       = _make_title_overlay_clip(topic, hook, total_dur)
    sub_lays = _make_subtitle_clips(sentences, total_dur)

    layers = [bg, main, ov] + sub_lays
    final  = CompositeVideoClip(layers, size=(W,H))
    _write_video(final, output_path)
    return {"type":"video","path":output_path,"fallback":False}


# ── Overlay clip (başlık + hook, ilk 3 sn) ───────────────────────────────────
def _make_title_overlay_clip(topic, hook, duration):
    from moviepy.editor import VideoClip

    def make_frame(t):
        if t < TITLE_SHOW_S:
            alpha = int(255 * min(1.0, t/0.5))          # 0.5sn fade-in
        elif t < TITLE_SHOW_S + 0.5:
            alpha = int(255 * (1 - (t-TITLE_SHOW_S)/0.5))  # fade-out
        else:
            alpha = 0

        show_title = alpha > 0
        frame_rgba = _make_overlay(topic, hook, subtitle="",
                                   show_title=show_title, title_alpha=alpha)
        # RGBA → RGB (moviepy RGB bekler)
        frame_pil = Image.fromarray(frame_rgba, "RGBA")
        bg_pil    = Image.new("RGB", (W, H), DARK)
        bg_pil.paste(frame_pil, mask=frame_pil.split()[3])
        return np.array(bg_pil)

    # Sadece header+footer sabit overlay
    def make_static_frame(t):
        frame_rgba = _make_overlay(topic, hook, subtitle="",
                                   show_title=(t < TITLE_SHOW_S + 0.5),
                                   title_alpha=max(0, int(255*(1 - max(0,t-TITLE_SHOW_S)/0.5))))
        pil = Image.fromarray(frame_rgba, "RGBA")
        out = Image.new("RGBA", (W,H), (0,0,0,0))
        out.paste(pil, mask=pil.split()[3])
        return np.array(out.convert("RGBA"))

    from moviepy.editor import ImageClip
    # Sabit header/footer overlay (her frame için static)
    # Header+footer sabit overlay — her frame'e eklenir
    # Subtitle ve title clip'leri ayrı; burada sadece header/footer
    static_rgba = _make_overlay(topic, hook, subtitle="", show_title=False)
    static_pil  = Image.fromarray(static_rgba, "RGBA")
    # RGBA → RGB (siyah bg üzerine composite)
    bg_pil = Image.new("RGB", (W, H), (0,0,0))
    bg_pil.paste(static_pil, mask=static_pil.split()[3])
    static_clip = ImageClip(np.array(bg_pil), duration=duration, ismask=False)
    static_clip = static_clip.set_opacity(0.0)   # header/footer subtitle clip'te var
    return static_clip


# ── Subtitle clips ────────────────────────────────────────────────────────────
def _make_subtitle_clips(sentences: list[str], total_dur: float) -> list:
    from moviepy.editor import ImageClip

    if not sentences:
        return []

    layers    = []
    per_sent  = total_dur / max(len(sentences), 1)
    start_t   = TITLE_SHOW_S + 0.5   # başlık bittikten sonra başla

    for i, sent in enumerate(sentences):
        t_start = start_t + i * per_sent
        t_end   = min(t_start + per_sent - 0.2, total_dur)
        if t_start >= total_dur:
            break

        # PIL ile altyazı frame'i
        frame_rgba = _make_overlay("", "", subtitle=sent,
                                   show_title=False, title_alpha=0)
        pil = Image.fromarray(frame_rgba, "RGBA")

        # RGBA PIL → composite üzerine RGB
        bg_sub = Image.new("RGB", (W, H), (0,0,0))
        bg_sub.paste(pil, mask=pil.split()[3])
        clip = (
            ImageClip(np.array(bg_sub), ismask=False)
            .set_start(t_start)
            .set_end(t_end)
            .set_opacity(0.92)
        )
        layers.append(clip)

    return layers


# ── Video yazma ───────────────────────────────────────────────────────────────
def _write_video(clip, output_path):
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    clip.write_videofile(
        str(out),
        fps=FPS,
        codec="libx264",
        audio=False,
        preset="ultrafast",
        threads=2,
        logger=None,
    )
    if not out.exists():
        raise FileNotFoundError(f"Video üretilmedi: {out}")
    logger.info(f"Reel {W}x{H} → {output_path}")


# ── Fallback ──────────────────────────────────────────────────────────────────
def _build_static_fallback(input_path, output_path, topic, hook):
    from media.template import build_image_post
    jpg_path = str(Path(output_path).with_suffix("")) + "_preview.jpg"
    build_image_post(input_path=input_path, output_path=jpg_path,
                     topic=topic, hook=hook)
    logger.info(f"Fallback → {jpg_path}")
    return {"type":"image_fallback","path":jpg_path,"fallback":True}
