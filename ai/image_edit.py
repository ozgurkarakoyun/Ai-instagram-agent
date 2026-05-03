"""
ai/image_edit.py · GPT Image edit layer

Uploads the user's source image to OpenAI Images Edit API and returns a
brand-safe, Instagram-ready visual that can then be placed into the existing
post/story/reel templates.
"""

from __future__ import annotations

import base64
import logging
import os
from pathlib import Path
from typing import Literal

from PIL import Image

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("output/ai_images")
SUPPORTED_INPUT_EXT = {".jpg", ".jpeg", ".png", ".webp"}

FormatType = Literal["post", "story", "reel"]


def _format_instruction(target_format: FormatType) -> str:
    if target_format == "post":
        return (
            "Create a premium Instagram feed post visual. Portrait composition, "
            "optimized for a professional orthopedic medical account. Keep the main subject "
            "recognizable, improve clarity, lighting, background cleanliness and visual hierarchy. "
            "Leave clean negative space for headline overlays. No exaggerated claims."
        )
    if target_format == "story":
        return (
            "Create a premium Instagram Story visual. Vertical mobile-first composition, "
            "safe margins at top and bottom, clean professional medical aesthetic, suitable for "
            "orthopedic patient education. Keep the main subject recognizable and improve clarity."
        )
    return (
        "Create a cinematic vertical Reel cover/intro frame. Dynamic but medically professional, "
        "clean orthopedic education style, with safe margins for subtitles and title overlays. "
        "Keep the main subject recognizable and avoid sensationalism."
    )


def _prepare_image_for_api(input_path: str, job_id: str) -> Path:
    """Convert any supported source image to RGB PNG under 50 MB for Images API."""
    src = Path(input_path)
    if src.suffix.lower() not in SUPPORTED_INPUT_EXT:
        raise ValueError(f"GPT image editing requires an image file, got {src.suffix!r}.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    prepared = OUTPUT_DIR / f"source_{job_id}.png"

    img = Image.open(src).convert("RGB")
    # Keep enough detail but avoid very large API uploads.
    max_side = 2048
    w, h = img.size
    if max(w, h) > max_side:
        scale = max_side / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    img.save(prepared, "PNG", optimize=True)
    return prepared


def edit_uploaded_image(
    input_path: str,
    job_id: str,
    topic: str,
    hook: str = "",
    target_format: FormatType = "post",
) -> str:
    """
    Return a path to an AI-edited image. If OpenAI is not configured or editing
    fails, callers should fall back to the original upload.
    """
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")

    model = os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-2").strip() or "gpt-image-2"
    prompt = f"""
You are editing an uploaded image for Assoc. Prof. Dr. Özgür Karakoyun's orthopedic Instagram account.

Topic: {topic}
Hook: {hook}
Target format: {target_format}

{_format_instruction(target_format)}

Brand direction:
- Modern orthopedic/medical education visual
- Dark navy / cobalt medical background where appropriate
- Clean, ethical, evidence-based tone
- No fake before-after claims, no miracle language, no misleading anatomy
- If the source is an X-ray or medical image, preserve the clinical structure and make it cleaner, poster-like, and educational
- Do not add patient-identifying information
- Do not add large text; the app will overlay the title, doctor name, contact and disclaimer later
""".strip()

    prepared = _prepare_image_for_api(input_path, job_id)
    out_path = OUTPUT_DIR / f"edited_{target_format}_{job_id}.png"

    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    with prepared.open("rb") as image_file:
        response = client.images.edit(
            model=model,
            image=image_file,
            prompt=prompt,
            size="1024x1536",
            n=1,
            output_format="png",
        )

    b64 = response.data[0].b64_json
    out_path.write_bytes(base64.b64decode(b64))
    logger.info("GPT image edit produced %s using %s", out_path, model)
    return str(out_path)
