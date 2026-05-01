"""
ai/hashtags.py  ·  v2
Topic-matched hashtags + global orthopedic base.
Model: gpt-4o-mini
"""

import os
import logging

logger = logging.getLogger(__name__)

TOPIC_HASHTAGS: dict[str, list[str]] = {
    "hip replacement":   ["#HipReplacement", "#TotalHipArthroplasty", "#HipSurgery", "#HipPain", "#JointReplacement"],
    "knee replacement":  ["#KneeReplacement", "#TotalKneeArthroplasty", "#KneeSurgery", "#KneePain", "#ArthritisRelief"],
    "osseointegration":  ["#Osseointegration", "#OsseointegrationProsthetics", "#BoneAnchored", "#AmputeeLife", "#LimbLoss"],
    "scoliosis":         ["#Scoliosis", "#ScoliosisAwareness", "#SpinalHealth", "#ScoliosisSurgery", "#SpineDeformity"],
    "limb reconstruction": ["#LimbReconstruction", "#LimbLengthening", "#DeformityCorrection", "#ExternalFixator", "#Ilizarov"],
    "rehabilitation":    ["#OrthopedicRehab", "#PhysicalTherapy", "#RecoveryJourney", "#PostOpRecovery", "#RehabLife"],
    "orthopedic surgery": ["#OrthopedicSurgery", "#BoneHealth", "#JointCare", "#OrthopedicDoctor", "#SurgicalExcellence"],
    "ai in orthopedics": ["#AIinMedicine", "#MedicalAI", "#DigitalHealth", "#FutureOfMedicine", "#SmartOrthopedics"],
}

GLOBAL_BASE = [
    "#OrthopedicSurgeon",
    "#OzgurKarakoyun",
    "#MedicalEducation",
    "#TurkeyOrthopedics",
    "#GlobalHealthcare",
    "#PatientCare",
]


def _generate_with_openai(topic: str) -> list[str]:
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{
            "role": "user",
            "content": (
                f"Generate 10 Instagram hashtags for an orthopedic surgeon's post about: {topic}\n"
                "Requirements: English, globally searchable, mix of broad+niche, no spaces.\n"
                "Return ONLY hashtags, one per line, each starting with #. No explanation."
            )
        }],
        temperature=0.5,
        max_tokens=200,
    )
    lines = response.choices[0].message.content.strip().splitlines()
    return [l.strip() for l in lines if l.strip().startswith("#")][:10]


def _get_static(topic: str) -> list[str]:
    topic_lower = topic.lower()
    matched = []
    for key, tags in TOPIC_HASHTAGS.items():
        if key in topic_lower:
            matched.extend(tags)
    return list(dict.fromkeys(matched + GLOBAL_BASE))[:15]


def generate_hashtags(topic: str) -> list[str]:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if api_key and api_key.startswith("sk-"):
        try:
            tags = _generate_with_openai(topic)
            tags += ["#OzgurKarakoyun", "#OrthopedicSurgeon"]
            return list(dict.fromkeys(tags))
        except Exception as exc:
            logger.warning(f"OpenAI hashtags failed ({exc}), using static.")
    return _get_static(topic)
