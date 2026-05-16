"""
Shared Hindi translation utility.
Converts English chapter names, teacher names, and subject names to Devanagari.

Priority:
  1. DB field (hindi_title / teacher_name_hindi) — always use if present
  2. Static subject map — instant, no LLM
  3. LLM (gpt-5.4-mini) — fallback for chapters and teacher transliterations
  4. st.session_state cache — avoids repeat LLM calls within a session
"""
import logging
import os

import streamlit as st
from openai import OpenAI

logger = logging.getLogger(__name__)

# ── Static subject map (no LLM needed) ────────────────────────────────────────

SUBJECT_HINDI_MAP: dict[str, str] = {
    "physics":               "भौतिकी",
    "chemistry":             "रसायन विज्ञान",
    "mathematics":           "गणित",
    "maths":                 "गणित",
    "math":                  "गणित",
    "biology":               "जीव विज्ञान",
    "accountancy":           "लेखाशास्त्र",
    "economics":             "अर्थशास्त्र",
    "business studies":      "व्यावसायिक अध्ययन",
    "political science":     "राजनीति विज्ञान",
    "history":               "इतिहास",
    "geography":             "भूगोल",
    "sociology":             "समाजशास्त्र",
    "psychology":            "मनोविज्ञान",
    "philosophy":            "दर्शनशास्त्र",
    "home science":          "गृह विज्ञान",
    "english":               "अंग्रेज़ी",
    "hindi":                 "हिंदी",
    "sanskrit":              "संस्कृत",
    "urdu":                  "उर्दू",
    "physical education":    "शारीरिक शिक्षा",
    "computer science":      "कंप्यूटर विज्ञान",
    "informatics practices": "सूचना विज्ञान",
}

# ── Helpers ────────────────────────────────────────────────────────────────────

def _llm(prompt: str, max_tokens: int = 30) -> str:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
    resp = client.chat.completions.create(
        model="gpt-5.4-mini",
        max_completion_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content.strip()


def _cached(key: str, fallback: str, prompt: str, max_tokens: int = 30) -> str:
    if st.session_state.get(key):
        return st.session_state[key]
    try:
        result = _llm(prompt, max_tokens)
    except Exception as e:
        logger.warning(f"[HindiTranslator] LLM failed for key={key}: {e}")
        result = fallback
    st.session_state[key] = result
    return result

# ── Public API ─────────────────────────────────────────────────────────────────

def subject_to_hindi(subject_en: str) -> str:
    """Returns Hindi subject name. Uses static map — no LLM."""
    return SUBJECT_HINDI_MAP.get(subject_en.lower().strip(), subject_en)


def chapter_to_hindi(chapter_en: str, hindi_title_from_db: str = "") -> str:
    """
    Returns Hindi chapter name.
    Uses DB hindi_title first, then session cache, then LLM.
    """
    from_db = (hindi_title_from_db or "").strip()
    if from_db:
        return from_db
    return _cached(
        key=f"hi_chap_{chapter_en}",
        fallback=chapter_en,
        prompt=(
            f"Translate this Indian school chapter name to its official Hindi name "
            f"as it appears in NCERT/board Hindi medium textbooks. "
            f"Return only the Devanagari text, nothing else: {chapter_en}"
        ),
        max_tokens=40,
    )


def teacher_to_hindi(teacher_en: str, teacher_name_hindi_from_db: str = "") -> str:
    """
    Returns Hindi (Devanagari transliteration) teacher name.
    Uses DB teacher_name_hindi first, then session cache, then LLM.
    e.g. 'Amber Sir' → 'अम्बर सर', 'Priya Ma'am' → 'प्रिया मैम'
    """
    from_db = (teacher_name_hindi_from_db or "").strip()
    if from_db:
        return from_db
    return _cached(
        key=f"hi_teacher_{teacher_en}",
        fallback=teacher_en,
        prompt=(
            f"Transliterate this Indian teacher name into Devanagari Hindi script. "
            f"Examples: 'Amber Sir' → 'अम्बर सर', 'Hardik Sir' → 'हार्दिक सर', "
            f"'Priya Ma'am' → 'प्रिया मैम'. "
            f"Return only the Devanagari text, nothing else: {teacher_en}"
        ),
        max_tokens=20,
    )


def translate_class(cls: dict) -> dict:
    """
    Given a class dict (from DB), returns a copy with hindi fields filled:
      subject_name_hindi, chapter_name_hindi, teacher_name_hindi
    Uses DB values first, static map for subjects, LLM for the rest.
    """
    result = dict(cls)
    result["subject_name_hindi"] = subject_to_hindi(cls.get("subject_name", ""))
    result["chapter_name_hindi"] = chapter_to_hindi(
        cls.get("chapter_name", ""),
        cls.get("hindi_title", ""),
    )
    result["teacher_name_hindi"] = teacher_to_hindi(
        cls.get("teacher_name", ""),
        cls.get("teacher_name_hindi", ""),
    )
    return result


def translate_batch(
    classes: list[dict],
    api_key: str = "",
    generate_fn=None,
) -> list[dict]:
    """
    Batch translation for a list of class dicts (used in Weekly Schedule).
    Sends one LLM call for all missing chapters + teachers + subjects together.
    Falls back to per-item translation if batch call fails.

    generate_fn: optional callable(prompt, api_key) → str  (reuses app.py's generate_message)
    """
    import json, re

    needs_chapter = [c for c in classes if not (c.get("hindi_title") or "").strip()]
    needs_teacher = [c for c in classes if not (c.get("teacher_name_hindi") or "").strip()]
    unique_subjects = list({c.get("subject_name", "") for c in classes if c.get("subject_name")})

    unique_chapters = list({c["chapter_name"] for c in needs_chapter if c.get("chapter_name")})
    unique_teachers = list({c["teacher_name"] for c in needs_teacher if c.get("teacher_name")})

    ch_map, th_map, subj_map = {}, {}, {}

    if unique_chapters or unique_teachers or unique_subjects:
        prompt = (
            "Return a JSON object with three keys:\n"
            "1. \"chapters\": map each English chapter name to its official Hindi (Devanagari) name "
            "as it appears in NCERT/board Hindi medium textbooks.\n"
            "2. \"teachers\": map each English teacher name to its Devanagari transliteration "
            "(e.g. 'Amber Sir' → 'अम्बर सर', 'Hardik Sir' → 'हार्दिक सर', 'Priya Ma'am' → 'प्रिया मैम').\n"
            "3. \"subjects\": map each English subject to its standard Hindi name "
            "(e.g. 'Physics' → 'भौतिकी', 'Chemistry' → 'रसायन विज्ञान', 'Mathematics' → 'गणित').\n\n"
            f"Chapters:\n" + "\n".join(f"- {n}" for n in unique_chapters) +
            f"\n\nTeachers:\n" + "\n".join(f"- {n}" for n in unique_teachers) +
            f"\n\nSubjects:\n" + "\n".join(f"- {n}" for n in unique_subjects)
        )
        try:
            if generate_fn:
                raw = generate_fn(prompt, api_key)
            else:
                raw = _llm(prompt, max_tokens=800)
            jm = re.search(r'\{.*\}', raw, re.DOTALL)
            data = json.loads(jm.group()) if jm else {}
            ch_map   = data.get("chapters", {})
            th_map   = data.get("teachers", {})
            subj_map = data.get("subjects", {})
        except Exception as e:
            logger.warning(f"[HindiTranslator] batch translation failed: {e}")

    result = []
    for cls in classes:
        c = dict(cls)
        c["subject_name_hindi"] = subj_map.get(c.get("subject_name", "")) or subject_to_hindi(c.get("subject_name", ""))
        c["chapter_name_hindi"] = (c.get("hindi_title") or "").strip() or ch_map.get(c.get("chapter_name", ""), c.get("chapter_name", ""))
        c["teacher_name_hindi"] = (c.get("teacher_name_hindi") or "").strip() or th_map.get(c.get("teacher_name", ""), c.get("teacher_name", ""))
        result.append(c)
    return result
