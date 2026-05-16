"""
Category 3B — Yesterday's Class Watch Check Poll
All logic, options, variations, and render for the yesterday watch-check poll tab.
"""
import html as _h
import logging
import os
import random

import streamlit as st
from openai import OpenAI
from datetime import datetime as _dt

from utils.db_poll import fetch_yesterday_watch_class
from utils.db_poll_test import fetch_yesterday_watch_class as fetch_yesterday_watch_class_test

logger = logging.getLogger(__name__)

# ── Subject Hindi map ──────────────────────────────────────────────────────────

_SUBJECT_HINDI_MAP = {
    "physics":               "भौतिकी",
    "chemistry":             "रसायन विज्ञान",
    "mathematics":           "गणित",
    "maths":                 "गणित",
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
    "english":               "अंग्रेजी",
    "hindi":                 "हिंदी",
    "sanskrit":              "संस्कृत",
    "urdu":                  "उर्दू",
    "physical education":    "शारीरिक शिक्षा",
    "computer science":      "कंप्यूटर विज्ञान",
    "informatics practices": "सूचना विज्ञान",
}

# ── Helpers ────────────────────────────────────────────────────────────────────

def _clean_chapter_name(name: str) -> str:
    import re as _re
    name = _re.sub(r'\s*[-–]\s*(Part|part|Lesson|lesson|भाग|पार्ट)\s*\d+', '', name)
    name = _re.sub(r'\s*\(?(Part|part|भाग|पार्ट)\s*\d+\)?', '', name)
    name = _re.sub(r'\s*[-–]\s*\d+\s*$', '', name)
    name = _re.sub(r'\s+\d+\s*$', '', name)
    return name.strip()


def _is_hindi(cls: dict) -> bool:
    return (cls.get("language") or "").upper().startswith("HIN")


def _translate_to_hindi(cls: dict) -> tuple:
    """Returns (subj_hindi, chapter_hindi, teacher_hindi)."""
    subj_en    = (cls.get("subject_name") or "").strip()
    chapter_en = _clean_chapter_name(cls.get("chapter_name") or "")
    teacher_en = (cls.get("teacher_name") or "").strip()
    teacher_h  = (cls.get("teacher_name_hindi") or teacher_en).strip()

    subj_h = _SUBJECT_HINDI_MAP.get(subj_en.lower(), "")
    if not subj_h:
        cache_key = f"yday_subj_hi_{subj_en}"
        if st.session_state.get(cache_key):
            subj_h = st.session_state[cache_key]
        else:
            try:
                _oc = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
                _resp = _oc.chat.completions.create(
                    model="gpt-5.4-mini",
                    max_completion_tokens=20,
                    messages=[{"role": "user", "content": (
                        f"Translate this Indian school subject name to Hindi "
                        f"(Devanagari script only, no extra words): {subj_en}"
                    )}],
                )
                subj_h = _resp.choices[0].message.content.strip()
            except Exception as e:
                logger.warning(f"[Poll3B] subject translate failed: {e}")
                subj_h = subj_en
            st.session_state[cache_key] = subj_h

    chapter_h = _clean_chapter_name((cls.get("hindi_title") or "").strip())
    if not chapter_h:
        cache_key = f"yday_chap_hi_{chapter_en}"
        if st.session_state.get(cache_key):
            chapter_h = st.session_state[cache_key]
        else:
            try:
                _oc = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
                _resp = _oc.chat.completions.create(
                    model="gpt-5.4-mini",
                    max_completion_tokens=30,
                    messages=[{"role": "user", "content": (
                        f"Translate this Indian school chapter name to Hindi "
                        f"(Devanagari script only, no extra words): {chapter_en}"
                    )}],
                )
                chapter_h = _resp.choices[0].message.content.strip()
            except Exception as e:
                logger.warning(f"[Poll3B] chapter translate failed: {e}")
                chapter_h = chapter_en
            st.session_state[cache_key] = chapter_h

    return subj_h, chapter_h, teacher_h

# ── Poll options ───────────────────────────────────────────────────────────────

def get_options(cls: dict) -> list:
    if _is_hindi(cls):
        return [
            ("A", "हाँ सर, समझ आ गया ✅"),
            ("B", "नहीं सर, थोड़ा कन्फ्यूजन है, एक बार और देखना पड़ेगा"),
            ("C", "कॉन्सेप्ट थोड़ा और डिटेल में समझना पड़ेगा 😊"),
        ]
    return [
        ("A", "Haan sir, samajh aa gaya ✅"),
        ("B", "Nahi sir, thoda confusion hai, ek baar aur dekhna padega"),
        ("C", "Concept thoda aur detail mein samajhna padega 😊"),
    ]

# ── Poll hook variations ───────────────────────────────────────────────────────

def get_variations(cls: dict) -> list:
    chapter = _clean_chapter_name(cls.get("chapter_name") or "")
    teacher = (cls.get("teacher_name") or "").strip()

    if _is_hindi(cls):
        _, chapter_h, teacher_h = _translate_to_hindi(cls)
        return [
            ("🔥 Variation 1", f"बच्चों, {chapter_h} चैप्टर की क्लास अटेंड की थी ना? 😄\nअब बताओ, कितना समझ आया? 👇"),
            ("💬 Variation 2", f"बच्चों, {teacher_h} ने {chapter_h} चैप्टर पढ़ाया था 📖\nअब बताओ, कॉन्सेप्ट्स कितने समझ आए? 👇"),
            ("📋 Variation 3", f"बच्चों, {chapter_h} की सारी कक्षाएँ देख ली थीं ना? 😄\nअब बताओ, आपको अध्याय कितना समझ आया? 👇"),
        ]
    return [
        ("💬 Variation 1", f"Bacchon, {teacher} Sir ne {chapter} chapter padhaya tha 📖\nAb batao, concepts kitne samajh aaye? 👇"),
        ("🔥 Variation 2", f"Bacchon, {chapter} chapter ki class attend ki thi na? 😄\nAb batao, kitna samajh aaya? 👇"),
    ]

# ── Render ─────────────────────────────────────────────────────────────────────

def render_poll_preview(hook_html: str, options: list) -> str:
    opts_html = "".join(
        f'<div class="wa-poll-option">'
        f'<div class="wa-poll-letter">{_h.escape(letter)}</div>'
        f'<div class="wa-poll-text">{_h.escape(opt)}</div>'
        f'</div>'
        for letter, opt in options
    )
    poll_card = (
        f'<div class="wa-poll-wrap">'
        f'<div class="wa-poll-header">📊 &nbsp;POLL</div>'
        f'{opts_html}'
        f'<div class="wa-poll-footer">Tap to vote · 0 votes</div>'
        f'</div>'
    )
    bubble = (
        f'<div class="wa-bubble-wrap"><div class="wa-bubble">'
        f'{hook_html}{poll_card}'
        f'<span class="wa-time">✓✓</span>'
        f'</div></div>'
    )
    return (
        f'<div style="background:#f5f5f7;border-radius:44px;padding:16px 12px;'
        f'border:8px solid #1d1d1f;max-width:360px;margin:0 auto;">'
        f'<div style="background:#eae6df;border-radius:32px;padding:12px 8px 8px 8px;">'
        f'{bubble}'
        f'</div></div>'
    )

# ── Main UI ────────────────────────────────────────────────────────────────────

def render(label_fn):
    """
    label_fn: callable(cls) → display label string (passed from app.py)
    """
    col_form, col_prev = st.columns([1, 1], gap="large")

    with col_form:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("#### Yesterday's Covered Class")
        test_mode = st.toggle("🧪 Test mode", value=False, key="p2_test_toggle")
        batch     = st.text_input("Batch Code", placeholder="e.g. MPBSE_CLASS_12_PCMB_ENG_2027", key="p2_batch_input")
        fetch_btn = st.button("🔍 Fetch Yesterday's Classes", key="p2_fetch_btn", use_container_width=True)

        if fetch_btn:
            if not batch.strip():
                st.error("Please enter a batch code.")
            else:
                with st.spinner("Fetching..."):
                    try:
                        fn = fetch_yesterday_watch_class_test if test_mode else fetch_yesterday_watch_class
                        classes, days_ago = fn(batch.strip())
                        st.session_state["p2_classes"]  = classes
                        st.session_state["p2_days_ago"] = days_ago
                        st.session_state.pop("p2_auto_pick", None)
                        if classes:
                            st.success(f"Found {len(classes)} class(es) from {days_ago} day(s) ago.")
                        else:
                            st.warning("No classes found.")
                            st.session_state.pop("p2_classes", None)
                    except Exception as e:
                        st.error(f"Error: {e}")
                        logger.error(f"[Poll3B] fetch error: {e}")

        selected = None
        if st.session_state.get("p2_classes"):
            classes = st.session_state["p2_classes"]

            if test_mode:
                opts    = {label_fn(c): c for c in classes}
                selected = opts[st.selectbox("Yesterday's Classes", list(opts.keys()), key="p2_class_select")]
            else:
                if "p2_auto_pick" not in st.session_state or st.session_state.get("p2_auto_batch") != batch.strip():
                    st.session_state["p2_auto_pick"]  = random.choice(classes)
                    st.session_state["p2_auto_batch"] = batch.strip()
                selected = st.session_state["p2_auto_pick"]
                st.caption(f"Auto-picked: **{label_fn(selected)}**")

            ts       = selected.get("start_ms")
            date_str = _dt.fromtimestamp(ts / 1000).strftime("%d %b %Y") if ts else "—"
            pills = (
                f'<span class="info-pill">📚 {selected["subject_name"]}</span>'
                f'<span class="info-pill">👨‍🏫 {selected["teacher_name"] or "—"}</span>'
                f'<span class="info-pill">🗓 {date_str}</span>'
            )
            st.markdown(f'<div style="margin:8px 0">{pills}</div>', unsafe_allow_html=True)

            variations   = get_variations(selected)
            var_labels   = [v[0] for v in variations]
            var_selected = st.radio("Poll variation", var_labels, horizontal=True, key="p2_var_radio")
            hook         = next(v[1] for v in variations if v[0] == var_selected)
            st.session_state["p2_hook"]         = hook
            st.session_state["p2_selected_cls"] = selected

        st.markdown("</div>", unsafe_allow_html=True)

    with col_prev:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("#### Poll Preview")

        if st.session_state.get("p2_hook"):
            hook_html = st.session_state["p2_hook"].replace('\n', '<br>')
            cls       = st.session_state.get("p2_selected_cls", {})
            st.markdown(render_poll_preview(hook_html, get_options(cls)), unsafe_allow_html=True)
            st.text_area("Copy poll text", st.session_state["p2_hook"], height=60, key="p2_copy_text")
        else:
            st.markdown("""
            <div style="text-align:center;padding:60px 20px;color:#a0aec0;">
                <div style="font-size:48px;margin-bottom:16px;">📊</div>
                <p style="font-size:15px;font-weight:500;">Fetch yesterday's classes<br>to see poll variations</p>
            </div>""", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)
