"""
ai/hook.py
Generate high-impact opening hook lines for Instagram content.

A strong hook is the single most important factor for reach.
Format: short, punchy, curiosity-driven, no clickbait.
"""

import os
import logging

logger = logging.getLogger(__name__)

HOOK_TEMPLATES: dict[str, list[str]] = {
    "hip replacement": [
        "Early mobilisation after hip replacement — what the evidence shows.",
        "3 signs you might need a hip replacement (that most people ignore)",
        "Your hip has been trying to tell you something for years.",
    ],
    "knee replacement": [
        "Why your knee still hurts — even after treatment.",
        "Knee arthritis at 50? It's more common than you think.",
        "3 things surgeons wish patients knew before knee replacement.",
    ],
    "osseointegration": [
        "Osseointegration may reduce socket-related discomfort in selected patients.",
        "Osseointegration anchors a prosthetic to bone — a significant advance for eligible patients.",
        "How osseointegration differs from traditional prosthetics.",
    ],
    "scoliosis": [
        "Caught early, scoliosis rarely needs surgery. Here's what to do.",
        "Your child's posture might be telling you something important.",
        "Scoliosis affects 3% of the population — and most don't know it.",
    ],
    "limb reconstruction": [
        "Bone can regenerate. Here's the science behind it.",
        "This fixator changed the way we approach bone deformity.",
        "Limb-saving surgery you've probably never heard of.",
    ],
    "rehabilitation": [
        "Surgery is 50% of recovery. The other 50% is this.",
        "Most patients skip this step — and wonder why recovery stalls.",
        "The fastest way to recover after orthopedic surgery.",
    ],
    "orthopedic surgery": [
        "Modern orthopedics is nothing like it was 10 years ago.",
        "Why minimally invasive surgery changed everything.",
        "The question every orthopedic patient should ask their surgeon.",
    ],
    "ai in orthopedics": [
        "AI is now helping surgeons plan operations. Here's how.",
        "The future of bone surgery is already here.",
        "How technology is making orthopedic outcomes more predictable.",
    ],
}

DEFAULT_HOOKS = [
    "What your orthopedic surgeon wants you to know.",
    "Evidence-based care makes a measurable difference in outcomes.",
    "The right diagnosis changes everything.",
]

SYSTEM_PROMPT = """
You write high-impact opening hook lines for an orthopedic surgeon's Instagram.

Rules:
- One sentence only (max 12 words)
- Creates curiosity without being clickbait
- Grounded in medical reality, not hype
- Could work as a video title or first caption line
- No hashtags, no emoji
"""


def _generate_with_openai(topic: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Write ONE hook line for an Instagram post about: {topic}\n"
                    "Doctor: Assoc. Prof. Dr. Özgür Karakoyun, Orthopedic Surgeon\n"
                    "Return ONLY the hook line. Nothing else."
                ),
            },
        ],
        temperature=0.8,
        max_tokens=60,
    )
    return response.choices[0].message.content.strip().strip('"').strip("'")


def _get_dummy(topic: str) -> str:
    topic_lower = topic.lower()
    for key, hooks in HOOK_TEMPLATES.items():
        if key in topic_lower:
            return hooks[0]
    return DEFAULT_HOOKS[0]


def generate_hook(topic: str) -> str:
    """Return a single punchy hook line for the given topic."""
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if api_key and api_key.startswith("sk-"):
        try:
            hook = _generate_with_openai(topic)
            logger.info(f"Hook via OpenAI: {hook!r}")
            return hook
        except Exception as exc:
            logger.warning(f"Hook OpenAI failed ({exc}), using template.")
    hook = _get_dummy(topic)
    logger.info(f"Hook from template: {hook!r}")
    return hook
