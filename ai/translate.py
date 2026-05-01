"""
ai/translate.py
Topic'i her zaman İngilizce'ye normalize eder.
OpenAI varsa çevirir, yoksa medikal terim sözlüğü kullanır.
"""

import os
import logging

logger = logging.getLogger(__name__)

# Yaygın Türkçe medikal terimler → İngilizce
TERM_MAP = {
    "diz protezi": "Knee Replacement",
    "kalça protezi": "Hip Replacement",
    "omuz protezi": "Shoulder Replacement",
    "skolyoz": "Scoliosis",
    "skolyosis": "Scoliosis",
    "osseointegrasyon": "Osseointegration",
    "osseointegrasyon": "Osseointegration",
    "uzuv uzatma": "Limb Lengthening",
    "bacak uzatma": "Limb Lengthening",
    "kemik uzatma": "Limb Lengthening",
    "deformite": "Deformity Correction",
    "deformite düzeltme": "Deformity Correction",
    "kırık tedavisi": "Fracture Treatment",
    "kırık": "Fracture",
    "rehabilitasyon": "Rehabilitation",
    "fizik tedavi": "Physical Therapy",
    "artroplasti": "Arthroplasty",
    "artrit": "Arthritis",
    "osteoartrit": "Osteoarthritis",
    "menisküs": "Meniscus",
    "bağ kopması": "Ligament Injury",
    "ön çapraz bağ": "ACL Injury",
    "omurga": "Spine",
    "bel fıtığı": "Lumbar Disc Herniation",
    "boyun fıtığı": "Cervical Disc Herniation",
    "yapay eklem": "Joint Replacement",
    "eklem": "Joint",
    "kemik": "Bone",
    "protez": "Prosthetics",
    "ampütasyon": "Amputation",
    "yapay uzuv": "Prosthetic Limb",
    "ai tıp": "AI in Orthopedics",
    "yapay zeka": "AI in Orthopedics",
}


def _translate_with_openai(topic: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{
            "role": "user",
            "content": (
                f"Translate this medical topic to English. "
                f"Return ONLY the translated topic, nothing else.\n"
                f"Topic: {topic}"
            )
        }],
        temperature=0.1,
        max_tokens=30,
    )
    return response.choices[0].message.content.strip()


def _translate_with_dict(topic: str) -> str:
    topic_lower = topic.lower().strip()
    for tr, en in TERM_MAP.items():
        if tr in topic_lower:
            return en
    # Eğer zaten İngilizce'ye benziyorsa olduğu gibi döndür
    return topic.title()


def normalize_topic(topic: str) -> tuple[str, bool]:
    """
    Topic'i İngilizce'ye normalize eder.
    Önce sözlüğe bakar, sonra OpenAI, sonra olduğu gibi döndürür.
    Returns: (normalized_topic, was_translated)
    """
    topic_stripped = topic.strip()

    # 1. Sözlük kontrolü (Türkçe medikal terimler)
    topic_lower = topic_stripped.lower()
    for tr, en in TERM_MAP.items():
        if tr in topic_lower:
            logger.info(f"Topic dict-match: {topic!r} → {en!r}")
            return en, True

    # 2. Türkçe karakter var mı?
    turkish_chars = set("çÇğĞıİöÖşŞüÜ")
    has_turkish = any(c in turkish_chars for c in topic_stripped)

    if not has_turkish:
        return topic_stripped, False  # Zaten İngilizce

    # 3. OpenAI ile çeviri
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if api_key and api_key.startswith("sk-"):
        try:
            translated = _translate_with_openai(topic_stripped)
            logger.info(f"Topic OpenAI: {topic!r} → {translated!r}")
            return translated, True
        except Exception as exc:
            logger.warning(f"OpenAI translate failed ({exc}), returning as-is.")

    return topic_stripped, False
