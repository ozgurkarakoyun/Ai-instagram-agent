"""
media/video.py  ·  v2.1
Production reel preview: 9:16 guarantee, subtitle overlay, duration cap.

Fallback behaviour (no MoviePy/ffmpeg):
  - Generates a branded JPEG still
  - Saves it as output/reel_<id>_preview.jpg
  - Does NOT produce a fake .mp4 file
  - Returns a dict so main.py can put fallback_image in the response
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

TARGET_W, TARGET_H = 1080, 1920
HEADER_H           = 200
FOOTER_H           = 200
MAX_DURATION_S     = 30


def build_reel_preview(
    input_path: str,
    output_path: str,          # expected: output/reel_<id>.mp4
    topic: str,
    hook: str = "",
    script: str = "",
) -> dict:
    """
    Build a 9:16 reel preview.

    Returns
    -------
    dict with keys:
      "type"           : "video" | "image_fallback"
      "path"           : actual output path
      "fallback"       : bool
    """
    try:
        import moviepy  # noqa: F401
        _build_with_moviepy(input_path, output_path, topic, hook, script)
        return {"type": "video", "path": output_path, "fallback": False}
    except ImportError:
        logger.warning("MoviePy not installed — using static image fallback.")
    except Exception as exc:
        logger.error(f"MoviePy failed ({exc}) — using static image fallback.")

    return _build_static_fallback(input_path, output_path, topic, hook)


def _build_with_moviepy(
    input_path: str,
    output_path: str,
    topic: str,
    hook: str,
    script: str,
) -> None:
    from moviepy.editor import (
        VideoFileClip, ColorClip, CompositeVideoClip, TextClip,
    )

    logger.info(f"MoviePy reel: {input_path}")

    raw      = VideoFileClip(input_path)
    duration = min(raw.duration, MAX_DURATION_S)
    clip     = raw.subclip(0, duration)

    # ── 9:16 fit ──────────────────────────────────────────────────────────────
    AVAIL_H    = TARGET_H - HEADER_H - FOOTER_H
    src_aspect = clip.w / clip.h
    tgt_aspect = TARGET_W / AVAIL_H

    if src_aspect > tgt_aspect:
        new_w, new_h = TARGET_W, int(TARGET_W / src_aspect)
    else:
        new_h, new_w = AVAIL_H, int(AVAIL_H * src_aspect)

    clip  = clip.resize((new_w, new_h))
    x_pos = (TARGET_W - new_w) // 2
    y_pos = HEADER_H + (AVAIL_H - new_h) // 2
    clip  = clip.set_position((x_pos, y_pos))

    # ── Background + bars ─────────────────────────────────────────────────────
    bg     = ColorClip((TARGET_W, TARGET_H), color=(10, 14, 26), duration=duration)
    header = ColorClip((TARGET_W, HEADER_H), color=(0, 20, 40),  duration=duration).set_position((0, 0))
    footer = ColorClip((TARGET_W, FOOTER_H), color=(0, 0, 0),    duration=duration).set_position((0, TARGET_H - FOOTER_H))
    layers = [bg, header, clip, footer]

    def _text(txt, size, color, font, pos, start=0):
        try:
            return (
                TextClip(txt, fontsize=size, color=color, font=font,
                         method="caption", size=(TARGET_W - 100, None), align="center")
                .set_position(pos).set_duration(duration).set_start(start)
            )
        except Exception as e:
            logger.warning(f"TextClip skipped ({e})")
            return None

    hook_text = hook if hook else topic.upper()
    for tc in [
        _text(hook_text[:80],              60, "white",   "DejaVu-Sans-Bold", ("center", 30)),
        _text(script[:140] if script else None, 36, "white", "DejaVu-Sans", ("center", TARGET_H - FOOTER_H + 20), start=2) if script else None,
        _text("Assoc. Prof. Dr. Özgür Karakoyun", 32, "#00C9C8", "DejaVu-Sans-Bold", (50, TARGET_H - FOOTER_H + 18)),
        _text("www.ozgurkarakoyun.com",     28, "white",   "DejaVu-Sans",      (50, TARGET_H - FOOTER_H + 60)),
    ]:
        if tc:
            layers.append(tc)

    final = CompositeVideoClip(layers, size=(TARGET_W, TARGET_H))
    out   = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    final.write_videofile(str(out), fps=24, codec="libx264", audio=False,
                          preset="ultrafast", threads=2, logger=None)
    raw.close()
    if not out.exists():
        raise FileNotFoundError(f"MoviePy did not produce {out}")
    logger.info(f"Reel {TARGET_W}x{TARGET_H} → {output_path}")


def _build_static_fallback(
    input_path: str,
    output_path: str,
    topic: str,
    hook: str,
) -> dict:
    """
    Generate a branded JPEG still.
    Returns the fallback image path — does NOT write a fake .mp4.
    """
    from media.template import build_image_post

    jpg_path = str(Path(output_path).with_suffix("")) + "_preview.jpg"
    build_image_post(input_path=input_path, output_path=jpg_path, topic=topic, hook=hook)
    logger.info(f"Static fallback → {jpg_path}")
    return {"type": "image_fallback", "path": jpg_path, "fallback": True}
