"""
Static 15-minute pre-class reminder message builders for Category 1A.
3 variations × 2 languages (Hinglish + Hindi) = 6 messages.
No LLM needed — fully templated.

Auto-trigger note: currently shown in UI for manual copy-paste.
Automated scheduling (send 15 mins before class via WhatsApp API) not yet implemented.
"""
from typing import List, Tuple


def _details_hinglish(teacher: str, chapter: str, time_str: str, gender: str = "male") -> str:
    icon = "👩‍🏫" if gender == "female" else "👨‍🏫"
    return f"{icon} Teacher: {teacher}\n📚 Chapter: {chapter}\n🕐 Time: {time_str}"


def _details_hindi(teacher: str, chapter: str, time_str: str, gender: str = "male") -> str:
    icon = "👩‍🏫" if gender == "female" else "👨‍🏫"
    return f"{icon} शिक्षक: {teacher}\n📚 अध्याय: {chapter}\n🕐 समय: {time_str}"


def _resolve_names(class_data: dict, is_hindi: bool) -> Tuple[str, str, str, str]:
    teacher_en = (class_data.get("teacher_name") or "").strip()
    teacher_hi = (class_data.get("teacher_name_hindi") or "").strip()
    teacher    = teacher_hi if (is_hindi and teacher_hi) else teacher_en

    chapter_en = (class_data.get("chapter_name") or "").strip()
    chapter_hi = (class_data.get("hindi_title") or "").strip()
    chapter    = chapter_hi if (is_hindi and chapter_hi) else chapter_en

    time_str = (class_data.get("class_time") or "").strip()
    gender   = (class_data.get("teacher_gender") or "male").strip()
    return teacher, chapter, time_str, gender


# ── Variation 1 ───────────────────────────────────────────────────────────────

def _v1_hinglish(teacher: str, chapter: str, time_str: str, gender: str = "male") -> str:
    salutation = "Ma'am" if gender == "female" else "Sir"
    return (
        "🔔 REMINDER REMINDER REMINDER!!!\n"
        "\n"
        "Bacchon, 15 minute mein *LIVE CLASS* shuru hone wali hai! ⏰\n"
        f"Jaldi se join kar lo — jo sabse pehle join karega, usse {salutation} se baat karne ka mauka milega! 🎯🔥\n"
        "\n"
        + _details_hinglish(teacher, chapter, time_str, gender)
    )


def _v1_hindi(teacher: str, chapter: str, time_str: str, gender: str = "male") -> str:
    salutation = "Ma'am" if gender == "female" else "सर"
    return (
        "🔔 REMINDER REMINDER REMINDER!!!\n"
        "\n"
        "बच्चों, 15 मिनट में *LIVE CLASS* शुरू होने वाली है! ⏰\n"
        f"जल्दी से जुड़ो — जो सबसे पहले जुड़ेगा, उसे {salutation} से बात करने का मौका मिलेगा! 🎯🔥\n"
        "\n"
        + _details_hindi(teacher, chapter, time_str, gender)
    )


# ── Variation 2 ───────────────────────────────────────────────────────────────

def _v2_hinglish(teacher: str, chapter: str, time_str: str, gender: str = "male") -> str:
    return (
        "🔔 REMINDER REMINDER REMINDER!!!\n"
        "\n"
        "Bacchon kya kar rahe ho abhi?! 👀\n"
        "Jaldi taiyaar ho jao — 15 min mein *LIVE CLASS* shuru hone wali hai! ⏰\n"
        "\n"
        + _details_hinglish(teacher, chapter, time_str, gender)
    )


def _v2_hindi(teacher: str, chapter: str, time_str: str, gender: str = "male") -> str:
    return (
        "🔔 REMINDER REMINDER REMINDER!!!\n"
        "\n"
        "बच्चों अभी क्या कर रहे हो?! 👀\n"
        "जल्दी तैयार हो जाओ — 15 मिनट में *LIVE CLASS* शुरू होने वाली है! ⏰\n"
        "\n"
        + _details_hindi(teacher, chapter, time_str, gender)
    )


# ── Variation 3 ───────────────────────────────────────────────────────────────

def _v3_hinglish(teacher: str, chapter: str, time_str: str, gender: str = "male") -> str:
    return (
        "🚨 REMINDER REMINDER 🚨\n"
        "\n"
        f"*Jaldi join karo bacchon* —\n"
        f"{teacher} class mein aane wale hein.\n"
        "Time par nahi aaye toh zaroori topics samajh nahi aayenge 💯\n"
        "\n"
        + _details_hinglish(teacher, chapter, time_str, gender)
    )


def _v3_hindi(teacher: str, chapter: str, time_str: str, gender: str = "male") -> str:
    return (
        "🚨 REMINDER REMINDER 🚨\n"
        "\n"
        f"*जल्दी जुड़ो बच्चों* —\n"
        f"{teacher} क्लास में आने वाले हैं।\n"
        "समय पर नहीं आए तो ज़रूरी टॉपिक्स समझ नहीं आएंगे 💯\n"
        "\n"
        + _details_hindi(teacher, chapter, time_str, gender)
    )


# ── Public API ────────────────────────────────────────────────────────────────

_VARIATIONS_HINGLISH = [_v1_hinglish, _v2_hinglish, _v3_hinglish]
_VARIATIONS_HINDI    = [_v1_hindi,    _v2_hindi,    _v3_hindi]


def build_15min_reminder(class_data: dict, lang: str = "ENG", variation: int = 1) -> str:
    """
    Build a 15-minute pre-class reminder.
    variation: 1, 2, or 3.
    lang: "HIN" → Hindi text + Hindi names; anything else → Hinglish text + English names.
    """
    is_hindi = lang.upper().startswith("HIN")
    teacher, chapter, time_str, gender = _resolve_names(class_data, is_hindi)
    idx = max(0, min(variation - 1, 2))
    fn  = _VARIATIONS_HINDI[idx] if is_hindi else _VARIATIONS_HINGLISH[idx]
    return fn(teacher, chapter, time_str, gender)


def build_all_15min_reminders(class_data: dict, lang: str = "ENG") -> List[Tuple[str, str]]:
    """Returns all 3 variations as [(label, message), ...]."""
    return [
        (f"Variation {i}", build_15min_reminder(class_data, lang, variation=i))
        for i in range(1, 4)
    ]
