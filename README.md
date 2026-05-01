# 🦴 AI Instagram Agent
### Assoc. Prof. Dr. Özgür Karakoyun – AI-Powered Orthopedic Content System

An AI-driven content production pipeline for a global English-language Instagram
presence. Upload an image or video → get a branded, medically ethical post with
caption, hashtags, and reel script — ready to review and publish.

---

## ✨ Features

| Feature | Details |
|---------|---------|
| 📸 Branded image post | 9:16 canvas, navy/teal medical aesthetic, auto-fitted image |
| 🎬 Reel preview | MoviePy-based video with header/footer overlay (falls back to still if needed) |
| 🤖 AI caption | OpenAI GPT-4o-mini • medically ethical • patient-friendly English |
| #️⃣ Hashtags | Topic-matched + global orthopedic tags (up to 15) |
| 🎤 Reel script | 2–3 sentence educational hook, TTS-ready |
| ⚕️ Disclaimer | Always appended: *"Medical information only. Consult your doctor."* |
| 📤 Publish flow | Preview → approve → Meta Graph API (placeholder, plug-in ready) |

---

## 🗂 Project Structure

```
ai-instagram-agent/
├── main.py                  # FastAPI app, all routes
├── requirements.txt
├── Procfile                 # Railway / Heroku entry point
├── .env.example             # Copy to .env and fill in keys
├── .gitignore
├── README.md
│
├── ai/
│   ├── caption.py           # OpenAI caption generation + dummy fallback
│   ├── hashtags.py          # Hashtag generation (static bank + OpenAI)
│   └── script.py            # Reel script (2–3 sentences, educational)
│
├── media/
│   ├── template.py          # Pillow image template engine (9:16 branded)
│   ├── video.py             # MoviePy reel preview builder
│   └── utils.py             # File validation + upload save
│
├── publish/
│   └── instagram.py         # Meta Graph API scaffold (placeholder active)
│
├── uploads/                 # Temporary upload storage (.gitkeep)
├── output/                  # Generated posts and reels (.gitkeep)
└── static/
    ├── template_bg.png      # Optional custom background
    └── fonts/               # Drop .ttf fonts here for custom typography
```

---

## ⚡ Local Setup

### 1. Clone and enter the project

```bash
git clone https://github.com/YOUR_USERNAME/ai-instagram-agent.git
cd ai-instagram-agent
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> **Note:** `moviepy` requires `ffmpeg` to be installed on your system.
> ```bash
> # Ubuntu/Debian
> sudo apt install ffmpeg
> # macOS
> brew install ffmpeg
> ```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env`:

```env
OPENAI_API_KEY=sk-...          # From https://platform.openai.com/api-keys
META_ACCESS_TOKEN=             # Leave blank for now (publish placeholder active)
INSTAGRAM_BUSINESS_ACCOUNT_ID=
```

### 5. Start the server

```bash
uvicorn main:app --reload --port 8000
```

Visit: **http://localhost:8000**
Interactive docs: **http://localhost:8000/docs**

---

## 🔌 API Usage

### `GET /`
Health check.

```bash
curl http://localhost:8000/
```

---

### `POST /create-post`

Generate a branded post from an uploaded image or video.

```bash
curl -X POST http://localhost:8000/create-post \
  -F "file=@your_image.jpg" \
  -F "topic=Osseointegration Prosthetics" \
  -F "content_type=image" \
  -F "tone=professional" \
  -F "auto_publish=false"
```

**Form fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `file` | file | required | JPG / PNG / MP4 / MOV |
| `topic` | string | required | e.g. "Hip Replacement" |
| `content_type` | string | `"image"` | `"image"` or `"reel"` |
| `tone` | string | `"professional"` | Caption tone |
| `auto_publish` | bool | `false` | No-op in Phase 1 |

**Response:**
```json
{
  "job_id": "a3f7b12c",
  "topic": "Hip Replacement",
  "hook": "Most hip replacement patients walk within 24 hours.",
  "generated_caption": "Most hip replacement patients walk within 24 hours.\n\nHip replacement is one...",
  "generated_hashtags": ["#HipReplacement", "#TotalHipArthroplasty", "..."],
  "full_caption": "caption text + hashtags — paste directly into Instagram",
  "reel_script": null,
  "medical_disclaimer": "Medical information only. Consult your doctor for diagnosis and treatment.",
  "output_file_path": "/output/post_a3f7b12c.jpg",
  "outputs": {
    "post": "/output/post_a3f7b12c.jpg",
    "story": "/output/story_a3f7b12c.jpg"
  },
  "preview_status": "ready",
  "publish_ready": false,
  "auto_publish_requested": false,
  "auto_publish_enabled": false
}
```

---

### `POST /approve-publish`

Send `job_id` to trigger publishing (placeholder in Phase 1).

```bash
curl -X POST http://localhost:8000/approve-publish \
  -F "job_id=a3f7b12c"
```

---

### `GET /preview/{filename}`

Download / view a generated file.

```bash
curl http://localhost:8000/preview/post_a3f7b12c.jpg --output preview.jpg
```

---

## 🚀 GitHub Push

```bash
git init
git add .
git commit -m "Initial commit – ai-instagram-agent"
git remote add origin https://github.com/YOUR_USERNAME/ai-instagram-agent.git
git push -u origin main
```

> ⚠️ `.env` is in `.gitignore` – **never** commit it.

---

## 🚂 Railway Deploy

### Option A – GitHub auto-deploy (recommended)

1. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub**
2. Select the `ai-instagram-agent` repository
3. Railway auto-detects the `Procfile` and starts the build

### Option B – Railway CLI

```bash
npm install -g @railway/cli
railway login
railway init
railway up
```

---

## 🔑 Environment Variables on Railway

1. In your Railway project dashboard, open **Variables**
2. Add each key:

| Variable | Value |
|----------|-------|
| `OPENAI_API_KEY` | `sk-...` |
| `META_ACCESS_TOKEN` | *(leave blank for now)* |
| `INSTAGRAM_BUSINESS_ACCOUNT_ID` | *(leave blank for now)* |
| `META_APP_ID` | *(leave blank for now)* |
| `META_APP_SECRET` | *(leave blank for now)* |

Railway sets `PORT` automatically — no need to add it.

---

## 📤 Instagram Publishing (Phase 2)

See `publish/instagram.py` for the full setup guide.

Quick checklist:
- [ ] Facebook App created with `instagram_content_publish` permission
- [ ] Instagram Business / Creator account connected to a Facebook Page
- [ ] Long-lived access token generated
- [ ] `META_ACCESS_TOKEN` and `INSTAGRAM_BUSINESS_ACCOUNT_ID` set in Railway variables
- [ ] Your generated images/videos are hosted at a public HTTPS URL (or use Railway's public domain)

---

## 🏷 Content Topics

- Orthopedic Surgery
- Hip Replacement
- Knee Replacement
- Osseointegration Prosthetics
- Scoliosis
- Limb Reconstruction
- AI in Orthopedics
- Rehabilitation

---

## 🩺 Medical Ethics

All generated captions include:

> *⚕️ Medical information only. Consult your doctor for diagnosis and treatment.*

The AI system prompt explicitly prohibits exaggerated treatment promises and follows
medical ethics guidelines for patient-facing content.

---

## 👨‍⚕️ About

Created for **Assoc. Prof. Dr. Özgür Karakoyun**  
Orthopedics & Traumatology | Limb Lengthening | Osseointegration | Tekirdağ, Turkey

📞 +90 545 919 54 13  
🌐 [www.ozgurkarakoyun.com](https://www.ozgurkarakoyun.com)  
📷 [@dr.ozgurkarakoyun](https://instagram.com/dr.ozgurkarakoyun)
