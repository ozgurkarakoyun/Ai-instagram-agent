"""
ai/script.py  ·  v2
2-3 sentence reel scripts. Educational, simple English.
Model: gpt-4o-mini
"""

import os
import logging

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
Write a spoken video script for Assoc. Prof. Dr. Özgür Karakoyun's Instagram Reel.
Rules:
- 2-3 sentences only
- Simple English for international audience
- Educational, not promotional
- No treatment guarantees
- End with: "Follow for more" or "Send me a DM"
- Natural speech rhythm — will be spoken on camera
"""

SCRIPTS: dict[str, str] = {
    "hip replacement":   "Hip replacement is one of orthopedics' greatest success stories — most patients are walking within 24 hours. Modern implants are designed to last decades, restoring the active life you deserve. Follow for more evidence-based orthopedic insights.",
    "knee replacement":  "Severe knee arthritis doesn't have to mean living in pain. Total knee replacement relieves that pain and restores function with implants that closely mimic natural joint movement. Send me a DM if you have questions.",
    "osseointegration":  "Osseointegration connects a prosthetic limb directly to the bone — no socket, no pressure sores, just natural movement. It's one of the most impactful advances in limb-loss care. Follow to learn more about this technology.",
    "scoliosis":         "Scoliosis is a spinal curve that, when detected early, can often be treated without surgery. Regular specialist evaluation is the key to the best outcome. Follow for more on spinal health.",
    "limb reconstruction": "Limb reconstruction corrects bone deformities and restores alignment using advanced fixation systems. With careful planning, patients regain full function and avoid amputation. Follow for more on limb-saving surgery.",
    "rehabilitation":    "Rehabilitation after orthopedic surgery is what turns a good operation into a great life outcome. A structured, progressive program tailored to you is non-negotiable. Follow for evidence-based recovery tips.",
    "orthopedic surgery": "Orthopedic surgery has transformed dramatically — minimally invasive techniques mean less pain and faster recovery. Every patient deserves a personalized, evidence-based plan. Follow for more specialist insights.",
}
DEFAULT_SCRIPT = "Orthopedic conditions are common, but with the right care, most patients return to an active life. The key is accurate diagnosis and a treatment plan tailored to you. Follow for trusted orthopedic education."


def _generate_with_openai(topic: str, hook: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Hook: {hook}\nTopic: {topic}\nWrite the reel script now."},
        ],
        temperature=0.65,
        max_tokens=150,
    )
    return response.choices[0].message.content.strip()


def _get_template(topic: str) -> str:
    tl = topic.lower()
    for key, script in SCRIPTS.items():
        if key in tl:
            return script
    return DEFAULT_SCRIPT


def generate_script(topic: str, hook: str = "") -> str:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if api_key and api_key.startswith("sk-"):
        try:
            return _generate_with_openai(topic, hook)
        except Exception as exc:
            logger.warning(f"OpenAI script failed ({exc}), using template.")
    return _get_template(topic)
