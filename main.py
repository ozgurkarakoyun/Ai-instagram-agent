"""
ai-instagram-agent  ·  main.py
Assoc. Prof. Dr. Özgür Karakoyun – AI Instagram Content System
Production build v2.0
"""

import os
import uuid
import logging
import time
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import uvicorn

load_dotenv()

from ai.caption import generate_caption
from ai.hashtags import generate_hashtags
from ai.script import generate_script
from ai.hook import generate_hook
from ai.translate import normalize_topic
from media.template import build_image_post, build_story_post
from media.video import build_reel_preview
from media.utils import validate_file, save_upload

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("instagram-agent")

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="AI Instagram Agent",
    description="Production-grade orthopedic content for Dr. Özgür Karakoyun",
    version="2.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

for d in ("output", "static", "uploads"):
    Path(d).mkdir(exist_ok=True)

app.mount("/output", StaticFiles(directory="output"), name="output")
app.mount("/static", StaticFiles(directory="static"), name="static")

MEDICAL_DISCLAIMER = "Medical information only. Consult your doctor for diagnosis and treatment."


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    rid = uuid.uuid4().hex[:8]
    request.state.request_id = rid
    start = time.time()
    response = await call_next(request)
    ms = round((time.time() - start) * 1000)
    response.headers["X-Request-ID"] = rid
    response.headers["X-Duration-Ms"] = str(ms)
    logger.info(f"[{rid}] {request.method} {request.url.path} {response.status_code} ({ms}ms)")
    return response


@app.get("/")
async def root():
    ui_path = Path("static/index.html")
    if ui_path.exists():
        return HTMLResponse(content=ui_path.read_text(encoding="utf-8"))
    return {
        "status": "running",
        "version": "2.0.0",
        "doctor": "Assoc. Prof. Dr. Özgür Karakoyun",
        "endpoints": ["/create-post", "/approve-publish", "/health", "/docs"],
    }


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": time.time()}


@app.post("/create-post")
async def create_post(
    request: Request,
    file: UploadFile = File(...),
    topic: str = Form(...),
    content_type: str = Form(default="image"),
    tone: str = Form(default="professional"),
    generate_story: bool = Form(default=True),
    auto_publish: bool = Form(default=False),
):
    rid = getattr(request.state, "request_id", uuid.uuid4().hex[:8])
    logger.info(f"[{rid}] topic={topic!r} type={content_type} tone={tone}")

    # Topic normalizasyonu (Türkçe → İngilizce)
    topic, was_translated = normalize_topic(topic)
    if was_translated:
        logger.info(f"[{rid}] Topic normalized → {topic!r}")

    try:
        validate_file(file, content_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        upload_path = await save_upload(file, rid)
    except Exception as exc:
        logger.error(f"[{rid}] Upload failed: {exc}")
        raise HTTPException(status_code=500, detail="Upload save failed.")

    try:
        hook     = generate_hook(topic=topic)
        caption  = generate_caption(topic=topic, tone=tone, content_type=content_type, hook=hook)
        hashtags = generate_hashtags(topic=topic)
        script   = generate_script(topic=topic) if content_type == "reel" else None
    except Exception as exc:
        logger.error(f"[{rid}] AI error: {exc}")
        raise HTTPException(status_code=500, detail=f"AI generation failed: {exc}")

    hashtag_str  = " ".join(hashtags)
    full_caption = f"{caption}\n\n{hashtag_str}"

    outputs = {}
    try:
        if content_type == "image":
            post_path = f"output/post_{rid}.jpg"
            build_image_post(str(upload_path), post_path, topic, hook)
            outputs["post"] = f"/{post_path}"

            if generate_story:
                story_path = f"output/story_{rid}.jpg"
                build_story_post(str(upload_path), story_path, topic, hook)
                outputs["story"] = f"/{story_path}"
        else:
            reel_path   = f"output/reel_{rid}.mp4"
            reel_result = build_reel_preview(str(upload_path), reel_path, topic, hook, script or "")
            actual_path    = reel_result.get("path", reel_path)
            is_fallback    = reel_result.get("fallback", False)
            outputs["reel"]          = f"/{actual_path}"
            outputs["reel_fallback"] = is_fallback
            if is_fallback:
                logger.warning(f"[{rid}] ffmpeg/MoviePy yok — fallback JPEG")
    except Exception as exc:
        logger.error(f"[{rid}] Media error: {exc}")
        raise HTTPException(status_code=500, detail=f"Media processing failed: {exc}")

    logger.info(f"[{rid}] Done -> {list(outputs.keys())}")

    return JSONResponse(content={
        "job_id": rid,
        "topic": topic,
        "topic_normalized": was_translated,
        # ── AI content ────────────────────────────────────────────────────────
        "hook": hook,
        "generated_caption": caption,
        "generated_hashtags": hashtags,
        "full_caption": full_caption,        # paste-ready: caption + hashtags
        "reel_script": script,
        "medical_disclaimer": MEDICAL_DISCLAIMER,
        # ── Media files ───────────────────────────────────────────────────────
        "output_file_path": outputs.get("post") or outputs.get("reel"),   # primary file
        "outputs": outputs,                   # all files: {"post": ..., "story": ...}
        # ── Status ───────────────────────────────────────────────────────────
        "preview_status": "ready",
        "publish_ready": False,
        "auto_publish_requested": auto_publish,
        "auto_publish_enabled": False,        # will activate when META_ACCESS_TOKEN is set
        "next_step": f"Review outputs then POST /approve-publish with job_id={rid!r}",
    })


@app.post("/approve-publish")
async def approve_publish(
    job_id: str = Form(...),
    output_type: str = Form(default="post"),
):
    base_url = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
    file_path = f"output/{output_type}_{job_id}.jpg"
    public_url = f"{base_url}/{file_path}" if base_url else None

    return JSONResponse(content={
        "job_id": job_id,
        "output_type": output_type,
        "status": "awaiting_meta_credentials",
        "public_file_url": public_url,
        "public_url_note": (
            "Set PUBLIC_BASE_URL in .env or Railway env vars to generate the correct URL."
            if not base_url else
            "Public URL generated. Use this with Meta Graph API image_url / video_url."
        ),
        "message": "Publishing module is ready for Meta Graph API integration.",
        "required_env_vars": [
            "META_ACCESS_TOKEN",
            "INSTAGRAM_BUSINESS_ACCOUNT_ID",
            "META_APP_ID",
            "META_APP_SECRET",
            "PUBLIC_BASE_URL",
        ],
    })


@app.get("/preview/{filename}")
async def preview_file(filename: str):
    safe_name = Path(filename).name
    path = Path("output") / safe_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(str(path))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
