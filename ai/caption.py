"""
ai/caption.py
Structured caption: Hook → Explanation → Takeaway → CTA → Disclaimer
Model: gpt-4o-mini (stable, cost-effective)
"""

import os
import logging

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a medical content writer for Assoc. Prof. Dr. Özgür Karakoyun,
an orthopedic surgery specialist with global patients.

Output format (exactly this order, no extra sections):
1. HOOK LINE (already provided — use it as the first line verbatim)
2. EXPLANATION (2-3 sentences: educational, evidence-based, simple English)
3. TAKEAWAY (1 sentence: the key message)
4. CTA (1 sentence: gentle invitation — "Questions? DM or visit link in bio.")
5. DISCLAIMER (last line, always): "Medical information only. Consult your doctor for diagnosis and treatment."

Rules:
- English only
- No treatment guarantees
- No exaggerated promises
- Patient-friendly but professional
- Max 200 words total
- No hashtags (added separately)
- Return plain text only, no markdown, no section labels
"""


def _structured_dummy(topic: str, hook: str) -> str:
    body_map = {
        "hip replacement": (
            "Total hip replacement reliably relieves pain and restores mobility in patients "
            "with advanced arthritis. Modern implants are designed to last 20+ years, and most "
            "patients return to daily activities within weeks under proper rehabilitation.\n\n"
            "The key to a great outcome starts with the right surgical plan.\n\n"
            "Questions? DM or visit the link in bio."
        ),
        "knee replacement": (
            "Total knee arthroplasty is among the most studied procedures in medicine, "
            "with consistently high patient satisfaction when properly indicated. "
            "Advances in implant geometry now allow near-normal joint kinematics.\n\n"
            "Early intervention and structured rehab are what separate good outcomes from great ones.\n\n"
            "Questions? DM or visit the link in bio."
        ),
        "osseointegration": (
            "Osseointegration prosthetics anchor directly to the bone, eliminating socket pressure "
            "and dramatically improving walking ability and quality of life for selected amputees. "
            "The technique, pioneered in Scandinavia, is now available globally.\n\n"
            "Not every patient is a candidate — specialist evaluation is essential.\n\n"
            "Questions? DM or visit the link in bio."
        ),
        "scoliosis": (
            "Scoliosis is a lateral spinal curvature that, when detected early, "
            "can often be managed with bracing rather than surgery. "
            "Regular monitoring by a spine specialist is the cornerstone of care.\n\n"
            "Early detection is the most powerful tool we have.\n\n"
            "Questions? DM or visit the link in bio."
        ),
        "limb reconstruction": (
            "Modern limb reconstruction uses external and internal fixation systems to correct "
            "bone deformities, close defects, and restore alignment — often avoiding amputation. "
            "Every case demands a highly individualized surgical plan.\n\n"
            "With the right technique, the human body's regenerative capacity is remarkable.\n\n"
            "Questions? DM or visit the link in bio."
        ),
        "rehabilitation": (
            "Post-operative rehabilitation is the bridge between surgical success and functional recovery. "
            "A structured, progressive protocol — tailored to the procedure and the patient — "
            "is what converts a good operation into a life-changing outcome.\n\n"
            "Don't underestimate the second half of recovery.\n\n"
            "Questions? DM or visit the link in bio."
        ),
    }
    disclaimer = "Medical information only. Consult your doctor for diagnosis and treatment."
    topic_lower = topic.lower()
    for key, body in body_map.items():
        if key in topic_lower:
            return f"{hook}\n\n{body}\n\n{disclaimer}"
    default_body = (
        "Evidence-based orthopedic care combines advanced surgical precision with a deep "
        "commitment to patient outcomes. Whether managing trauma, joint disease, or complex "
        "deformity, the right treatment plan starts with a thorough evaluation.\n\n"
        "Informed patients make better decisions.\n\n"
        "Questions? DM or visit the link in bio."
    )
    return f"{hook}\n\n{default_body}\n\n{disclaimer}"


def _generate_with_openai(topic: str, tone: str, content_type: str, hook: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Topic: {topic}\n"
                    f"Hook line (use verbatim as first line): {hook}\n"
                    f"Tone: {tone}\n"
                    f"Format: {content_type}\n"
                    f"Doctor: Assoc. Prof. Dr. Özgür Karakoyun, Orthopedic Surgeon\n"
                    "Write the full caption now."
                ),
            },
        ],
        temperature=0.7,
        max_tokens=500,
    )
    return response.choices[0].message.content.strip()


def generate_caption(
    topic: str,
    tone: str = "professional",
    content_type: str = "image",
    hook: str = "",
) -> str:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if api_key and api_key.startswith("sk-"):
        try:
            return _generate_with_openai(topic=topic, tone=tone, content_type=content_type, hook=hook)
        except Exception as exc:
            logger.warning(f"OpenAI caption failed ({exc}), using template.")
    return _structured_dummy(topic, hook)
