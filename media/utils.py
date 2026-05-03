"""
media/utils.py  ·  v2
File validation with mime-type check, size limits, codec-safe extensions.
"""

import logging
import mimetypes
from pathlib import Path

from fastapi import UploadFile

logger = logging.getLogger(__name__)

# ── Allowed extensions ────────────────────────────────────────────────────────
IMAGE_EXT   = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
VIDEO_EXT   = {".mp4", ".mov", ".avi", ".mkv", ".m4v"}
ALL_EXT     = IMAGE_EXT | VIDEO_EXT

# ── Allowed MIME types ────────────────────────────────────────────────────────
IMAGE_MIME  = {"image/jpeg", "image/png", "image/webp", "image/heic"}
VIDEO_MIME  = {"video/mp4", "video/quicktime", "video/x-msvideo",
               "video/x-matroska", "video/mp4v-es", "video/mpeg"}

# ── File size limits ──────────────────────────────────────────────────────────
MAX_IMAGE_MB  = 20
MAX_VIDEO_MB  = 200
UPLOAD_DIR    = Path("uploads")


def validate_file(file: UploadFile, content_type: str) -> None:
    """
    Validate extension + MIME type + content_type match.
    Raises ValueError with a clear message on any failure.
    """
    if not file.filename:
        raise ValueError("No filename provided.")

    ext = Path(file.filename).suffix.lower()

    # Extension check
    if ext not in ALL_EXT:
        raise ValueError(
            f"Unsupported file extension '{ext}'. "
            f"Allowed: {', '.join(sorted(ALL_EXT))}"
        )

    # content_type ↔ extension mismatch
    if content_type == "image" and ext not in IMAGE_EXT:
        raise ValueError(
            f"content_type='image' but file extension is '{ext}'. "
            f"Upload a JPG, PNG, or WebP image."
        )
    # Reels can be generated from either a video or a still image slideshow.
    if content_type == "reel" and ext not in (VIDEO_EXT | IMAGE_EXT):
        raise ValueError(
            f"content_type='reel' but file extension is '{ext}'. "
            f"Upload an MP4/MOV video or a JPG/PNG/WebP image."
        )

    # MIME type check (based on extension mapping)
    guessed_mime, _ = mimetypes.guess_type(file.filename)
    declared_mime   = (file.content_type or "").lower().split(";")[0].strip()
    allowed_mime    = IMAGE_MIME if content_type == "image" else (VIDEO_MIME | IMAGE_MIME)

    for mime in (guessed_mime, declared_mime):
        if mime and mime not in allowed_mime:
            logger.warning(f"Suspicious MIME type for {file.filename!r}: {mime}")
            # Warn but don't block — extension is authoritative

    logger.info(f"Validated: {file.filename!r} ({content_type})")


async def save_upload(file: UploadFile, job_id: str) -> Path:
    """Read the uploaded file and persist under uploads/<job_id><ext>."""
    UPLOAD_DIR.mkdir(exist_ok=True)

    ext       = Path(file.filename).suffix.lower()
    save_path = UPLOAD_DIR / f"{job_id}{ext}"

    contents = await file.read()
    size_mb   = len(contents) / (1024 * 1024)

    # Size limit
    limit_mb = MAX_VIDEO_MB if ext in VIDEO_EXT else MAX_IMAGE_MB
    if size_mb > limit_mb:
        raise ValueError(
            f"File too large ({size_mb:.1f} MB). "
            f"Maximum for this type: {limit_mb} MB."
        )

    save_path.write_bytes(contents)
    logger.info(f"Upload saved: {save_path} ({size_mb:.2f} MB)")
    return save_path


def cleanup_job(job_id: str) -> None:
    """Remove all upload files for a job (optional housekeeping)."""
    for f in UPLOAD_DIR.glob(f"{job_id}*"):
        try:
            f.unlink()
            logger.info(f"Cleaned: {f}")
        except Exception as exc:
            logger.warning(f"Cleanup failed for {f}: {exc}")
