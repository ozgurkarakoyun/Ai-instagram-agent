"""
media/logo.py
Logo yükleme ve hazırlama modülü.

Desteklenen formatlar: SVG, PNG, JPG, WEBP
- SVG → cairosvg ile PNG'ye çevrilir
- PNG transparan arka plan desteklenir
- Logo yoksa None döner → template OK pill kullanır
"""

import logging
from pathlib import Path
from PIL import Image

logger = logging.getLogger(__name__)

LOGO_PATHS = [
    "static/logo.svg",
    "static/logo.png",
    "static/logo.jpg",
    "static/logo.webp",
]

_logo_cache: Image.Image | None = None
_cache_loaded = False


def _svg_to_png(svg_path: str, target_h: int = 200) -> Image.Image | None:
    """SVG dosyasını Pillow Image'a çevirir."""
    try:
        import cairosvg
        import io
        png_bytes = cairosvg.svg2png(
            url=svg_path,
            output_height=target_h * 2,   # 2x için render et, sonra scale
        )
        img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
        logger.info(f"SVG converted: {svg_path} → {img.size}")
        return img
    except ImportError:
        logger.warning("cairosvg not installed. SVG not supported. pip install cairosvg")
        return None
    except Exception as exc:
        logger.error(f"SVG conversion failed: {exc}")
        return None


def load_logo(target_h: int = 110) -> Image.Image | None:
    """
    Logo dosyasını yükler ve hedef yüksekliğe scale eder.
    Aspect ratio korunur.
    Cache kullanır — ilk yüklemeden sonra hızlıdır.

    Returns: RGBA Image veya None (logo bulunamazsa)
    """
    global _logo_cache, _cache_loaded

    if _cache_loaded:
        return _logo_cache

    _cache_loaded = True

    for path in LOGO_PATHS:
        if not Path(path).exists():
            continue

        logger.info(f"Loading logo: {path}")

        try:
            if path.endswith(".svg"):
                img = _svg_to_png(path, target_h=target_h * 2)
            else:
                img = Image.open(path).convert("RGBA")

            if img is None:
                continue

            # Scale to target height, preserve aspect ratio
            orig_w, orig_h = img.size
            scale = target_h / orig_h
            new_w = max(1, int(orig_w * scale))
            img   = img.resize((new_w, target_h), Image.LANCZOS)

            _logo_cache = img
            logger.info(f"Logo ready: {img.size}")
            return img

        except Exception as exc:
            logger.error(f"Logo load failed ({path}): {exc}")
            continue

    logger.info("No logo found in static/ — using text pill")
    return None


def invalidate_cache():
    """Logo dosyası değiştirildiğinde cache'i temizle."""
    global _logo_cache, _cache_loaded
    _logo_cache   = None
    _cache_loaded = False
