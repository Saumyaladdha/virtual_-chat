import streamlit as st
import streamlit.components.v1 as _st_components  # type: ignore[import-untyped]
import json
import os
import logging
from pathlib import Path
from difflib import SequenceMatcher
from openai import OpenAI
from dotenv import load_dotenv
from utils.db_live import fetch_today_classes
from utils.db_test import fetch_recent_classes
from utils.db_pyq import fetch_yesterday_classes as _fetch_yesterday_classes_prod, fetch_batch_meta as _fetch_batch_meta
from utils.db_pyq_test import fetch_yesterday_classes as _fetch_yesterday_classes_test
from utils.db_poll import fetch_today_poll_class, fetch_yesterday_watch_class
from utils.db_poll_test import fetch_today_poll_class as fetch_today_poll_class_test, fetch_yesterday_watch_class as fetch_yesterday_watch_class_test
from utils.db_mistake import fetch_mistake_class as _fetch_mistake_prod
from utils.db_mistake_test import fetch_mistake_class as _fetch_mistake_test
from utils.db_weekly import fetch_week_classes as _fetch_week_prod
from utils.db_weekly_test import fetch_week_classes_test as _fetch_week_test
from utils.reminders import build_all_15min_reminders
from utils.pyq_loader import pick_questions

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

load_dotenv()

st.set_page_config(
    page_title="Arivihan — Virtual Chat Generator",
    page_icon="🎓",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.main { background: #f5f5f7; }

.brand-header {
    background: #ffffff;
    border: 1px solid #e8e8ed;
    padding: 20px 28px;
    border-radius: 12px;
    margin-bottom: 24px;
    display: flex;
    align-items: center;
    gap: 12px;
}
.brand-title { color: #1d1d1f; font-size: 22px; font-weight: 700; margin: 0; }
.brand-sub { color: #6e6e73; font-size: 13px; margin: 2px 0 0 0; }
.brand-badge {
    background: #f5f5f7;
    color: #6e6e73;
    font-size: 11px;
    font-weight: 600;
    padding: 3px 10px;
    border-radius: 20px;
    border: 1px solid #e8e8ed;
    margin-left: auto;
}

.section-card {
    background: white;
    border-radius: 12px;
    padding: 22px 24px;
    border: 1px solid #e8e8ed;
    margin-bottom: 16px;
}
.section-label {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
    color: #6e6e73;
    text-transform: uppercase;
    margin-bottom: 4px;
}
.section-title {
    font-size: 18px;
    font-weight: 700;
    color: #1d1d1f;
    margin-bottom: 4px;
}
.section-desc {
    font-size: 13px;
    color: #6e6e73;
    margin-bottom: 0;
}

.info-pill {
    display: inline-block;
    background: #f5f5f7;
    color: #3a3a3c;
    font-size: 12px;
    font-weight: 500;
    padding: 4px 12px;
    border-radius: 20px;
    border: 1px solid #e8e8ed;
    margin: 3px 3px 3px 0;
}
.info-pill.green { background: #f0fff4; color: #276749; border-color: #c6f6d5; }
.info-pill.orange { background: #fffaf0; color: #9c4221; border-color: #fbd38d; }
.info-pill.red { background: #fff5f5; color: #c53030; border-color: #fed7d7; }

/* WhatsApp chat window */
.wa-screen {
    background: #eae6df url("https://web.whatsapp.com/img/bg-chat-tile-dark_04fcacde539c58cca6745483d4858c52.png");
    border-radius: 12px;
    padding: 20px 16px 12px 16px;
    margin-top: 8px;
}
/* Sent bubble (right side) */
.wa-bubble-wrap {
    display: flex;
    justify-content: flex-end;
    margin-bottom: 4px;
}
.wa-bubble {
    background: #dcf8c6;
    border-radius: 8px 0px 8px 8px;
    padding: 9px 14px 22px 14px;
    max-width: 88%;
    font-size: 14.5px;
    line-height: 1.7;
    color: #111b21;
    position: relative;
    box-shadow: 0 1px 2px rgba(0,0,0,0.13);
    word-break: break-word;
}
/* Bubble tail */
.wa-bubble::before {
    content: "";
    position: absolute;
    top: 0; right: -8px;
    width: 0; height: 0;
    border-left: 9px solid #dcf8c6;
    border-bottom: 9px solid transparent;
}
/* Timestamp inside bubble */
.wa-bubble .wa-time {
    position: absolute;
    bottom: 5px; right: 10px;
    font-size: 11px;
    color: #667781;
}
/* Bold (*text*) in bubble */
.wa-bubble strong {
    font-weight: 700;
    color: #111b21;
}
/* Image inside bubble */
.wa-bubble-img {
    background: #dcf8c6;
    border-radius: 8px 0px 8px 8px;
    max-width: 88%;
    overflow: hidden;
    box-shadow: 0 1px 2px rgba(0,0,0,0.13);
    margin-left: auto;
    margin-bottom: 2px;
    position: relative;
}
.wa-bubble-img::before {
    content: "";
    position: absolute;
    top: 0; right: -8px;
    width: 0; height: 0;
    border-left: 9px solid #dcf8c6;
    border-bottom: 9px solid transparent;
}
.wa-bubble-img img {
    width: 100%;
    display: block;
    max-height: 220px;
    object-fit: cover;
    border-radius: 6px 0px 0px 0px;
}

.pyq-question-box {
    background: #f5f5f7;
    border-left: 3px solid #3a3a3c;
    border-radius: 8px;
    padding: 14px 18px;
    font-size: 15px;
    font-weight: 500;
    color: #1d1d1f;
    margin: 10px 0;
    line-height: 1.6;
}

/* WhatsApp Poll card */
.wa-poll-wrap {
    background: #ffffff;
    border-radius: 8px;
    overflow: hidden;
    margin: 6px 0 4px 0;
    border: 1px solid #e0e0e0;
}
.wa-poll-header {
    background: #f9f9f9;
    border-bottom: 1px solid #e0e0e0;
    padding: 7px 12px;
    font-size: 11px;
    font-weight: 700;
    color: #667781;
    letter-spacing: 0.8px;
    text-transform: uppercase;
}
.wa-poll-option {
    display: flex;
    align-items: center;
    padding: 9px 12px;
    border-bottom: 1px solid #f0f0f0;
    gap: 10px;
}
.wa-poll-option:last-of-type { border-bottom: none; }
.wa-poll-letter {
    width: 22px; height: 22px;
    border-radius: 50%;
    border: 2px solid #667781;
    display: flex; align-items: center; justify-content: center;
    font-size: 11px; font-weight: 700; color: #667781;
    flex-shrink: 0;
}
.wa-poll-text {
    font-size: 13.5px;
    color: #111b21;
    line-height: 1.4;
}
.wa-poll-footer {
    padding: 5px 12px 8px 12px;
    font-size: 11px;
    color: #8696a0;
}

.stButton > button {
    background: #1d1d1f;
    color: white;
    border: none;
    padding: 12px 24px;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 600;
    width: 100%;
    transition: opacity 0.15s;
}
.stButton > button:hover { opacity: 0.8; border: none; }

.stSelectbox > div > div { border-radius: 8px; border-color: #e8e8ed; }
.stTextInput > div > div > input { border-radius: 8px; border-color: #e8e8ed; }

.divider { height: 1px; background: #e8e8ed; margin: 16px 0; }
</style>
""", unsafe_allow_html=True)

from datetime import date, datetime as _dt, timedelta

BASE_DIR = Path(__file__).parent
UNIFIED_DIR = BASE_DIR / "data" / "questions"
PROMPT_DIR = BASE_DIR / "prompts"

def _topper_file_key(grade_name: str, stream_name: str, language: str) -> str:
    """Map batch DB fields to topper image/CSV filename key, e.g. 'pcb_12th_english'."""
    grade = (grade_name or "").lower()
    stream = (stream_name or "").lower()
    medium = "hindi" if (language or "ENG").upper().startswith("HIN") else "english"

    if "10" in grade:
        return f"10th_{medium}"

    if any(k in stream for k in ("pcb", "bio", "medical", "neet")):
        prefix = "pcb"
    elif any(k in stream for k in ("pcm", "math", "jee", "engineering")):
        prefix = "pcm"
    elif any(k in stream for k in ("commerce", "account")):
        prefix = "commerce"
    elif any(k in stream for k in ("arts", "humanities")):
        prefix = "arts"
    else:
        prefix = "pcb"

    return f"{prefix}_12th_{medium}"


def load_festivals():
    fpath = BASE_DIR / "data" / "festivals_calendar.json"
    with open(fpath, encoding="utf-8") as f:
        data = json.load(f)
    all_festivals = []
    for year_festivals in data.values():
        all_festivals.extend(year_festivals)
    return all_festivals

def get_today_and_upcoming_festivals(days_ahead=7):
    today = date.today()
    upcoming = []
    for f in load_festivals():
        try:
            fdate = date.fromisoformat(f["date"])
        except Exception:
            continue
        delta = (fdate - today).days
        if 0 <= delta <= days_ahead:
            f["days_until"] = delta
            upcoming.append(f)
    upcoming.sort(key=lambda x: x["days_until"])
    return today, upcoming

def get_festival_for_date(check_date=None):
    if check_date is None:
        check_date = date.today()
    for f in load_festivals():
        try:
            if date.fromisoformat(f["date"]) == check_date:
                return f
        except Exception:
            continue
    return None

def get_all_festivals_sorted():
    all_f = load_festivals()
    all_f.sort(key=lambda x: x["date"])
    return all_f

def load_doubt_prompt(medium="English"):
    base = Path(__file__).parent / "prompts"
    if medium == "Hindi":
        path = base / "hindi" / "doubt_clearing.txt"
        if path.exists():
            return path.read_text(encoding="utf-8")
    path = base / "english" / "doubt_clearing.txt"
    return path.read_text(encoding="utf-8") if path.exists() else ""

def load_festival_prompt(medium="English"):
    base = Path(__file__).parent / "prompts"
    if medium == "Hindi":
        path = base / "hindi" / "festival_holiday_message.txt"
        if path.exists():
            return path.read_text(encoding="utf-8")
    path = base / "english" / "festival_holiday_message.txt"
    if path.exists():
        return path.read_text(encoding="utf-8")
    path = base / "festival_holiday_message.txt"
    return path.read_text(encoding="utf-8") if path.exists() else ""

BOARD_DISPLAY = {
    "mp": "MP Board (MPBSE)",
    "rj": "RJ Board (RBSE)",
    "up": "UP Board (UPMSP)",
}
# Short friendly names sent to the model
BOARD_SHORT = {
    "mp": "MP Board",
    "rj": "RJ Board",
    "up": "UP Board",
}
BOARD_KEY = {v: k for k, v in BOARD_DISPLAY.items()}

STREAM_OPTIONS = ["PCMB", "Commerce", "Arts"]

# Maps av_exams.code → internal board key
EXAM_CODE_TO_BOARD = {
    "MPBSE":    "mp",
    "RBSE":     "rj",
    "UPBHSIE":  "up",
}

def db_exam_to_board_key(exam_name, exam_code=None):
    if exam_code:
        key = EXAM_CODE_TO_BOARD.get((exam_code or "").upper().strip())
        if key:
            logger.info(f"[MAP] exam_code='{exam_code}' → board_key={key}")
            return key
    # Fallback to name matching
    e = (exam_name or "").upper()
    if "MP" in e or "MADHYA" in e:
        return "mp"
    if "RB" in e or "RAJASTHAN" in e:
        return "rj"
    if "UP" in e or "UTTAR" in e:
        return "up"
    logger.warning(f"[MAP] Unknown exam '{exam_name}' / '{exam_code}', defaulting to mp")
    return "mp"

def db_grade_to_class(grade_name):
    g = (grade_name or "").upper()
    if "12" in g or "XII" in g:
        return "Class 12"
    if "11" in g or "XI" in g:
        return "Class 11"
    return "Class 10"

def db_language_to_medium(language):
    return "Hindi" if (language or "").upper().startswith("HIN") else "English"

def db_stream_to_stream(stream_name):
    s = (stream_name or "").upper()
    if "COMMERCE" in s:
        return "Commerce"
    if "ARTS" in s or "HUMANITIES" in s:
        return "Arts"
    return "PCMB"

_SUBJECT_EN_TO_HI = {
    "physics": ["भौतिकी", "physics"],
    "chemistry": ["रसायन विज्ञान", "chemistry"],
    "biology": ["जीव विज्ञान", "biology"],
    "mathematics": ["गणित", "mathematics", "maths"],
    "maths": ["गणित", "mathematics", "maths"],
    "math": ["गणित", "mathematics", "maths"],
    "hindi": ["हिंदी", "hindi"],
    "english": ["अंग्रेज़ी", "english"],
    "accountancy": ["लेखाशास्त्र", "लेखांकन", "accountancy"],
    "business studies": ["व्यवसाय अध्ययन", "business studies"],
    "economics": ["अर्थशास्त्र", "economics"],
    "history": ["इतिहास", "history"],
    "geography": ["भूगोल", "geography"],
    "political science": ["राजनीति विज्ञान", "political science"],
    "sociology": ["समाजशास्त्र", "sociology"],
    "sanskrit": ["संस्कृत", "sanskrit"],
}

def fuzzy_match_subject(prefill, subjects_list):
    if not prefill or not subjects_list:
        return 0
    p = prefill.lower().strip()
    # Direct substring match
    for i, s in enumerate(subjects_list):
        if p in s.lower() or s.lower() in p:
            return i
    # English→Hindi translation fallback
    aliases = _SUBJECT_EN_TO_HI.get(p, [])
    for alias in aliases:
        for i, s in enumerate(subjects_list):
            if alias in s.lower() or s.lower() in alias:
                return i
    # Reverse: check if any alias of each subject matches prefill
    for i, s in enumerate(subjects_list):
        s_lower = s.lower()
        for eng, hi_list in _SUBJECT_EN_TO_HI.items():
            if s_lower in hi_list or any(h in s_lower for h in hi_list):
                if p == eng or p in hi_list:
                    return i
    return 0

def get_folder_path(class_level, medium, stream, board_key):
    if class_level == "Class 10":
        folder = "10_englishMedium" if medium == "English" else "10_hindiMedium"
        return UNIFIED_DIR / folder / board_key, False
    else:
        key = (stream, medium)
        folder_map = {
            ("PCMB", "English"): "12_pcmb",
            ("PCMB", "Hindi"): "12_pcmb-hindi",
            ("Commerce", "English"): "12_commerce",
            ("Commerce", "Hindi"): "12_commerce_hindi",
            ("Arts", "English"): "12_arts",
            ("Arts", "Hindi"): "12_arts_hindi",
        }
        folder_name = folder_map.get(key)
        if not folder_name:
            return None, False
        folder = UNIFIED_DIR / folder_name
        if folder_name == "12_arts_hindi":
            return folder, True  # flat folder — board identified via filename
        return folder / board_key, False

def detect_board_from_filename(fname, board_key):
    fname = fname.lower()
    if board_key == "mp":
        return fname.startswith("mp")
    elif board_key == "rj":
        return fname.startswith("rbse") or fname.startswith("rj")
    elif board_key == "up":
        return fname.startswith("up")
    return False

def load_subjects(folder_path, board_key=None, flat_board=False):
    subjects = {}
    if not folder_path or not folder_path.exists():
        return subjects
    for fpath in sorted(folder_path.glob("*.json")):
        if fpath.name.startswith("."):
            continue
        if flat_board and not detect_board_from_filename(fpath.name, board_key):
            continue
        try:
            with open(fpath, encoding="utf-8") as f:
                data = json.load(f)
            subject = data.get("subject", fpath.stem)
            subjects[subject] = (fpath, data)
        except Exception:
            continue
    return subjects

def get_chapters(data):
    chapters = []

    # Prefer syllabus.books[0].chapters — has marks data in unified JSONs.
    # Top-level data["chapters"] exists but marks are None there.
    books = data.get("syllabus", {}).get("books", [])
    if books:
        raw = books[0].get("chapters", [])
    else:
        raw = []

    # Fall back to top-level chapters (older flat format)
    if not raw:
        raw = data.get("chapters", [])

    # Fall back to blueprint
    if not raw:
        raw = data.get("blueprint", {}).get("units_or_chapters", [])

    for c in raw:
        name = (c.get("name") or "").strip()
        if name:
            chapters.append(c)
    return chapters

def fuzzy_match_chapter(typed_name, chapters):
    """Return best matching chapter object and similarity score (0-1)."""
    if not typed_name or not chapters:
        return None, 0.0
    best, best_score = None, 0.0
    typed_lower = typed_name.lower().strip()
    for c in chapters:
        name = c.get("name", "")
        score = SequenceMatcher(None, typed_lower, name.lower()).ratio()
        # Boost score if typed text is fully contained in chapter name or vice versa
        if typed_lower in name.lower() or name.lower() in typed_lower:
            score = max(score, 0.75)
        if score > best_score:
            best_score = score
            best = c
    return best, best_score

def get_chapter_context(chapter_obj):
    marks = chapter_obj.get("marks", 0) or chapter_obj.get("weightage_marks", 0) or 0
    guaranteed = chapter_obj.get("guaranteed_annual_question", False)
    must_not_skip = chapter_obj.get("is_must_not_skip", False)
    difficulty = chapter_obj.get("difficulty", "") or ""
    important_topics = chapter_obj.get("important_topics", []) or []
    repeated_topics = chapter_obj.get("most_repeated_topics", []) or []
    return {
        "marks": marks,
        "guaranteed_annual": guaranteed,
        "must_not_skip": must_not_skip,
        "difficulty": difficulty,
        "important_topics": important_topics[:3] if important_topics else [],
        "repeated_topics": repeated_topics[:2] if repeated_topics else [],
    }

def load_prompt_template(language: str = "ENG"):
    lang_dir = "hindi" if (language or "ENG").upper().startswith("HIN") else "english"
    prompt_path = PROMPT_DIR / lang_dir / "daily_live_class" / "base.txt"
    with open(prompt_path, encoding="utf-8") as f:
        return f.read()

def load_pyq_prompt_template(language: str = "ENG"):
    if (language or "ENG").upper().startswith("HIN"):
        path = PROMPT_DIR / "hindi" / "pyq_followup.txt"
    else:
        path = PROMPT_DIR / "english" / "pyq_followup.txt"
    with open(path, encoding="utf-8") as f:
        return f.read()

def load_poll_prompt_template(poll_type: str, language: str = "ENG"):
    """poll_type: 'today' or 'yesterday'"""
    fname = "today_class_watch_check.txt" if poll_type == "today" else "yesterday_class_watch_check.txt"
    if (language or "ENG").upper().startswith("HIN"):
        path = PROMPT_DIR / "hindi" / fname
        if not path.exists():
            path = PROMPT_DIR / "english" / fname
    else:
        path = PROMPT_DIR / "english" / fname
    with open(path, encoding="utf-8") as f:
        return f.read()

def title_case(text):
    """Capitalize each word, preserving all-caps like PYQ. Strips trailing part suffixes like '- II', '- III'."""
    if not text:
        return text
    import re as _re
    text = _re.sub(r'\s*-\s*(I{1,3}|IV|V?I{0,3})\s*$', '', text.strip(), flags=_re.IGNORECASE)
    def _cap(w):
        return w if w.isupper() and len(w) > 1 else w.capitalize()
    return " ".join(_cap(w) for w in text.strip().split())

def _get_fallback_hook(chapter_name: str, teacher_name: str, language: str = "ENG") -> str:
    """Pick one of 3 fallback hooks randomly each time."""
    import random
    idx = random.randint(0, 2)
    ch  = title_case(chapter_name)
    tch = title_case(teacher_name)
    is_hindi = (language or "ENG").upper().startswith("HIN")
    if is_hindi:
        hooks = [
            "यह अध्याय थोड़ी सी मेहनत में पूरे अंक देता है",
            f"आज की कक्षा के बाद {ch} से जुड़े सारे डाउट्स क्लियर हो जाएंगे",
            f"{tch} आज {ch} को बहुत मज़ेदार तरीके से समझाएंगे",
        ]
    else:
        hooks = [
            "yeh chapter thodi si mehnat mein poore marks deta hai",
            f"aaj ki class ke baad {ch} se related saare doubts clear ho jaayenge",
            f"{tch} aaj {ch} ko bahut mazedar tarah se samjhayenge",
        ]
    return hooks[idx]


def _get_day_format_instruction(language: str = "ENG") -> str:
    """Load the day-format instruction from prompts/*/daily_live_class/day_*.txt"""
    from datetime import date as _date
    day = _date.today().weekday()  # 0=Mon … 6=Sun
    cycle = {0: "fun_fact", 1: "marks", 2: "imp_topics",
             3: "fun_fact", 4: "marks", 5: "imp_topics", 6: "fun_fact"}
    fmt = cycle[day]
    lang_dir = "hindi" if (language or "ENG").upper().startswith("HIN") else "english"
    path = PROMPT_DIR / lang_dir / "daily_live_class" / f"day_{fmt}.txt"
    with open(path, encoding="utf-8") as f:
        return f.read().strip()


def build_prompt(template, class_level, board, subject, chapter_name, teacher_name,
                 class_time, marks, guaranteed_annual, must_not_skip, difficulty,
                 important_topics, repeated_topics, teacher_gender="male", language="ENG"):
    return template.format(
        class_level=class_level,
        board=board,
        subject=subject,
        chapter=title_case(chapter_name),
        teacher_name=title_case(teacher_name),
        teacher_gender=teacher_gender,
        class_time=class_time,
        marks=marks if marks else "Not available",
        guaranteed_annual="Yes" if guaranteed_annual else "No",
        must_not_skip="Yes" if must_not_skip else "No",
        difficulty=difficulty if difficulty else "Not specified",
        important_topics=", ".join(important_topics) if important_topics else "Not available",
        repeated_topics=", ".join(repeated_topics) if repeated_topics else "Not available",
        fallback_hook=_get_fallback_hook(chapter_name, teacher_name, language),
        day_format_instruction=_get_day_format_instruction(language),
    )

def build_multi_class_prompt(classes: list, language: str = "ENG") -> str:
    import re
    template = load_prompt_template(language)
    is_hindi = (language or "ENG").upper().startswith("HIN")

    def chapter_label(c):
        ht = (c.get("hindi_title") or "").strip()
        en = c["chapter_name"]
        if is_hindi:
            if ht:
                return ht
            return f"{en} [use the exact official NCERT Hindi textbook name for this chapter — do NOT translate word-by-word, use the precise name as it appears in the NCERT Hindi medium book]"
        return title_case(en)

    def teacher_label(c):
        if is_hindi:
            tnh = (c.get("teacher_name_hindi") or "").strip()
            if tnh:
                return tnh
            en = title_case(c["teacher_name"])
            return f"{en} [इस नाम को देवनागरी में लिखें, जैसे Hardik Sir → हार्दिक सर]"
        return title_case(c["teacher_name"])

    classes_block = "\n".join([
        f"Class {i+1}:\n"
        f"  Chapter: {chapter_label(c)}\n"
        f"  Subject: {c['subject_name']}\n"
        f"  Teacher: {teacher_label(c)} (gender: {c.get('teacher_gender','male')})\n"
        f"  Time: {c['class_time']}"
        for i, c in enumerate(classes)
    ])
    batch_meta = classes[0]

    # Strip the single-class CLASS DETAILS block — it has unfilled {vars} that confuse the model
    template_clean = re.sub(
        r'={3,}\s*CLASS DETAILS\s*={3,}.*?={3,}',
        '',
        template,
        flags=re.DOTALL,
    ).strip()

    header = (
        f"IMPORTANT: Write the message EXACTLY ONCE. Do not repeat it.\n"
        f"Board: {batch_meta.get('exam_name','')}\n"
        f"Class Level: {batch_meta.get('grade_name','')}\n"
        f"Medium: {batch_meta.get('language','')}\n\n"
        f"Today there are {len(classes)} live classes. Write ONE combined WhatsApp message.\n"
        f"Follow the MULTI-CLASS FORMAT section in your instructions below.\n\n"
        f"===== TODAY'S CLASSES =====\n"
        f"{classes_block}\n"
        f"===========================\n\n"
    )
    # Inject fallback_hook and day_format_instruction
    _fb_hook = _get_fallback_hook(classes[0]["chapter_name"], classes[0]["teacher_name"], language)
    template_clean = template_clean.replace("{fallback_hook}", _fb_hook)
    template_clean = template_clean.replace("{day_format_instruction}", _get_day_format_instruction(language))
    return header + template_clean

def clean_message(text):
    import re
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text, flags=re.DOTALL)  # strip **bold**
    text = re.sub(r'__(.+?)__', r'\1', text)
    text = re.sub(r'_(.+?)_', r'\1', text)
    text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)      # strip # ## ### headers
    text = re.sub(r'^[-*_]{3,}\s*$', '', text, flags=re.MULTILINE)  # strip --- *** ___ dividers
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def parse_poll_message(text):
    """Split generated poll text into (hook_text, [(letter, option_text), ...])."""
    import re
    # Match "Poll:" possibly preceded by an emoji or whitespace on the same or previous line
    parts = re.split(r'\n[^\n]{0,10}Poll\s*:\s*\n', text, maxsplit=1, flags=re.IGNORECASE)
    if len(parts) == 2:
        hook = parts[0].strip()
        # Strip any trailing emoji line from hook (e.g. lone "📊")
        hook = re.sub(r'\n\s*[\U00010000-\U0010ffff☀-➿︀-️]+\s*$', '', hook).strip()
        options = re.findall(r'^([A-D])\)\s*(.+)$', parts[1], re.MULTILINE)
        return hook, options
    # Fallback: try to find options anywhere in the text
    options = re.findall(r'^([A-D])\)\s*(.+)$', text, re.MULTILINE)
    if options:
        # Everything before the first option line is the hook
        first_opt_pos = text.find(f'{options[0][0]})')
        hook = text[:first_opt_pos].strip()
        # Remove trailing "Poll:" label from hook
        hook = re.sub(r'\n?\s*[^\n]{0,10}Poll\s*:?\s*$', '', hook, flags=re.IGNORECASE).strip()
        return hook, options
    return text.strip(), []

def render_phone_poll(hook_html, options):
    """Return full HTML: phone frame → WA chat bg → text bubble + poll card."""
    import html as _h
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
        f'{hook_html}'
        f'{poll_card}'
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

def generate_message(prompt_text, api_key):
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-5.4-mini",
        messages=[{"role": "user", "content": prompt_text}],
        temperature=0.8,
        max_completion_tokens=550,
    )
    return clean_message(response.choices[0].message.content)


def get_mistake_prompt_key(grade_name: str, stream_name: str, subject_name: str = "") -> str:
    grade = (grade_name or "").strip().lower()
    stream = (stream_name or "").strip().lower()
    subject = (subject_name or "").strip().lower()

    # Language subjects are cross-stream — check first
    if "english" in subject:
        return "english"
    if "sanskrit" in subject:
        return "sanskrit"
    if "hindi" in subject:
        return "hindi_subject"

    if "10" in grade:
        return "class10"
    if "12" in grade or "11" in grade:
        if any(k in stream for k in ("pcm", "math", "maths", "science")):
            return "class12_pcm"
        if any(k in stream for k in ("pcb", "bio", "biology", "medical")):
            return "class12_pcb"
        if any(k in stream for k in ("commerce", "account")):
            return "class12_commerce"
        if any(k in stream for k in ("art", "human", "history", "geog", "politic", "socio", "econom")):
            return "class12_arts"
    return "class10"


def build_chapter_context(chapter_name: str, hindi_title: str, subject_name: str,
                          medium: str, grade_name: str, stream_name: str, board_key: str) -> tuple[str, dict]:
    """
    Build chapter context from unified JSON for mistake prompt.
    Hindi medium: search Hindi JSON using hindi_title (if available), else empty.
    English medium: search English JSON using chapter_name.
    Returns (context_string, log_dict). context_string is empty if no data found.
    """
    log = {"status": "", "search_name": "", "matched_chapter": "", "match_score": 0.0, "fields_found": []}
    try:
        class_level = db_grade_to_class(grade_name)
        stream      = db_stream_to_stream(stream_name)

        if medium == "Hindi":
            fp, fb = get_folder_path(class_level, "Hindi", stream, board_key)
            search_name = hindi_title.strip() if hindi_title and hindi_title.strip() else ""
            if not search_name:
                log["status"] = "SKIP — hindi_title is empty; LLM uses own knowledge"
                print(f"[M11 ctx] ⚠️  {log['status']}")
                logger.info(f"[M11 ctx] {log['status']}")
                return "", log
        else:
            fp, fb = get_folder_path(class_level, "English", stream, board_key)
            search_name = chapter_name.strip()

        log["search_name"] = search_name
        print(f"\n[M11 ctx] Searching: '{search_name}' | medium={medium} | subject='{subject_name}' | class={class_level} | stream={stream} | board={board_key}")
        print(f"[M11 ctx] JSON folder path: {fp}")

        subj_map = load_subjects(fp, board_key=board_key, flat_board=fb)
        if not subj_map:
            log["status"] = f"SKIP — no subjects JSON found at {fp}"
            print(f"[M11 ctx] ❌  {log['status']}")
            logger.info(f"[M11 ctx] {log['status']}")
            return "", log

        si = fuzzy_match_subject(subject_name, list(subj_map.keys()))
        matched_subj = list(subj_map.keys())[si]
        _, sd = subj_map[matched_subj]
        chs = get_chapters(sd)
        print(f"[M11 ctx] Subject matched: '{matched_subj}' | chapters in JSON: {len(chs)}")
        cm, score = fuzzy_match_chapter(search_name, chs)
        log["match_score"] = round(score, 3)

        if not cm or score < 0.5:
            log["status"] = f"SKIP — chapter '{search_name}' not found (best score={score:.2f})"
            print(f"[M11 ctx] ❌  {log['status']}")
            logger.info(f"[M11 ctx] {log['status']}")
            return "", log

        log["matched_chapter"] = cm.get("chapter_name") or cm.get("name", "")
        print(f"\n[M11 ctx] ✅ Matched chapter: '{log['matched_chapter']}' | score={log['match_score']} | subject matched: '{matched_subj}'")
        _nonempty_keys = [k for k, v in cm.items() if v and v != [] and v != ""]
        print(f"[M11 ctx] Non-empty keys in chapter JSON: {_nonempty_keys}")

        parts = []
        def _add(label, val, limit=5):
            if isinstance(val, list) and val:
                truncated = val[:limit]
                line = f"{label}: {'; '.join(str(v) for v in truncated)}"
                parts.append(line)
                log["fields_found"].append(label)
                print(f"  [FIELD] {label}: {truncated}")
            elif isinstance(val, str) and val.strip():
                line = f"{label}: {val.strip()[:300]}"
                parts.append(line)
                log["fields_found"].append(label)
                print(f"  [FIELD] {label}: {val.strip()[:120]}")

        _add("Most Repeated Topics",       cm.get("most_repeated_topics"))
        _add("Frequently Asked",           cm.get("frequently_asked"))
        _add("Important Topics",           cm.get("important_topics"))
        _add("Topics",                     cm.get("topics"))
        _add("Important Formulas",         cm.get("important_formulas"), limit=6)
        _add("Important Reactions",        cm.get("important_reactions"), limit=4)
        _add("Important Derivations",      cm.get("important_derivations"), limit=3)
        _add("Important Diagrams",         cm.get("important_diagrams"), limit=3)
        _add("Common MCQ Traps",           cm.get("key_mcq_answers"), limit=5)
        _add("Guaranteed Annual Topic",    cm.get("guaranteed_annual_topic"))
        _add("Exam Note",                  cm.get("note"))
        _add("Why Students Lose Marks",    cm.get("difficulty_reason"))
        _add("Important Lines",            cm.get("important_lines"), limit=3)
        _add("Key Themes",                 cm.get("key_themes"), limit=3)
        if cm.get("has_numerical"):
            parts.append("Has Numericals: Yes — formula/unit mistakes are common")
            log["fields_found"].append("has_numerical")
            print("  [FIELD] has_numerical: True")
        if cm.get("is_mostly_diagram_based"):
            parts.append("Diagram Based: Yes — diagram label/arrow mistakes are common")
            log["fields_found"].append("is_mostly_diagram_based")
            print("  [FIELD] is_mostly_diagram_based: True")
        if cm.get("is_mostly_derivation"):
            parts.append("Derivation Based: Yes — step-skipping mistakes are common")
            log["fields_found"].append("is_mostly_derivation")
            print("  [FIELD] is_mostly_derivation: True")
        ai = cm.get("author_intro")
        if ai and isinstance(ai, dict):
            parts.append("Author Info: " + "; ".join(f"{k}: {v}" for k, v in list(ai.items())[:3])[:250])
            log["fields_found"].append("author_intro")
            print(f"  [FIELD] author_intro: {list(ai.items())[:3]}")

        ctx = "\n".join(parts)
        log["status"] = f"OK — matched '{log['matched_chapter']}' (score={log['match_score']}), {len(log['fields_found'])} fields"
        if not parts:
            print(f"  [M11 ctx] ⚠️  Chapter found but ALL fields are empty — LLM will use own knowledge")
        else:
            print(f"  [M11 ctx] {len(parts)} field(s) sent to LLM: {log['fields_found']}")
        logger.info(f"[M11 ctx] {log['status']} | fields: {log['fields_found']}")
        return ctx, log
    except Exception as e:
        log["status"] = f"ERROR — {e}"
        print(f"[M11 ctx] ❌ ERROR: {e}")
        logger.error(f"[M11 ctx] {log['status']}")
        return "", log


def load_mistake_prompt(key: str, medium: str = "English") -> str:
    base = Path(__file__).parent / "prompts"
    if medium == "Hindi":
        hindi_path = base / "hindi" / f"mistake_{key}_hindi.txt"
        if hindi_path.exists():
            return hindi_path.read_text(encoding="utf-8")
    path = base / "english" / f"mistake_{key}.txt"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def get_concept_prompt_key(grade_name: str, stream_name: str, subject_name: str = "") -> str:
    grade = (grade_name or "").strip().lower()
    stream = (stream_name or "").strip().lower()
    subject = (subject_name or "").strip().lower()

    if "english" in subject:
        return "english"
    if "sanskrit" in subject:
        return "sanskrit"
    if "hindi" in subject:
        return "hindi_subject"

    if "10" in grade:
        return "class10"
    if "12" in grade or "11" in grade:
        if any(k in stream for k in ("pcm", "math", "maths", "science")):
            return "class12_pcm"
        if any(k in stream for k in ("pcb", "bio", "biology", "medical")):
            return "class12_pcb"
        if any(k in stream for k in ("commerce", "account")):
            return "class12_commerce"
        if any(k in stream for k in ("art", "human", "history", "geog", "politic", "socio", "econom")):
            return "class12_arts"
    return "class10"


def load_weekly_prompt(medium: str = "English") -> str:
    base = Path(__file__).parent / "prompts"
    if medium == "Hindi":
        p = base / "hindi" / "weekly_schedule.txt"
        if p.exists():
            return p.read_text(encoding="utf-8")
    p = base / "english" / "weekly_schedule.txt"
    return p.read_text(encoding="utf-8") if p.exists() else ""


_CLOCK_EMOJI = {1:"🕐",2:"🕑",3:"🕒",4:"🕓",5:"🕔",6:"🕕",7:"🕖",8:"🕗",9:"🕘",10:"🕙",11:"🕚",12:"🕛"}
_WEEKDAY_EN  = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
_WEEKDAY_HI  = ["सोमवार","मंगलवार","बुधवार","गुरुवार","शुक्रवार","शनिवार","रविवार"]


def build_schedule_block(classes: list, medium: str = "English") -> str:
    """Group classes by weekday and return the pre-formatted schedule text block."""
    from collections import defaultdict
    days: dict = defaultdict(list)
    for c in classes:
        days[c["weekday"]].append(c)

    lines = []
    for wd in sorted(days.keys()):
        day_classes = sorted(days[wd], key=lambda x: x["start_ms"])
        day_label = _WEEKDAY_HI[wd] if medium == "Hindi" else _WEEKDAY_EN[wd]
        lines.append(f"📅 {day_label}")
        for cls in day_classes:
            # Clock emoji from first digit of hour (12-hour)
            from datetime import datetime, timezone, timedelta
            IST = timezone(timedelta(hours=5, minutes=30))
            start_ist = datetime.fromtimestamp(cls["start_ms"] / 1000, tz=IST)
            h12 = start_ist.hour % 12 or 12
            clock = _CLOCK_EMOJI.get(h12, "🕐")
            if medium == "Hindi":
                chapter_display = (cls.get("hindi_title") or cls["chapter_name"]).strip()
                teacher_display = (cls.get("teacher_name_hindi") or cls["teacher_name"]).strip()
                teacher_icon = "👩‍🏫" if cls["teacher_gender"] == "female" else "👨‍🏫"
                # Convert time to Hindi
                h = start_ist.hour
                m = start_ist.minute
                if h <= 11: prefix = "सुबह"
                elif h <= 15: prefix = "दोपहर"
                elif h <= 18: prefix = "शाम"
                else: prefix = "रात"
                dh = h if h <= 12 else h - 12
                time_str = f"{prefix} {dh} बजे" if m == 0 else f"{prefix} {dh}:{m:02d} बजे"
                lines.append(f"📚 अध्याय: {chapter_display}")
                lines.append(f"{teacher_icon} शिक्षक: {teacher_display}")
                lines.append(f"{clock} समय: {time_str}")
            else:
                teacher_icon = "👩‍🏫" if cls["teacher_gender"] == "female" else "👨‍🏫"
                lines.append(f"📚 Chapter: {cls['chapter_name']}")
                lines.append(f"{teacher_icon} Teacher: {cls['teacher_name']}")
                lines.append(f"{clock} Time: {cls['class_time']}")
            lines.append("")  # blank line between classes on same day
        # remove the trailing blank we just added before next day
        if lines and lines[-1] == "":
            lines.pop()
        lines.append("")  # blank line between days

    # strip trailing blank lines
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def build_days_summary(classes: list, medium: str = "English") -> str:
    from collections import Counter
    counts = Counter(c["weekday"] for c in classes)
    parts = []
    for wd in sorted(counts.keys()):
        day = _WEEKDAY_HI[wd] if medium == "Hindi" else _WEEKDAY_EN[wd]
        n = counts[wd]
        parts.append(f"{day} ({n})" if n > 1 else day)
    return ", ".join(parts)


def load_concept_prompt(key: str, medium: str = "English") -> str:
    base = Path(__file__).parent / "prompts"
    if medium == "Hindi":
        hindi_path = base / "hindi" / f"concept_{key}_hindi.txt"
        if hindi_path.exists():
            return hindi_path.read_text(encoding="utf-8")
    path = base / "english" / f"concept_{key}.txt"
    return path.read_text(encoding="utf-8") if path.exists() else ""


def generate_mistake_html(prompt_text: str, api_key: str) -> str:
    """Generate HTML card for mistake alert — higher token limit than generate_message."""
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-5.4-mini",
        messages=[{"role": "user", "content": prompt_text}],
        temperature=0.7,
        max_completion_tokens=3200,
    )
    return response.choices[0].message.content or ""



# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="brand-header">
    <div>
        <p class="brand-title">Arivihan Virtual Chat</p>
        <p class="brand-sub">AI Message Generator for Student Batches</p>
    </div>
    <span class="brand-badge">BETA</span>
</div>
""", unsafe_allow_html=True)

# ── API Key (from env only) ───────────────────────────────────────────────────
api_key = os.getenv("OPENAI_API_KEY", "")

with st.sidebar:
    st.markdown("### Categories")
    st.markdown("**1A** — Daily Live Class Update")
    st.markdown("**1B** — PYQ Drop")
    st.markdown("**3** — Class Watch Check Poll")
    st.markdown("**6** — Teacher Poll")
    st.markdown("**11** — Common Mistake Alert")
    st.markdown("**12** — Doubt Clearing Reminder")
    st.markdown("**F** — Festival / Holiday Message")
    st.markdown("**T** — Topper Spotlight")
    st.markdown("**W** — Weekly Schedule")
    st.markdown("🔒 Practice Reminder *(coming soon)*")

# ── Section Header ────────────────────────────────────────────────────────────
st.markdown("""
<div class="section-card">
    <p class="section-label">Category 1A — Daily Schedule Drop</p>
    <p class="section-title">Daily Live Class Update</p>
    <p class="section-desc">Generate a natural Hinglish batch message for today's live class. Picks real exam weightage and chapter data from the board syllabus.</p>
</div>
""", unsafe_allow_html=True)


# ── Category 1A — Batch Code Entry + Generate ────────────────────────────────
col_form, col_preview = st.columns([1, 1], gap="large")

with col_form:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown("#### Enter Batch Code")

    batch_code_input = st.text_input(
        "Batch Code",
        placeholder="e.g. MPBSE_CLASS_12_PCM_ENG_2027",
        key="batch_code_input",
    )

    test_mode = st.toggle("🧪 Test mode (fetch most recent classes, any date)", value=False, key="test_mode_toggle")

    btn_label = "🔍 Fetch Recent Classes (Test)" if test_mode else "🔍 Fetch Today's Classes"
    fetch_clicked = st.button(btn_label, key="fetch_btn", use_container_width=True)

    if fetch_clicked:
        if not batch_code_input.strip():
            st.warning("Please enter a batch code first.")
        else:
            logger.info(f"[UI] Fetching classes for batch_code: {batch_code_input.strip()}  test_mode={test_mode}")
            with st.spinner("Fetching from database..."):
                try:
                    if test_mode:
                        classes = fetch_recent_classes(batch_code_input.strip(), limit=5)
                    else:
                        classes = fetch_today_classes(batch_code_input.strip())
                    st.session_state["db_classes"] = classes
                    st.session_state["db_test_mode"] = test_mode
                    if classes:
                        logger.info(f"[UI] ✓ {len(classes)} class(es) found")
                        label = "recent" if test_mode else "today's"
                        st.success(f"✓ {len(classes)} {label} class(es) found.")
                    else:
                        msg = "No classes found in this batch at all." if test_mode else "No upcoming classes found for today in this batch."
                        st.warning(msg)
                except Exception as e:
                    logger.error(f"[UI] DB error: {e}")
                    st.error(f"Database error: {e}")
                    st.session_state["db_classes"] = []

    # ── Class selector ────────────────────────────────────────────────────────
    selected_class = None
    chapter_obj    = {}
    board_key      = "mp"
    class_level    = "Class 10"
    medium         = "English"
    stream         = None

    if st.session_state.get("db_classes"):
        classes = st.session_state["db_classes"]
        if st.session_state.get("db_test_mode"):
            st.warning("⚠️ Test mode — showing recent classes (not today's live schedule)")
        def _cls_label_1a(c):
            ts = c.get("start_ms")
            date_str = _dt.fromtimestamp(ts / 1000).strftime("%d %b %Y") if ts else "—"
            return f"{c['chapter_name']}  ·  {c['subject_name']}  ·  {c['class_time']}  ·  {date_str}"
        options_map = {_cls_label_1a(c): c for c in classes}
        selectbox_label = "Recent Classes (Test)" if st.session_state.get("db_test_mode") else "Today's Classes"
        selected_label = st.selectbox(
            selectbox_label,
            list(options_map.keys()),
            key="db_class_select",
        )
        selected_class = options_map[selected_label]

        # Read-only info pills
        pills_html = (
            f'<span class="info-pill">📚 {selected_class["subject_name"]}</span>'
            f'<span class="info-pill">👨\u200d🏫 {selected_class["teacher_name"] or "—"}</span>'
            f'<span class="info-pill">🕐 {selected_class["class_time"]}</span>'
        )
        st.markdown(f'<div style="margin:10px 0">{pills_html}</div>', unsafe_allow_html=True)

        # Derive board/class/medium/stream from DB data for JSON lookup
        board_key   = db_exam_to_board_key(selected_class["exam_name"], selected_class.get("exam_code"))
        class_level = db_grade_to_class(selected_class["grade_name"])
        medium      = db_language_to_medium(selected_class["language"])
        stream      = db_stream_to_stream(selected_class["stream_name"])
        logger.info(
            f"[UI] JSON lookup → board={board_key} class={class_level} "
            f"medium={medium} stream={stream}"
        )

        hindi_title = (selected_class.get("hindi_title") or "").strip()
        # Hindi batch + hindi_title available → Hindi folder, search by Devanagari name
        # Hindi batch + hindi_title NULL      → English folder, search by English name
        # English batch                       → English folder, search by English name
        effective_medium = "Hindi" if (medium == "Hindi" and hindi_title) else "English"
        json_search_term = hindi_title if effective_medium == "Hindi" else selected_class["chapter_name"]
        if effective_medium != medium:
            logger.info("[UI] hindi_title is NULL → falling back to English JSON folder")

        folder_path, flat_board = get_folder_path(class_level, effective_medium, stream, board_key)
        subjects_data = load_subjects(folder_path, board_key=board_key, flat_board=flat_board)

        if subjects_data:
            subj_idx = fuzzy_match_subject(selected_class["subject_name"], list(subjects_data.keys()))
            subject_name = list(subjects_data.keys())[subj_idx]
            _, subject_data = subjects_data[subject_name]
            chapters = get_chapters(subject_data)
            matched, score = fuzzy_match_chapter(json_search_term, chapters)
            if matched and score >= 0.60:
                chapter_obj = matched
                logger.info(f"[UI] JSON chapter match: '{matched['name']}' (score={score:.2f})")
                if score >= 0.85:
                    st.success(f"Syllabus match: {matched['name']}", icon="✅")
                else:
                    st.info(f"Closest syllabus match: {matched['name']}", icon="🔍")
            else:
                logger.info("[UI] No JSON chapter match — generating without weightage data")
                st.caption("No syllabus match — generating without weightage data.")

        # Weightage pills
        if chapter_obj:
            ctx_pills = get_chapter_context(chapter_obj)
            wp = ""
            if ctx_pills["marks"] > 0:
                wp += f'<span class="info-pill orange">📊 {ctx_pills["marks"]} Marks</span>'
            if ctx_pills["guaranteed_annual"]:
                wp += '<span class="info-pill green">✅ Annual Guaranteed</span>'
            if ctx_pills["must_not_skip"]:
                wp += '<span class="info-pill red">⚠️ Must Not Skip</span>'
            if ctx_pills["difficulty"]:
                wp += f'<span class="info-pill">🎯 {ctx_pills["difficulty"]}</span>'
            if wp:
                st.markdown(f'<div style="margin:8px 0">{wp}</div>', unsafe_allow_html=True)
            if ctx_pills["important_topics"]:
                st.caption("Key topics: " + " · ".join(ctx_pills["important_topics"]))

    st.markdown("</div>", unsafe_allow_html=True)
    all_classes = st.session_state.get("db_classes", [])
    generate_clicked = st.button("✨ Generate Message", key="gen_btn_1a")
    generate_all_clicked = (
        st.button(f"✨ Generate Combined Message ({len(all_classes)} classes)", key="gen_btn_all")
        if len(all_classes) >= 2 else False
    )

# ── Preview ───────────────────────────────────────────────────────────────────
with col_preview:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown("#### Generated Message")
    st.caption("Ready to copy and send to your student batch")

    if generate_all_clicked:
        if not api_key:
            st.error("Please enter your OpenAI API key in the sidebar.")
        elif not all_classes:
            st.error("Fetch a batch first.")
        else:
            with st.spinner(f"Generating combined message for {len(all_classes)} classes..."):
                try:
                    lang = all_classes[0].get("language", "ENG")
                    full_prompt = build_multi_class_prompt(all_classes, lang)
                    logger.info(f"[UI] Multi-class generate → {len(all_classes)} classes  lang={lang}")
                    message = generate_message(full_prompt, api_key)
                    st.session_state["generated_message"] = message
                    earliest = min(all_classes, key=lambda c: c.get("start_ms", 0))
                    st.session_state["last_thumbnail"] = earliest.get("video_image", "")
                    st.session_state["context_log"] = {"ctx": {}, "full_prompt": full_prompt}
                except Exception as e:
                    logger.error(f"[UI] Multi-class generation error: {e}")
                    st.error(f"Error: {e}")

    if generate_clicked:
        if not api_key:
            st.error("Please enter your OpenAI API key in the sidebar.")
        elif not selected_class:
            st.error("Fetch a batch and select a class first.")
        else:
            with st.spinner("Generating message..."):
                try:
                    ctx = get_chapter_context(chapter_obj) if chapter_obj else {
                        "marks": 0, "guaranteed_annual": False, "must_not_skip": False,
                        "difficulty": "", "important_topics": [], "repeated_topics": [],
                    }
                    board_short = BOARD_SHORT.get(board_key, "Board")
                    lang = selected_class.get("language", "ENG")
                    is_hindi = lang.upper().startswith("HIN")
                    if is_hindi:
                        ht = (selected_class.get("hindi_title") or "").strip()
                        chapter_for_prompt = ht if ht else (
                            f"{selected_class['chapter_name']} [use the exact official NCERT Hindi textbook name for this chapter — do NOT translate word-by-word, use the precise name as it appears in the NCERT Hindi medium book]"
                        )
                    else:
                        chapter_for_prompt = selected_class["chapter_name"]
                    if is_hindi:
                        tnh = (selected_class.get("teacher_name_hindi") or "").strip()
                        en_teacher = selected_class["teacher_name"]
                        teacher_for_prompt = tnh if tnh else (
                            f"{en_teacher} [इस नाम को देवनागरी में लिखें, जैसे Hardik Sir → हार्दिक सर]"
                        )
                    else:
                        teacher_for_prompt = selected_class["teacher_name"]
                    template = load_prompt_template(lang)
                    full_prompt = build_prompt(
                        template=template,
                        class_level=class_level,
                        board=board_short,
                        subject=selected_class["subject_name"],
                        chapter_name=chapter_for_prompt,
                        teacher_name=teacher_for_prompt,
                        class_time=selected_class["class_time"],
                        marks=ctx["marks"],
                        guaranteed_annual=ctx["guaranteed_annual"],
                        must_not_skip=ctx["must_not_skip"],
                        difficulty=ctx["difficulty"],
                        important_topics=ctx["important_topics"],
                        repeated_topics=ctx["repeated_topics"],
                        teacher_gender=selected_class.get("teacher_gender", "male"),
                        language=lang,
                    )
                    logger.info(
                        f"[UI] Generating → chapter='{selected_class['chapter_name']}' "
                        f"teacher='{selected_class['teacher_name']}' time='{selected_class['class_time']}' "
                        f"marks={ctx['marks']} guaranteed={ctx['guaranteed_annual']}"
                    )
                    message = generate_message(full_prompt, api_key)
                    st.session_state["generated_message"] = message
                    st.session_state["last_thumbnail"] = selected_class.get("video_image", "")
                    st.session_state["last_inputs"] = {
                        "board": board_short, "class": class_level,
                        "subject": selected_class["subject_name"],
                        "chapter": selected_class["chapter_name"],
                        "teacher": selected_class["teacher_name"],
                        "time":    selected_class["class_time"],
                    }
                    st.session_state["last_class_data"] = selected_class
                    st.session_state["context_log"] = {"ctx": ctx, "full_prompt": full_prompt}
                except Exception as e:
                    logger.error(f"[UI] Generation error: {e}")
                    st.error(f"Error: {e}")

    if "generated_message" in st.session_state:
        msg = st.session_state["generated_message"]
        thumb = st.session_state.get("last_thumbnail", "")

        import re as _re
        msg_html = _re.sub(r'\*([^*\n]+)\*', r'<strong>\1</strong>', msg)
        msg_html = msg_html.replace('\n', '<br>')

        if thumb:
            bubble_inner = (
                f'<div class="wa-bubble-img"><img src="{thumb}" /></div>'
                f'<div class="wa-bubble-wrap"><div class="wa-bubble">{msg_html}'
                f'<span class="wa-time">✓✓</span></div></div>'
            )
        else:
            bubble_inner = (
                f'<div class="wa-bubble-wrap"><div class="wa-bubble">{msg_html}'
                f'<span class="wa-time">✓✓</span></div></div>'
            )

        st.markdown(
            f'<div style="background:#f5f5f7;border-radius:44px;padding:16px 12px;'
            f'border:8px solid #1d1d1f;max-width:360px;margin:0 auto;">'
            f'<div style="background:#eae6df;border-radius:32px;padding:12px 8px 8px 8px;">'
            f'{bubble_inner}'
            f'</div></div>',
            unsafe_allow_html=True,
        )
        if "last_inputs" in st.session_state:
            inp = st.session_state["last_inputs"]
            st.markdown("---")
            st.caption(
                f"**{inp['board']}** · {inp['class']} · {inp['subject']} · "
                f"{inp['teacher']} · {inp['time']}"
            )

        if "context_log" in st.session_state:
            log = st.session_state["context_log"]
            ctx_data = log["ctx"]
            with st.expander("🔍 Data sent to model", expanded=False):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric("Marks", ctx_data.get("marks") or "—")
                    st.metric("Annual Guaranteed", "✅ Yes" if ctx_data.get("guaranteed_annual") else "❌ No")
                    st.metric("Must Not Skip", "⚠️ Yes" if ctx_data.get("must_not_skip") else "No")
                with col_b:
                    st.metric("Difficulty", ctx_data.get("difficulty") or "—")
                    st.metric("Important Topics", len(ctx_data.get("important_topics") or []))
                    st.metric("Repeated Topics", len(ctx_data.get("repeated_topics") or []))
                st.markdown("---")
                st.markdown("**Full prompt sent to model:**")
                st.code(log["full_prompt"], language="text")
    else:
        st.markdown("""
        <div style="text-align:center; padding:60px 20px; color:#a0aec0;">
            <div style="font-size:48px; margin-bottom:16px;">💬</div>
            <p style="font-size:15px; font-weight:500;">Enter a batch code, fetch today's classes,<br>then click Generate Message</p>
        </div>
        """, unsafe_allow_html=True)

    # ── 15-Min Reminder — always visible, no LLM ─────────────────────────────
    import re as _re_c1
    st.markdown("---")
    st.markdown("##### ⏰ 15-Min Reminder")
    _c1_test_mode = st.toggle("🧪 Test mode (skip time check)", value=False, key="c1_reminder_test_toggle")

    _c1_lang = "ENG"
    if "last_class_data" not in st.session_state:
        st.caption("Fetch a batch and generate a message first to preview the reminder.")
        _c1_cls_src = None
    else:
        _c1_cls_src  = st.session_state["last_class_data"]
        _c1_lang     = _c1_cls_src.get("language", "ENG")
        _c1_start_ms = _c1_cls_src.get("start_ms") or 0
        _c1_now_ms   = int(__import__('time').time() * 1000)
        _c1_mins_left = (_c1_start_ms - _c1_now_ms) / 60000

        if _c1_test_mode:
            st.caption(f"Test mode — skipping time check · class starts in {_c1_mins_left:.0f} min")
        elif 0 <= _c1_mins_left <= 15:
            st.caption(f"Class starts in {_c1_mins_left:.0f} min — send now!")
        elif _c1_mins_left < 0:
            st.info("Class has already started — reminder window passed.")
            _c1_cls_src = None
        else:
            st.info(f"Class starts in {_c1_mins_left:.0f} min — reminder will appear when ≤ 15 min remain.")
            _c1_cls_src = None

    if _c1_cls_src:
        _c1_variations = build_all_15min_reminders(_c1_cls_src, _c1_lang)
        _c1_tabs = st.tabs([f"V{i+1}" for i in range(len(_c1_variations))])
        for _c1_tab, (_, _c1_msg) in zip(_c1_tabs, _c1_variations):
            with _c1_tab:
                _c1_html = _re_c1.sub(r'\*([^*\n]+)\*', r'<strong>\1</strong>', _c1_msg.replace('\n', '<br>'))
                st.markdown(
                    f'<div style="background:#f5f5f7;border-radius:44px;padding:16px 12px;'
                    f'border:8px solid #1d1d1f;max-width:360px;margin:8px auto;">'
                    f'<div style="background:#eae6df;border-radius:32px;padding:12px 8px 8px 8px;">'
                    f'<div class="wa-bubble-wrap"><div class="wa-bubble">{_c1_html}'
                    f'<span class="wa-time">✓✓</span></div></div>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )
                st.code(_c1_msg, language="text")
    else:
        st.caption("Enable test mode to preview, or generate a morning message first.")

    st.markdown("</div>", unsafe_allow_html=True)


# ── PYQ Drop Section ──────────────────────────────────────────────────────────
st.markdown("""
<div class="section-card" style="margin-top:28px;">
    <p class="section-label">Category 1B — PYQ Drop</p>
    <p class="section-title">Yesterday's Class PYQ</p>
    <p class="section-desc">Fetch yesterday's covered chapters and drop a real board PYQ to keep students practising.</p>
</div>
""", unsafe_allow_html=True)

col_pyq_form, col_pyq_preview = st.columns([1, 1], gap="large")

with col_pyq_form:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown("#### Enter Batch Code")

    pyq_test_mode = st.toggle("🧪 Test mode (fetch most recent classes, any date)", value=False, key="pyq_test_mode_toggle")

    pyq_batch_code = st.text_input(
        "Batch Code",
        placeholder="e.g. MPBSE_CLASS_12_2026_COMMERCE_ENG_2026",
        key="pyq_batch_code_input",
    )
    btn_label_pyq = "🔍 Fetch Recent Classes (Test)" if pyq_test_mode else "🔍 Fetch Yesterday's Classes"
    pyq_fetch_clicked = st.button(btn_label_pyq, key="pyq_fetch_btn", use_container_width=True)

    if pyq_fetch_clicked:
        if not pyq_batch_code.strip():
            st.error("Please enter a batch code.")
        else:
            spinner_label = "Fetching recent classes (test mode)..." if pyq_test_mode else "Fetching recent classes..."
            with st.spinner(spinner_label):
                try:
                    _fetch_fn = _fetch_yesterday_classes_test if pyq_test_mode else _fetch_yesterday_classes_prod
                    classes, days_ago = _fetch_fn(pyq_batch_code.strip())
                    if classes:
                        st.session_state["pyq_classes"] = classes
                        st.session_state["pyq_days_ago"] = days_ago
                        label = "yesterday" if days_ago == 1 else f"{days_ago} days ago"
                        st.success(f"Found {len(classes)} class(es) from {label}.")
                    else:
                        st.warning("No classes found for yesterday or 2 days ago.")
                        st.session_state.pop("pyq_classes", None)
                        st.session_state.pop("pyq_days_ago", None)
                except Exception as e:
                    st.error(f"Error: {e}")
                    logger.error(f"[PYQ] fetch error: {e}")

    pyq_selected_class = None
    pyq_chapter_obj = None

    if st.session_state.get("pyq_classes"):
        import random as _random
        pyq_classes = st.session_state["pyq_classes"]
        days_ago_val = st.session_state.get("pyq_days_ago", 1)

        def _class_label(c):
            ts = c.get("start_ms")
            date_str = _dt.fromtimestamp(ts / 1000).strftime("%d %b %Y") if ts else "—"
            return f"{c['chapter_name']}  ·  {c['subject_name']}  ·  {date_str}"

        if pyq_test_mode:
            # Test mode: selectbox so user can pick
            _days_ago_label = "Yesterday's Classes" if days_ago_val == 1 else f"Classes ({days_ago_val} days ago)"
            pyq_options = {_class_label(c): c for c in pyq_classes}
            pyq_label = st.selectbox(_days_ago_label, list(pyq_options.keys()), key="pyq_class_select")
            pyq_selected_class = pyq_options[pyq_label]

            with st.expander("🔧 Manual Test Override", expanded=False):
                _m_batch   = st.text_input("Batch Code", key="pyq_m_batch", placeholder="e.g. MPBSE-12-PCM-HIN")
                _m_chapter = st.text_input("Chapter Name", key="pyq_m_chapter", placeholder="e.g. Probability")
                _m_subject = st.text_input("Subject", key="pyq_m_subject", placeholder="e.g. mathematics")
                if st.button("🔍 Test", key="pyq_m_run"):
                    if _m_chapter.strip() and _m_subject.strip():
                        _meta = _fetch_batch_meta(_m_batch.strip()) if _m_batch.strip() else {}
                        st.session_state["pyq_manual_test"] = {
                            "chapter_name":   _m_chapter.strip(),
                            "subject_name":   _m_subject.strip(),
                            "exam_code":      _meta.get("exam_code", ""),
                            "exam_name":      _meta.get("exam_name", ""),
                            "grade_name":     _meta.get("grade_name", ""),
                            "language":       _meta.get("language", "ENG"),
                            "teacher_name":   "Test",
                            "teacher_gender": "male",
                            "start_ms":       None,
                        }
                    else:
                        st.warning("Enter at least chapter name and subject.")
                if st.session_state.get("pyq_manual_test"):
                    _mt = st.session_state["pyq_manual_test"]
                    st.caption(
                        f"Active: **{_mt['chapter_name']}** · {_mt['subject_name']} · "
                        f"board={_mt['exam_code'] or '—'} · class={_mt['grade_name'] or '—'} · lang={_mt['language']}"
                    )
                    if st.button("✖ Clear", key="pyq_m_clear"):
                        st.session_state.pop("pyq_manual_test", None)
                    else:
                        pyq_selected_class = _mt
        else:
            # Production: auto-pick one randomly
            if "pyq_auto_pick" not in st.session_state or st.session_state.get("pyq_auto_pick_batch") != pyq_batch_code.strip():
                st.session_state["pyq_auto_pick"] = _random.choice(pyq_classes)
                st.session_state["pyq_auto_pick_batch"] = pyq_batch_code.strip()
            pyq_selected_class = st.session_state["pyq_auto_pick"]
            st.caption(f"Auto-picked: **{_class_label(pyq_selected_class)}**")

    if pyq_selected_class:
        ts = pyq_selected_class.get("start_ms")
        date_str = _dt.fromtimestamp(ts / 1000).strftime("%d %b %Y") if ts else "Manual"
        days_ago_val = st.session_state.get("pyq_days_ago", 1)
        days_label = f"{days_ago_val} day{'s' if days_ago_val > 1 else ''} ago · {date_str}" if ts else "Manual test"

        st.markdown(
            f'<div style="margin:10px 0">'
            f'<span class="info-pill">📚 {pyq_selected_class["subject_name"]}</span>'
            f'<span class="info-pill">👨‍🏫 {pyq_selected_class["teacher_name"] or "—"}</span>'
            f'<span class="info-pill">🗓 {days_label}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        _pyq_lang_raw = pyq_selected_class.get("language", "ENG")
        _pyq_csv_lang = "Hindi" if _pyq_lang_raw.upper().startswith("HIN") else "English"
        logger.info(
            f"[PYQ] calling pick_questions: exam_code='{pyq_selected_class.get('exam_code')}' "
            f"exam_name='{pyq_selected_class.get('exam_name')}' "
            f"grade_name='{pyq_selected_class.get('grade_name')}' lang='{_pyq_csv_lang}'"
        )
        pyqs = pick_questions(
            pyq_selected_class["chapter_name"],
            pyq_selected_class["subject_name"],
            n=8,
            language=_pyq_csv_lang,
            exam_code=pyq_selected_class.get("exam_code", ""),
            exam_name=pyq_selected_class.get("exam_name", ""),
            grade_name=pyq_selected_class.get("grade_name", ""),
        )
        if pyqs:
            st.session_state["pyq_questions"] = pyqs
            st.session_state.pop("pyq_manual_override", None)
            st.caption(f"CSV chapter matched: **{pyqs[0]['chapter']}** · {len(pyqs)} question(s) found")
            for i, q in enumerate(pyqs, 1):
                st.markdown(
                    f'<div class="pyq-question-box"><strong>Q{i}</strong> ({q["year"]} · {q["marks"]} marks)<br>{q["question"]}</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.info(f"No PYQ found for **{pyq_selected_class['subject_name']} — {pyq_selected_class['chapter_name']}**.")
            st.session_state.pop("pyq_questions", None)

    st.markdown("</div>", unsafe_allow_html=True)

    pyq_generate_clicked = (
        st.button("🖼️ Generate PYQ Image", key="pyq_gen_btn", use_container_width=True)
        if pyq_selected_class and st.session_state.get("pyq_questions")
        else False
    )

with col_pyq_preview:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown("#### PYQ Drop")
    st.caption("WhatsApp message + shareable image")

    if pyq_generate_clicked:
        import re as _re_pyq, tempfile as _tmpf, subprocess as _subp, sys as _sys, json as _jspyq, os as _ospyq
        from datetime import datetime as _dtpyq

        _src     = pyq_selected_class
        pyqs     = st.session_state["pyq_questions"]
        _lang_pyq = _src.get("language", "ENG")
        _is_hindi_pyq = _lang_pyq.upper().startswith("HIN")

        # Chapter name — strip Part suffix
        _ht_pyq = (_src.get("hindi_title") or "").strip()
        _chapter_raw_pyq = _ht_pyq if (_is_hindi_pyq and _ht_pyq) else _src["chapter_name"]
        _chapter_pyq = _re_pyq.sub(r"\s*[-–]\s*(Part|भाग)\s*\d+\s*$", "", _chapter_raw_pyq, flags=_re_pyq.IGNORECASE).strip()

        # Fixed WhatsApp text — no dashes, chapter name replaces "solutions"
        _wa_text = (
            f"Kal ki *{_chapter_pyq}* ki class se concept tho clear ho gaye honge, "
            f"chalo kuch PYQs practice kar lete 📝\n\n"
            f"Jo sawaal samajh na aaye, AI Instant Guru se seedha puch sakte ho, woh abhi jawab dega."
        )
        st.session_state["pyq_wa_text"]    = _wa_text
        st.session_state["pyq_chapter_display"] = _chapter_pyq

        # ── Build PYQ HTML image ─────────────────────────────────────────────
        # Decide how many questions to render based on total content length
        # (maths questions are long — fewer fit on the card)
        def _pyq_display_count(questions):
            total = sum(len(q.get("question", "")) for q in questions)
            if total <= 600:   return min(8, len(questions))
            if total <= 900:   return min(7, len(questions))
            if total <= 1200:  return min(6, len(questions))
            return min(5, len(questions))

        _pyqs_to_show = pyqs[:_pyq_display_count(pyqs)]

        def _latex_to_html(text: str) -> str:
            """Convert LaTeX tabular/table environments to HTML tables; keep $math$ for KaTeX."""
            import re as _re

            # Normalize DB encoding: x000d is carriage return stored as literal text
            text = text.replace('\x5cx000d', '\x5c\x5c ')
            text = text.replace('x000d', ' ')
            text = text.replace('\r\n', '\n').replace('\r', '\n')

            def _clean_cell(cell: str) -> str:
                cell = cell.strip()
                cell = _re.sub(r'\\newline\b', '<br>', cell)
                cell = _re.sub(r'\\textbf\{([^}]*)\}', r'<strong>\1</strong>', cell)
                cell = _re.sub(r'\\textit\{([^}]*)\}', r'<em>\1</em>', cell)
                cell = _re.sub(r'\\underline\{([^}]*)\}', r'<u>\1</u>', cell)
                cell = _re.sub(r'\\quad\b', '&nbsp;&nbsp;', cell)
                cell = _re.sub(r'\\hline\b', '', cell)
                cell = _re.sub(r'\\[a-zA-Z]+\{([^}]*)\}', r'\1', cell)
                cell = _re.sub(r'\\[a-zA-Z]+\b', '', cell)
                return cell.strip()

            def _tabular_to_html(col_spec: str, body: str) -> str:
                cols = _re.findall(r'[lrcpL]', col_spec)
                align_map = {'l': 'left', 'r': 'right', 'c': 'center', 'p': 'left', 'L': 'left'}
                rows = _re.split(r'\\\\\s*', body)
                html = (
                    '<table style="border-collapse:collapse;width:100%;font-size:12px;'
                    'margin:8px 0;font-family:sans-serif;line-height:1.5">'
                )
                for row in rows:
                    row = _re.sub(r'\\hline\b', '', row).strip()
                    if not row:
                        continue
                    cells = row.split('&')
                    html += '<tr>'
                    for ci, cell in enumerate(cells):
                        align = align_map.get(cols[ci] if ci < len(cols) else 'l', 'left')
                        html += (
                            f'<td style="border:1px solid #bbb;padding:4px 8px;'
                            f'text-align:{align};vertical-align:top">'
                            f'{_clean_cell(cell)}</td>'
                        )
                    html += '</tr>'
                html += '</table>'
                return html

            def _replace_table(m: object) -> str:
                inner = m.group(1)
                caption = ''
                cap_m = _re.search(r'\\caption\{([^}]*)\}', inner)
                if cap_m:
                    caption = _re.sub(r'\\textit\{([^}]*)\}', r'<em>\1</em>', cap_m.group(1))
                inner = _re.sub(r'\\caption(?:setup)?\{[^}]*\}', '', inner)
                inner = _re.sub(r'\\centering\b', '', inner)
                tab_m = _re.search(r'\\begin\{tabular\}\{([^}]*)\}(.*?)\\end\{tabular\}', inner, _re.DOTALL)
                table_html = _tabular_to_html(tab_m.group(1), tab_m.group(2)) if tab_m else inner
                prefix = (
                    f'<div style="text-align:center;font-weight:600;font-size:12px;'
                    f'margin:4px 0;font-family:sans-serif">{caption}</div>'
                ) if caption else ''
                return prefix + table_html

            text = _re.sub(r'\\begin\{table\}\[?[^\]]*\]?(.*?)\\end\{table\}', _replace_table, text, flags=_re.DOTALL)
            text = _re.sub(
                r'\\begin\{tabular\}\{([^}]*)\}(.*?)\\end\{tabular\}',
                lambda m: _tabular_to_html(m.group(1), m.group(2)),
                text, flags=_re.DOTALL
            )
            text = _re.sub(r'\\newline\b', '<br>', text)
            text = _re.sub(r'\\textbf\{([^}]*)\}', r'<strong>\1</strong>', text)
            text = _re.sub(r'\\textit\{([^}]*)\}', r'<em>\1</em>', text)
            text = _re.sub(r'\\underline\{([^}]*)\}', r'<u>\1</u>', text)
            text = _re.sub(r'\\quad\b', '&nbsp;&nbsp;', text)
            return text

        def _llm_clean_table(raw: str) -> str:
            """Call OpenAI to convert a LaTeX table question to clean HTML."""
            logger.info("[LLM table clean] calling gpt-5.4-mini to clean LaTeX table")
            try:
                _oc = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
                resp = _oc.chat.completions.create(
                    model="gpt-5.4-mini",
                    max_completion_tokens=2000,
                    temperature=0,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You convert a LaTeX exam question (with an embedded table) to clean HTML for a print card.\n\n"
                                "=== MATH — CRITICAL RULE ===\n"
                                "NEVER touch anything between $ and $. Copy it character-for-character.\n"
                                "Example: '$\\frac{1}{4}$' must appear in output exactly as '$\\frac{1}{4}$'.\n"
                                "KaTeX will render it — your job is only to leave it alone.\n\n"
                                "=== ENCODING ARTIFACTS — STRIP ALL OF THESE ===\n"
                                "The database stores carriage returns as text artifacts. Strip every occurrence:\n"
                                "  - bare 'x000d' (e.g. '& x000d &' → '& &')\n"
                                "  - '\\x000d' (backslash + x000d) — treat as row terminator '\\\\'\n"
                                "  - '_x000d_' (underscores around x000d) — treat as row terminator, remove the underscores\n"
                                "  - any orphan leading/trailing underscores left over must be removed\n\n"
                                "=== TABLE RENDERING ===\n"
                                "- Wrap table in: <div style=\"overflow-x:auto;max-width:100%\">\n"
                                "- Table: <table style=\"border-collapse:collapse;width:100%;table-layout:fixed;font-size:11px;margin:6px 0;font-family:sans-serif;line-height:1.4\">\n"
                                "- Each <td>: style=\"border:1px solid #bbb;padding:3px 6px;vertical-align:top;word-wrap:break-word;overflow-wrap:break-word\"\n"
                                "- Remove \\hline entirely (all variants: \\hline_, _\\hline_) — never output a row for \\hline\n"
                                "- 4-column balance sheet: use <colgroup> with widths 35%,15%,35%,15%\n\n"
                                "=== TEXT OUTSIDE TABLE ===\n"
                                "- \\textbf{X} → <strong>X</strong>, \\textit{X} → <em>X</em>, \\underline{X} → <u>X</u>\n"
                                "- \\newline or \\\\ outside table → <br>\n"
                                "- Newline between numbered conditions like (1)...(2)...(3) → add a space so words don't run together\n"
                                "- Remove: \\centering, \\caption{}, \\captionsetup{}, \\quad, \\label{}, \\[, \\], \\begin{table}, \\end{table}\n\n"
                                "=== OUTPUT ===\n"
                                "Output ONLY the final HTML. No markdown, no code fences, no explanation.\n"
                                "Do NOT wrap in <html>/<body>."
                            ),
                        },
                        {"role": "user", "content": raw},
                    ],
                )
                result = resp.choices[0].message.content.strip()
                logger.info("[LLM table clean] success")
            except Exception as e:
                logger.warning(f"[LLM table clean] failed: {e}")
                result = _latex_to_html(raw)
            return result

        def _q_block(i, q):
            if not q.get("question"):
                return ""
            yr   = f" {q['year']}" if q.get("year") else ""
            mrks = f"({q['marks']} marks)" if q.get("marks") else ""
            raw  = q["question"]
            if r'\begin{tabular}' in raw or r'\begin{table}' in raw:
                q_html = _llm_clean_table(raw)
            else:
                q_html = _latex_to_html(raw)
            return (
                f'<div class="q-row">'
                f'<div class="q-badge">Ques {i}</div>'
                f'<div class="q-body">'
                f'<div class="q-meta">Board{yr}</div>'
                f'<div class="q-text">{q_html} <span class="q-marks">{mrks}</span></div>'
                f'</div></div>'
            )

        _q_blocks = "".join(_q_block(i+1, _pyqs_to_show[i]) for i in range(len(_pyqs_to_show)))

        _pyq_tmpl = (Path(__file__).parent / "templates" / "pyq_card.html").read_text(encoding="utf-8")
        _pyq_html = _pyq_tmpl.replace("{{chapter_title}}", _chapter_pyq).replace("{{q_blocks}}", _q_blocks)

        st.session_state["pyq_html"] = _pyq_html

        # ── Screenshot via Playwright ────────────────────────────────────────
        with _tmpf.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8") as _tf:
            _tf.write(_pyq_html)
            _tf_path = _tf.name
        _png_path = _tf_path.replace(".html", ".png")

        _script = f"""
import pathlib
from playwright.sync_api import sync_playwright
html_content = pathlib.Path(r"{_tf_path}").read_text(encoding="utf-8")
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(device_scale_factor=3)
    page.set_content(html_content, wait_until="networkidle")
    page.wait_for_timeout(1000)
    el = page.query_selector(".card") or page.query_selector("body > div") or page.query_selector("body")
    if el is None:
        raise RuntimeError("No screenshottable element found")
    el.screenshot(path="{_png_path}")
    browser.close()
"""
        with st.spinner("Generating image..."):
            _res = _subp.run(["/usr/local/bin/python3.11", "-c", _script], capture_output=True, text=True)

        if _res.returncode == 0:
            with open(_png_path, "rb") as _pf:
                _png_bytes = _pf.read()
            st.session_state["pyq_png"] = _png_bytes
            print(f"[PYQ] Screenshot saved: {_png_path}")

            # Upload to S3
            try:
                import boto3 as _b3
                _s3c = _b3.client(
                    "s3", region_name=_ospyq.getenv("AWS_REGION","ap-south-1"),
                    aws_access_key_id=_ospyq.getenv("AWS_ACCESS_KEY_ID"),
                    aws_secret_access_key=_ospyq.getenv("AWS_SECRET_ACCESS_KEY"),
                )
                _s3_key = f"virtual_chat_responses/pyqs/{_dtpyq.now().strftime('%Y%m%d_%H%M%S')}_{_src['chapter_name'][:30].replace(' ','_')}.png"
                _s3_bucket = "mldatabase"
                _s3c.put_object(Bucket=_s3_bucket, Key=_s3_key, Body=_png_bytes, ContentType="image/png")
                _s3_url = f"https://{_s3_bucket}.s3.{_ospyq.getenv('AWS_REGION','ap-south-1')}.amazonaws.com/{_s3_key}"
                st.session_state["pyq_s3_url"] = _s3_url
                print(f"[PYQ] ✅ S3 URL: {_s3_url}")
                logger.info(f"[PYQ] S3 URL: {_s3_url}")
            except Exception as _s3e:
                print(f"[PYQ] ❌ S3 error: {_s3e}")
                st.session_state.pop("pyq_s3_url", None)

            for _fp in [_tf_path, _png_path]:
                try: _ospyq.remove(_fp)
                except: pass
        else:
            st.error(f"Screenshot failed: {_res.stderr[:300]}")
            logger.error(f"[PYQ] playwright error: {_res.stderr}")

    # ── Show WhatsApp attachment preview (image + caption together) ──────────
    if st.session_state.get("pyq_png") and st.session_state.get("pyq_wa_text"):
        import re as _rewap, base64 as _b64
        _wa_display = st.session_state["pyq_wa_text"]
        _wa_html    = _wa_display.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
        _wa_html    = _wa_html.replace("\n","<br>")
        _wa_html    = _rewap.sub(r"\*([^*]+)\*", r"<strong>\1</strong>", _wa_html)
        _img_b64    = _b64.b64encode(st.session_state["pyq_png"]).decode()

        # WhatsApp-style: image bubble with caption below inside same bubble
        st.markdown(
            f'<div style="background:#eae6df;border-radius:12px;padding:10px 8px;max-width:380px;">'
            f'<div style="background:#dcf8c6;border-radius:10px;overflow:hidden;">'
            f'<img src="data:image/png;base64,{_img_b64}" style="width:100%;display:block;border-radius:10px 10px 0 0;">'
            f'<div style="padding:10px 14px 10px;font-family:sans-serif;font-size:13.5px;line-height:1.7;color:#111b21;">'
            f'{_wa_html}'
            f'<span style="font-size:11px;color:#667781;float:right;margin-top:4px;">✓✓</span>'
            f'</div></div></div>',
            unsafe_allow_html=True,
        )
        st.markdown("<br>", unsafe_allow_html=True)
        st.text_area("Copy text", _wa_display, height=80, key="pyq_wa_copy")

        if st.session_state.get("pyq_s3_url"):
            _url = st.session_state["pyq_s3_url"]
            st.markdown(
                f'<div style="background:#e8f5e9;border-radius:8px;padding:10px 14px;margin:8px 0;">'
                f'<div style="font-size:11px;font-weight:700;color:#2e7d32;margin-bottom:4px;">☁️ S3 URL</div>'
                f'<a href="{_url}" target="_blank" style="font-size:12px;word-break:break-all;">{_url}</a>'
                f'</div>', unsafe_allow_html=True)
            st.code(_url, language=None)

        st.download_button("⬇️ Download PNG", data=st.session_state["pyq_png"],
            file_name="pyq_card.png", mime="image/png", use_container_width=True)
    else:
        st.markdown("""
        <div style="text-align:center;padding:60px 20px;color:#a0aec0;">
            <div style="font-size:48px;margin-bottom:16px;">📝</div>
            <p style="font-size:15px;font-weight:500;">Fetch yesterday's classes,<br>then click Generate PYQ Image</p>
        </div>""", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


# ── Category 3 — Poll Messages ────────────────────────────────────────────────
st.markdown("""
<div class="section-card" style="margin-top:28px;">
    <p class="section-label">Category 3 — Engagement Poll</p>
    <p class="section-title">Class Watch Check</p>
    <p class="section-desc">WhatsApp poll — before today's live class (attendance intent) or the morning after (watch-check).</p>
</div>
""", unsafe_allow_html=True)

_poll_tab_today, _poll_tab_yday = st.tabs(["📅 Today's Class Poll", "📋 Yesterday's Watch Check"])

def _clean_chapter_name(name: str) -> str:
    import re as _recn
    name = _recn.sub(r'\s*[-–]\s*(Part|part|Lesson|lesson|भाग|पार्ट)\s*\d+', '', name)
    name = _recn.sub(r'\s*\(?(Part|part|भाग|पार्ट)\s*\d+\)?', '', name)
    name = _recn.sub(r'\s*[-–]\s*\d+\s*$', '', name)
    name = _recn.sub(r'\s+\d+\s*$', '', name)
    return name.strip()

def _time_short(class_time: str) -> str:
    # "Shaam 4 baje" → "4 baje", "Subah 10:30 baje" → "10:30 baje"
    parts = class_time.strip().split(" ", 1)
    return parts[1] if len(parts) == 2 else class_time

def _is_hindi_batch(cls):
    return (cls.get("language") or "").upper().startswith("HIN")

def _p1_options(cls):
    if _is_hindi_batch(cls):
        return [
            ("1", "बिल्कुल, तैयार हैं! 🔥"),
            ("2", "आज नहीं आ पाएंगे 🙏"),
            ("3", "मिस हो जाएगी 😅"),
            ("4", "रिकॉर्डिंग बाद में देख लेंगे 📺"),
        ]
    return [
        ("1", "Bilkul, ready hain! 🔥"),
        ("2", "Aaj nahi aa payenge 🙏"),
        ("3", "Miss ho jayegi 😅"),
        ("4", "Recording dekh lenge baad mein 📺"),
    ]

def _p2_options(cls):
    if _is_hindi_batch(cls):
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


def _translate_poll_names_to_hindi(cls: dict) -> tuple:
    """Returns (subj_h, chapter_h, teacher_h) for Hindi polls."""
    subj_en    = (cls.get("subject_name") or "").strip()
    chapter_en = _clean_chapter_name(cls.get("chapter_name") or "")
    teacher_en = (cls.get("teacher_name") or "").strip()

    teacher_h = (cls.get("teacher_name_hindi") or teacher_en).strip()

    # Subject: static map first, LLM fallback
    subj_h = _SUBJECT_HINDI_MAP.get(subj_en.lower(), "")
    if not subj_h:
        cache_key = f"poll_subj_hi_{subj_en}"
        if st.session_state.get(cache_key):
            subj_h = st.session_state[cache_key]
        else:
            logger.info(f"[Poll] LLM translating subject: '{subj_en}'")
            try:
                _oc = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
                _resp = _oc.chat.completions.create(
                    model="gpt-5.4-mini",
                    max_tokens=20,
                    messages=[{"role": "user", "content": (
                        f"Translate this Indian school subject name to Hindi "
                        f"(Devanagari script only, no extra words): {subj_en}"
                    )}],
                )
                subj_h = _resp.choices[0].message.content.strip()
            except Exception as e:
                logger.warning(f"[Poll] Subject translate failed: {e}")
                subj_h = subj_en
            st.session_state[cache_key] = subj_h

    # Chapter: DB hindi_title first, LLM fallback
    chapter_h = _clean_chapter_name((cls.get("hindi_title") or "").strip())
    if chapter_h:
        logger.info(f"[Poll] Chapter from DB hindi_title: '{chapter_h}'")
    else:
        cache_key = f"poll_chap_hi_{chapter_en}"
        if st.session_state.get(cache_key):
            chapter_h = st.session_state[cache_key]
            logger.info(f"[Poll] Chapter from cache: '{chapter_h}'")
        else:
            logger.info(f"[Poll] LLM translating chapter: '{chapter_en}'")
            try:
                _oc = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
                _resp = _oc.chat.completions.create(
                    model="gpt-5.4-mini",
                    max_tokens=30,
                    messages=[{"role": "user", "content": (
                        f"Translate this Indian school chapter name to Hindi "
                        f"(Devanagari script only, no extra words): {chapter_en}"
                    )}],
                )
                chapter_h = _resp.choices[0].message.content.strip()
                logger.info(f"[Poll] Chapter LLM result: '{chapter_h}'")
            except Exception as e:
                logger.warning(f"[Poll] Chapter translate failed: {e}")
                chapter_h = chapter_en
            st.session_state[cache_key] = chapter_h

    return subj_h, chapter_h, teacher_h


def _today_poll_variations(cls):
    chapter = _clean_chapter_name(cls.get("chapter_name") or "")
    teacher = (cls.get("teacher_name") or "").strip()
    time    = _time_short(cls.get("class_time") or "")
    if _is_hindi_batch(cls):
        _, chapter_h, teacher_h = _translate_poll_names_to_hindi(cls)
        return [
            ("📚 Variation 1", f"आज {chapter_h} चैप्टर की लाइव क्लास है, तो कौन कौन आ रहा है? 🙋"),
            ("🧾 Variation 2", f"आज {chapter_h} चैप्टर की क्लास है 📖\nतो समय पर जॉइन करना मत भूलना 😉"),
            ("🎯 Variation 3", f"आज {teacher_h} की लाइव क्लास है 🚀\nतो कौन कौन जॉइन कर रहा है? 🙋"),
            ("⏰ Variation 4", f"आज {time} लाइव क्लास शुरू होगी ⏰\nतो जल्दी बताओ, कौन कौन आ रहा है? ✋"),
        ]
    return [
        ("📚 Variation 1", f"Aaj {chapter} ke chapter ki live class hai, toh kaun kaun aa raha hai? 🙋"),
        ("🧾 Variation 2", f"Aaj {chapter} chapter ki class hai 📖\nToh time par join karna mat bhulna 😉"),
        ("🎯 Variation 3", f"Aaj {teacher} Sir/Ma'am ki live class hai 🚀\nToh kaun kaun join kar raha hai? 🙋"),
        ("⏰ Variation 4", f"Aaj {time} live class start hogi ⏰\nToh jaldi batao, kaun kaun aa raha hai? ✋"),
    ]

def _yday_poll_variations(cls):
    chapter = _clean_chapter_name(cls.get("chapter_name") or "")
    teacher = (cls.get("teacher_name") or "").strip()
    if _is_hindi_batch(cls):
        _, chapter_h, teacher_h = _translate_poll_names_to_hindi(cls)
        return [
            ("🔥 Variation 1", f"बच्चों, {chapter_h} चैप्टर की क्लास अटेंड की थी ना? 😄\nअब बताओ, कितना समझ आया? 👇"),
            ("💬 Variation 2", f"बच्चों, {teacher_h} ने {chapter_h} चैप्टर पढ़ाया था 📖\nअब बताओ, कॉन्सेप्ट्स कितने समझ आए? 👇"),
            ("📋 Variation 3", f"बच्चों, {chapter_h} की सारी कक्षाएँ देख ली थीं ना? 😄\nअब बताओ, आपको अध्याय कितना समझ आया? 👇"),
        ]
    return [
        ("💬 Variation 1", f"Bacchon, {teacher} Sir ne {chapter} chapter padhaya tha 📖\nAb batao, concepts kitne samajh aaye? 👇"),
        ("🔥 Variation 2", f"Bacchon, {chapter} chapter ki class attend ki thi na? 😄\nAb batao, kitna samajh aaya? 👇"),
    ]

# 3A — Today's Class Poll
with _poll_tab_today:
    col_p1_form, col_p1_prev = st.columns([1, 1], gap="large")

    with col_p1_form:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("#### Today's Live Class")
        p1_test = st.toggle("🧪 Test mode", value=False, key="p1_test_toggle")
        p1_batch = st.text_input("Batch Code", placeholder="e.g. MPBSE_CLASS_12_PCMB_ENG_2027", key="p1_batch_input")
        p1_fetch = st.button("🔍 Fetch Today's Classes", key="p1_fetch_btn", use_container_width=True)

        if p1_fetch:
            if not p1_batch.strip():
                st.error("Please enter a batch code.")
            else:
                with st.spinner("Fetching..."):
                    try:
                        if p1_test:
                            classes = fetch_today_poll_class_test(p1_batch.strip())
                        else:
                            classes = fetch_today_poll_class(p1_batch.strip())
                        st.session_state["p1_classes"] = classes
                        st.session_state.pop("p1_auto_pick", None)
                        if classes:
                            st.success(f"Found {len(classes)} class(es).")
                        else:
                            st.warning("No classes found.")
                            st.session_state.pop("p1_classes", None)
                    except Exception as e:
                        st.error(f"Error: {e}")
                        logger.error(f"[Poll3A] fetch error: {e}")

        p1_selected = None
        if st.session_state.get("p1_classes"):
            import random as _random_p1
            _p1cls = st.session_state["p1_classes"]
            def _p1label(c):
                ts = c.get("start_ms")
                ds = _dt.fromtimestamp(ts / 1000).strftime("%d %b %Y") if ts else "—"
                return f"{c['chapter_name']}  ·  {c['subject_name']}  ·  {c['class_time']}  ·  {ds}"
            if p1_test:
                _p1opts = {_p1label(c): c for c in _p1cls}
                _p1lbl = st.selectbox("Select Class", list(_p1opts.keys()), key="p1_class_select")
                p1_selected = _p1opts[_p1lbl]
            else:
                if "p1_auto_pick" not in st.session_state or st.session_state.get("p1_auto_batch") != p1_batch.strip():
                    st.session_state["p1_auto_pick"] = _random_p1.choice(_p1cls)
                    st.session_state["p1_auto_batch"] = p1_batch.strip()
                p1_selected = st.session_state["p1_auto_pick"]
                st.caption(f"Auto-picked: **{_p1label(p1_selected)}**")

            _p1ts = p1_selected.get("start_ms")
            _p1date = _dt.fromtimestamp(_p1ts / 1000).strftime("%d %b %Y") if _p1ts else "—"
            pills = (
                f'<span class="info-pill">📚 {p1_selected["subject_name"]}</span>'
                f'<span class="info-pill">👨‍🏫 {p1_selected["teacher_name"] or "—"}</span>'
                f'<span class="info-pill">🕐 {p1_selected["class_time"]}</span>'
                f'<span class="info-pill">🗓 {_p1date}</span>'
            )
            st.markdown(f'<div style="margin:8px 0">{pills}</div>', unsafe_allow_html=True)

            _p1_vars = _today_poll_variations(p1_selected)
            _p1_var_labels = [v[0] for v in _p1_vars]
            _p1_var_sel = st.radio("Poll variation", _p1_var_labels, horizontal=True, key="p1_var_radio")
            _p1_hook = next(v[1] for v in _p1_vars if v[0] == _p1_var_sel)
            st.session_state["p1_hook"] = _p1_hook
            st.session_state["p1_selected_cls"] = p1_selected

        st.markdown("</div>", unsafe_allow_html=True)

    with col_p1_prev:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("#### Poll Preview")

        if st.session_state.get("p1_hook"):
            _hook_html = st.session_state["p1_hook"].replace('\n', '<br>')
            st.markdown(render_phone_poll(_hook_html, _p1_options(st.session_state.get("p1_selected_cls", {}))), unsafe_allow_html=True)
            st.text_area("Copy poll text", st.session_state["p1_hook"], height=60, key="p1_copy_text")
        else:
            st.markdown("""
            <div style="text-align:center;padding:60px 20px;color:#a0aec0;">
                <div style="font-size:48px;margin-bottom:16px;">📊</div>
                <p style="font-size:15px;font-weight:500;">Fetch today's classes<br>to see poll variations</p>
            </div>""", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

# 3B — Yesterday's Watch Check
with _poll_tab_yday:
    col_p2_form, col_p2_prev = st.columns([1, 1], gap="large")

    with col_p2_form:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("#### Yesterday's Covered Class")
        p2_test = st.toggle("🧪 Test mode", value=False, key="p2_test_toggle")
        p2_batch = st.text_input("Batch Code", placeholder="e.g. MPBSE_CLASS_12_PCMB_ENG_2027", key="p2_batch_input")
        p2_fetch = st.button("🔍 Fetch Yesterday's Classes", key="p2_fetch_btn", use_container_width=True)

        if p2_fetch:
            if not p2_batch.strip():
                st.error("Please enter a batch code.")
            else:
                with st.spinner("Fetching..."):
                    try:
                        if p2_test:
                            classes, days_ago = fetch_yesterday_watch_class_test(p2_batch.strip())
                        else:
                            classes, days_ago = fetch_yesterday_watch_class(p2_batch.strip())
                        st.session_state["p2_classes"] = classes
                        st.session_state["p2_days_ago"] = days_ago
                        st.session_state.pop("p2_auto_pick", None)
                        if classes:
                            st.success(f"Found {len(classes)} class(es) from yesterday.")
                        else:
                            st.warning("No classes found.")
                            st.session_state.pop("p2_classes", None)
                    except Exception as e:
                        st.error(f"Error: {e}")
                        logger.error(f"[Poll3B] fetch error: {e}")

        p2_selected = None
        if st.session_state.get("p2_classes"):
            import random as _random_p2
            _p2cls = st.session_state["p2_classes"]

            def _p2label(c):
                ts = c.get("start_ms")
                ds = _dt.fromtimestamp(ts / 1000).strftime("%d %b %Y") if ts else "—"
                return f"{c['chapter_name']}  ·  {c['subject_name']}  ·  {ds}"

            if p2_test:
                _p2opts = {_p2label(c): c for c in _p2cls}
                _p2sel = st.selectbox("Yesterday's Classes", list(_p2opts.keys()), key="p2_class_select")
                p2_selected = _p2opts[_p2sel]
            else:
                if "p2_auto_pick" not in st.session_state or st.session_state.get("p2_auto_batch") != p2_batch.strip():
                    st.session_state["p2_auto_pick"] = _random_p2.choice(_p2cls)
                    st.session_state["p2_auto_batch"] = p2_batch.strip()
                p2_selected = st.session_state["p2_auto_pick"]
                st.caption(f"Auto-picked: **{_p2label(p2_selected)}**")

            ts2 = p2_selected.get("start_ms")
            ds2 = _dt.fromtimestamp(ts2 / 1000).strftime("%d %b %Y") if ts2 else "—"
            pills2 = (
                f'<span class="info-pill">📚 {p2_selected["subject_name"]}</span>'
                f'<span class="info-pill">👨‍🏫 {p2_selected["teacher_name"] or "—"}</span>'
                f'<span class="info-pill">🗓 {ds2}</span>'
            )
            st.markdown(f'<div style="margin:8px 0">{pills2}</div>', unsafe_allow_html=True)

            _p2_vars = _yday_poll_variations(p2_selected)
            _p2_var_labels = [v[0] for v in _p2_vars]
            _p2_var_sel = st.radio("Poll variation", _p2_var_labels, horizontal=True, key="p2_var_radio")
            _p2_hook = next(v[1] for v in _p2_vars if v[0] == _p2_var_sel)
            st.session_state["p2_hook"] = _p2_hook
            st.session_state["p2_selected_cls"] = p2_selected

        st.markdown("</div>", unsafe_allow_html=True)

    with col_p2_prev:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("#### Poll Preview")

        if st.session_state.get("p2_hook"):
            _p2_hook_html = st.session_state["p2_hook"].replace('\n', '<br>')
            st.markdown(render_phone_poll(_p2_hook_html, _p2_options(st.session_state.get("p2_selected_cls", {}))), unsafe_allow_html=True)
            st.text_area("Copy poll text", st.session_state["p2_hook"], height=60, key="p2_copy_text")
        else:
            st.markdown("""
            <div style="text-align:center;padding:60px 20px;color:#a0aec0;">
                <div style="font-size:48px;margin-bottom:16px;">📊</div>
                <p style="font-size:15px;font-weight:500;">Fetch yesterday's classes<br>to see poll variations</p>
            </div>""", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)


# ── Category 11 — Common Mistake Alert ────────────────────────────────────────
import random as _random_m11

st.markdown("""
<div class="section-card" style="margin-top:28px;">
    <p class="section-label">Category 11 — Common Mistake Alert</p>
    <p class="section-title">Board Exam Mistake Alert</p>
    <p class="section-desc">Sent on Tuesday and Friday. Picks a recent chapter, searches for common board mistakes, and generates a punchy Hinglish alert.</p>
</div>
""", unsafe_allow_html=True)

col_m11_form, col_m11_prev = st.columns([1, 1], gap="large")

with col_m11_form:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown("#### Enter Batch Code")

    m11_batch = st.text_input(
        "Batch Code",
        placeholder="e.g. MPBSE_CLASS_12_PCM_ENG_2027",
        key="m11_batch_input",
    )

    m11_test = st.toggle("🧪 Test mode (fetch recent classes, any date)", value=False, key="m11_test_toggle")

    m11_fetch_label = "🔍 Fetch Recent Classes (Test)" if m11_test else "🔍 Fetch Classes (last 4 days)"
    m11_fetch_clicked = st.button(m11_fetch_label, key="m11_fetch_btn", use_container_width=True)

    if m11_fetch_clicked:
        if not m11_batch.strip():
            st.warning("Please enter a batch code first.")
        else:
            with st.spinner("Fetching from database..."):
                try:
                    if m11_test:
                        _m11_classes, _m11_days = _fetch_mistake_test(m11_batch.strip(), limit=5)
                    else:
                        _m11_classes, _m11_days = _fetch_mistake_prod(m11_batch.strip())
                    st.session_state["m11_classes"] = _m11_classes
                    st.session_state["m11_days"] = _m11_days
                    st.session_state.pop("m11_auto_pick", None)
                    if _m11_classes:
                        st.success(f"Found {len(_m11_classes)} class(es) from {_m11_days} day(s) ago.")
                    else:
                        st.warning("No classes found in last 4 days.")
                except Exception as e:
                    st.error(f"DB error: {e}")
                    logger.error(f"[M11] fetch error: {e}")

    _m11_classes = st.session_state.get("m11_classes", [])

    if _m11_classes:
        def _m11_label(c):
            return f"{c['chapter_name']} — {c['teacher_name']} ({c['subject_name']})"

        if m11_test:
            _m11_opts = {_m11_label(c): c for c in _m11_classes}
            _m11_sel = st.selectbox("Select class", list(_m11_opts.keys()), key="m11_class_select")
            m11_selected = dict(_m11_opts[_m11_sel])  # copy so we can override
            _m11_subj_override = st.text_input(
                "Subject Override (optional)",
                placeholder="e.g. History, Political Science, Geography",
                key="m11_subject_override",
            )
            _m11_chap_override = st.text_input(
                "Chapter Override (optional)",
                placeholder="e.g. Nationalism in India",
                key="m11_chapter_override",
            )
            _m11_fmt_choice = st.selectbox(
                "Format",
                options=["Auto (random)", "1 — Formula/Value", "2 — Humanities/Theory", "3 — Board Exam Question", "4 — Accounts Table"],
                key="m11_format_choice",
            )
            if _m11_subj_override.strip():
                m11_selected["subject_name"] = _m11_subj_override.strip()
            if _m11_chap_override.strip():
                m11_selected["chapter_name"] = _m11_chap_override.strip()
        else:
            if "m11_auto_pick" not in st.session_state or st.session_state.get("m11_auto_batch") != m11_batch.strip():
                st.session_state["m11_auto_pick"] = _random_m11.choice(_m11_classes)
                st.session_state["m11_auto_batch"] = m11_batch.strip()
            m11_selected = st.session_state["m11_auto_pick"]
            st.caption(f"Auto-picked: **{_m11_label(m11_selected)}**")

        st.markdown(
            f'<div style="margin:8px 0">'
            f'<span class="info-pill">📖 {m11_selected["chapter_name"]}</span>'
            f'<span class="info-pill">🔬 {m11_selected["subject_name"]}</span>'
            f'<span class="info-pill">👨‍🏫 {m11_selected["teacher_name"] or "—"}</span>'
            f'<span class="info-pill">🎓 {m11_selected["grade_name"]} · {m11_selected["stream_name"]}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)

    _m11_gen_enabled = bool(_m11_classes)
    m11_gen = st.button("✨ Generate Mistake Alert", key="m11_gen_btn", use_container_width=True, disabled=not _m11_gen_enabled)

with col_m11_prev:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown("#### Mistake Alert Preview")

    if m11_gen and _m11_classes:
        with st.spinner("Generating mistake card..."):
            try:
                import importlib.util as _m11_ilu
                _m11_lang_raw = (m11_selected.get("language") or "ENG")
                _m11_pb_folder = "hindi" if _m11_lang_raw.upper().startswith("HIN") else "english"
                _m11_pb_path = Path(__file__).parent / f"prompts/{_m11_pb_folder}/mistake/prompt_builder.py"
                _m11_spec = _m11_ilu.spec_from_file_location("mistake_prompt_builder", _m11_pb_path)
                _m11_pb = _m11_ilu.module_from_spec(_m11_spec)
                _m11_spec.loader.exec_module(_m11_pb)

                _m11_lang   = _m11_lang_raw
                _m11_medium = db_language_to_medium(_m11_lang)
                _bk_m11     = db_exam_to_board_key(m11_selected["exam_name"], m11_selected.get("exam_code"))
                _board_short_m11 = BOARD_SHORT.get(_bk_m11, "Board")
                _cl_m11     = db_grade_to_class(m11_selected["grade_name"])

                # If subject was overridden, clear hindi_title (irrelevant for overridden chapter)
                # and derive stream from the overridden subject so JSON context lookup is correct
                _m11_subj_active = m11_selected.get("subject_name", "")
                _subj_lo = _m11_subj_active.lower()
                if any(k in _subj_lo for k in ("account", "commerce", "economics", "business")):
                    _m11_stream_for_ctx = "Commerce"
                elif any(k in _subj_lo for k in ("history", "geography", "polity", "civics", "political", "sociology")):
                    _m11_stream_for_ctx = "Arts"
                elif any(k in _subj_lo for k in ("physics", "chemistry", "math", "maths")):
                    _m11_stream_for_ctx = "PCM"
                elif any(k in _subj_lo for k in ("biology", "botany", "zoology")):
                    _m11_stream_for_ctx = "PCB"
                else:
                    _m11_stream_for_ctx = m11_selected.get("stream_name", "")

                _m11_ht = "" if st.session_state.get("m11_chapter_override", "").strip() else (m11_selected.get("hindi_title") or "").strip()

                _m11_ctx, _m11_log = build_chapter_context(
                    chapter_name=m11_selected["chapter_name"],
                    hindi_title=_m11_ht,
                    subject_name=_m11_subj_active,
                    medium=_m11_medium,
                    grade_name=m11_selected["grade_name"],
                    stream_name=_m11_stream_for_ctx,
                    board_key=_bk_m11,
                )
                with st.expander("🔍 Chapter Context Log", expanded=False):
                    st.caption(f"**Status:** {_m11_log.get('status', '—')}")
                    if _m11_log.get("matched_chapter"):
                        st.caption(f"**Matched:** {_m11_log['matched_chapter']} (score={_m11_log.get('match_score', '—')})")
                    if _m11_log.get("fields_found"):
                        st.caption(f"**Fields:** {', '.join(_m11_log['fields_found'])}")
                    if _m11_ctx:
                        st.text(_m11_ctx)

                _fmt_sel = st.session_state.get("m11_format_choice", "Auto (random)")
                _force_fmt = None if _fmt_sel.startswith("Auto") else int(_fmt_sel.split("—")[0].strip())

                _m11_prompt, _m11_fmt = _m11_pb.build_mistake_html_prompt(
                    subject=_m11_subj_active,
                    chapter=m11_selected["chapter_name"],
                    class_level=_cl_m11,
                    board=_board_short_m11,
                    chapter_context=_m11_ctx,
                    stream=_m11_stream_for_ctx,
                    force_format=_force_fmt,
                )
                print(f"[M11 FMT] subject={m11_selected['subject_name']} chapter={m11_selected['chapter_name']} → format={_m11_fmt}")
                _m11_html_raw = generate_mistake_html(_m11_prompt, api_key)

                # Strip any accidental markdown fences the LLM may wrap around HTML
                import re as _re_m11
                _m11_html_raw = _m11_html_raw.strip()
                # Remove ```html ... ``` or ``` ... ``` wrappers
                _m11_html_raw = _re_m11.sub(r'^```[a-zA-Z]*\s*', '', _m11_html_raw)
                _m11_html_raw = _re_m11.sub(r'\s*```\s*$', '', _m11_html_raw)
                _m11_html_raw = _m11_html_raw.strip()

                st.session_state["m11_html"] = _m11_html_raw
                st.session_state.pop("m11_png", None)
                print(f"[M11] HTML length={len(_m11_html_raw)}, starts_with={repr(_m11_html_raw[:100])}")

                # Screenshot via Playwright
                import tempfile as _m11_tmp, subprocess as _m11_sub
                with _m11_tmp.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8") as _m11tf:
                    _m11tf.write(_m11_html_raw)
                    _m11_tf_path = _m11tf.name
                _m11_png_path = _m11_tf_path.replace(".html", ".png")
                _m11_script = f"""
import pathlib
from playwright.sync_api import sync_playwright
html_content = pathlib.Path(r"{_m11_tf_path}").read_text(encoding="utf-8")
print("[M11 PW] HTML length:", len(html_content))
print("[M11 PW] First 200 chars:", repr(html_content[:200]))
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(device_scale_factor=3, viewport={{"width": 560, "height": 900}})
    page.set_content(html_content, wait_until="networkidle")
    page.wait_for_timeout(1200)
    el = page.query_selector(".card") or page.query_selector("[class*='card']") or page.query_selector("body > div")
    print("[M11 PW] Element found:", el)
    if el:
        box = el.bounding_box()
        print("[M11 PW] Bounding box:", box)
        if box and box["width"] > 10 and box["height"] > 10:
            page.screenshot(path="{_m11_png_path}", clip={{"x": box["x"], "y": box["y"], "width": box["width"], "height": box["height"]}})
        else:
            print("[M11 PW] Box too small, falling back to full page")
            page.screenshot(path="{_m11_png_path}", full_page=True)
    else:
        print("[M11 PW] No element found, using full page screenshot")
        page.screenshot(path="{_m11_png_path}", full_page=True)
    browser.close()
"""
                _m11_res = _m11_sub.run(["/usr/local/bin/python3.11", "-c", _m11_script], capture_output=True, text=True)
                if _m11_res.returncode == 0:
                    with open(_m11_png_path, "rb") as _pf:
                        st.session_state["m11_png"] = _pf.read()
                    print(f"[M11] Screenshot saved: {_m11_png_path}")
                else:
                    st.error(f"Screenshot failed: {_m11_res.stderr[:300]}")
                    logger.error(f"[M11] playwright error: {_m11_res.stderr}")

                import os as _m11os
                for _fp in [_m11_tf_path, _m11_png_path]:
                    try: _m11os.remove(_fp)
                    except: pass

                logger.info(f"[M11] HTML card generated for '{m11_selected['chapter_name']}'")
            except Exception as e:
                st.error(f"Error: {e}")
                logger.error(f"[M11] generation error: {e}")

    if st.session_state.get("m11_html"):
        with st.expander("🔍 Raw HTML (debug)", expanded=False):
            st.code(st.session_state["m11_html"][:2000], language="html")

    if st.session_state.get("m11_png"):
        st.image(st.session_state["m11_png"], use_container_width=True)
        st.download_button(
            "⬇️ Download Mistake Card",
            data=st.session_state["m11_png"],
            file_name="mistake_card.png",
            mime="image/png",
            use_container_width=True,
        )
    else:
        st.markdown("""
        <div style="text-align:center;padding:60px 20px;color:#a0aec0;">
            <div style="font-size:48px;margin-bottom:16px;">⚠️</div>
            <p style="font-size:15px;font-weight:500;">Fetch classes,<br>then click Generate Mistake Alert</p>
        </div>""", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


# ── Category 9 — Quick Concept Card ──────────────────────────────────────────
import random as _random_c9

st.markdown("""
<div class="section-card" style="margin-top:28px;">
    <p class="section-label">Category 9 — Quick Concept Card</p>
    <p class="section-title">Daily Midday Concept</p>
    <p class="section-desc">Sent daily at midday. AI searches the web for the most board-exam-testable formula, reaction, date, or definition from the chapter.</p>
</div>
""", unsafe_allow_html=True)

col_c9_form, col_c9_prev = st.columns([1, 1], gap="large")

with col_c9_form:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown("#### Enter Batch Code")

    c9_mode = st.radio("Mode", ["Normal (auto-pick)", "Test (pick class)"], key="c9_mode", horizontal=True)
    c9_test = "Test" in c9_mode

    c9_batch = st.text_input("Batch Code", key="c9_batch", placeholder="e.g. MP2025BATCH01")
    c9_fetch = st.button("🔍 Fetch Batch", key="c9_fetch_btn", use_container_width=True)

    if c9_fetch and c9_batch.strip():
        with st.spinner("Fetching from DB..."):
            try:
                if c9_test:
                    _c9_classes, _c9_days = _fetch_mistake_test(c9_batch.strip(), limit=5)
                else:
                    _c9_classes, _c9_days = _fetch_mistake_prod(c9_batch.strip())
                st.session_state["c9_classes"] = _c9_classes
                st.session_state["c9_days"] = _c9_days
                if _c9_classes:
                    st.success(f"Found {len(_c9_classes)} class(es) from {_c9_days} day(s) ago.")
                else:
                    st.warning("No classes found for this batch.")
            except Exception as _e_c9:
                st.error(f"DB error: {_e_c9}")

    _c9_classes = st.session_state.get("c9_classes", [])

    if _c9_classes:
        def _c9_label(c):
            return f"{c.get('grade_name','')} | {c.get('subject_name','')} | {c.get('chapter_name','')}"

        if c9_test:
            _c9_opts = {_c9_label(c): c for c in _c9_classes}
            _c9_sel = st.selectbox("Select class", list(_c9_opts.keys()), key="c9_class_select")
            c9_selected = _c9_opts[_c9_sel]
        else:
            if "c9_auto_pick" not in st.session_state:
                st.session_state["c9_auto_pick"] = _random_c9.choice(_c9_classes)
            c9_selected = st.session_state["c9_auto_pick"]
            st.caption(f"Auto-picked: **{_c9_label(c9_selected)}**")

        _c9_lang = (c9_selected.get("language") or "ENG")
        _c9_medium = db_language_to_medium(_c9_lang)
        _c9_ht = (c9_selected.get("hindi_title") or "").strip()
        _c9_chapter = _c9_ht if _c9_medium == "Hindi" and _c9_ht else (c9_selected.get("chapter_name") or "")
        _c9_subject = c9_selected.get("subject_name") or ""
        _c9_stream = c9_selected.get("stream_name") or ""
        _c9_grade = c9_selected.get("grade_name") or ""

        st.caption(f"Medium: **{_c9_medium}** | Chapter: **{_c9_chapter}** | Subject: **{_c9_subject}**")

    _c9_gen_enabled = bool(_c9_classes)
    c9_gen = st.button("✨ Generate Concept Card", key="c9_gen_btn", use_container_width=True, disabled=not _c9_gen_enabled)

    st.markdown("</div>", unsafe_allow_html=True)

with col_c9_prev:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown("#### Preview")

    if c9_gen and _c9_classes:
        with st.spinner("Searching web + generating..."):
            try:
                _c9_key = get_concept_prompt_key(_c9_grade, _c9_stream, _c9_subject)
                _c9_tmpl = load_concept_prompt(_c9_key, _c9_medium)
                if not _c9_tmpl:
                    st.error(f"Prompt file not found for key: {_c9_key}")
                else:
                    _bk_c9 = db_exam_to_board_key(c9_selected["exam_name"], c9_selected.get("exam_code"))
                    _board_c9 = BOARD_SHORT.get(_bk_c9, "Board")
                    _cl_c9 = db_grade_to_class(c9_selected["grade_name"])
                    from collections import defaultdict as _defaultdict
                    _c9_prompt = _c9_tmpl.format_map(_defaultdict(str, {
                        "board": _board_c9,
                        "class_level": _cl_c9,
                        "subject": _c9_subject,
                        "chapter": _c9_chapter,
                        "stream": _c9_stream,
                        "hindi_title": _c9_ht,
                    }))
                    _c9_msg = generate_message(_c9_prompt, api_key)
                    st.session_state["c9_generated"] = _c9_msg
            except Exception as _e_c9g:
                st.error(f"Generation error: {_e_c9g}")

    if st.session_state.get("c9_generated"):
        import re as _re_c9
        _c9_raw = st.session_state["c9_generated"]
        _c9_html = _re_c9.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', _c9_raw, flags=_re_c9.DOTALL)
        _c9_html = _re_c9.sub(r'\*([^*\n]+)\*', r'<strong>\1</strong>', _c9_html)
        _c9_html = _c9_html.replace('\n', '<br>')
        st.markdown(
            f'<div style="background:#f5f5f7;border-radius:44px;padding:16px 12px;'
            f'border:8px solid #1d1d1f;max-width:360px;margin:0 auto;">'
            f'<div style="background:#eae6df;border-radius:32px;padding:12px 8px 8px 8px;">'
            f'<div class="wa-bubble-wrap"><div class="wa-bubble">{_c9_html}'
            f'<span class="wa-time">✓✓</span></div></div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown("""
        <div style="text-align:center;padding:60px 20px;color:#a0aec0;">
            <div style="font-size:48px;margin-bottom:16px;">⚠️</div>
            <p style="font-size:15px;font-weight:500;">Fetch classes,<br>then click Generate</p>
        </div>""", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


# ── Category F — Festival / Holiday Message ───────────────────────────────────
st.markdown("""
<div class="section-card" style="margin-top:28px;">
    <p class="section-label">Category 12 — Doubt Clearing</p>
    <p class="section-title">Doubt Clearing Reminder</p>
    <p class="section-desc">Sent once a week. AI picks a fresh hook angle every time — no fixed template. Optionally tie it to a recent chapter.</p>
</div>
""", unsafe_allow_html=True)

import random as _random_d12

col_d12_form, col_d12_prev = st.columns([1, 1], gap="large")

with col_d12_form:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown("#### Enter Batch Code")

    d12_test = st.toggle("🧪 Test mode (fetch recent classes, any date)", value=False, key="d12_test_toggle")

    d12_batch = st.text_input(
        "Batch Code",
        placeholder="e.g. MPBSE_CLASS_12_PCM_ENG_2027",
        key="d12_batch_input",
    )

    if not d12_test:
        _d12_weekday = date.today().weekday()
        _d12_is_sunday = _d12_weekday == 6
        if _d12_is_sunday:
            st.success("Today is Sunday — good day to send this.")
        else:
            _d12_days = (6 - _d12_weekday) % 7
            st.info(f"Recommended send day: Sunday ({_d12_days} day{'s' if _d12_days != 1 else ''} away). You can still generate now.")

    d12_fetch_label = "🔍 Fetch Recent Classes (Test)" if d12_test else "🔍 Fetch Classes (last 4 days)"
    d12_fetch_clicked = st.button(d12_fetch_label, key="d12_fetch_btn", use_container_width=True)

    if d12_fetch_clicked:
        if not d12_batch.strip():
            st.warning("Please enter a batch code first.")
        else:
            with st.spinner("Fetching from database..."):
                try:
                    if d12_test:
                        _d12_classes, _d12_days_ago = _fetch_mistake_test(d12_batch.strip(), limit=5)
                    else:
                        _d12_classes, _d12_days_ago = _fetch_mistake_prod(d12_batch.strip())
                    st.session_state["d12_classes"] = _d12_classes
                    st.session_state["d12_days"] = _d12_days_ago
                    st.session_state.pop("d12_auto_pick", None)
                    if _d12_classes:
                        st.success(f"Found {len(_d12_classes)} class(es) from {_d12_days_ago} day(s) ago.")
                    else:
                        st.warning("No classes found in last 4 days.")
                except Exception as e:
                    st.error(f"DB error: {e}")
                    logger.error(f"[D12] fetch error: {e}")

    _d12_classes = st.session_state.get("d12_classes", [])
    d12_selected = None

    if _d12_classes:
        def _d12_label(c):
            return f"{c['chapter_name']} — {c['subject_name']} ({c['grade_name']})"

        if d12_test:
            _d12_opts = {_d12_label(c): c for c in _d12_classes}
            _d12_sel = st.selectbox("Select class", list(_d12_opts.keys()), key="d12_class_select")
            d12_selected = _d12_opts[_d12_sel]
        else:
            if "d12_auto_pick" not in st.session_state or st.session_state.get("d12_auto_batch") != d12_batch.strip():
                st.session_state["d12_auto_pick"] = _random_d12.choice(_d12_classes)
                st.session_state["d12_auto_batch"] = d12_batch.strip()
            d12_selected = st.session_state["d12_auto_pick"]
            st.caption(f"Auto-picked: **{_d12_label(d12_selected)}**")

        if d12_selected:
            st.markdown(
                f'<div style="margin:8px 0">'
                f'<span class="info-pill">📖 {d12_selected["chapter_name"]}</span>'
                f'<span class="info-pill">🔬 {d12_selected["subject_name"]}</span>'
                f'<span class="info-pill">🎓 {d12_selected["grade_name"]}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown("</div>", unsafe_allow_html=True)

    d12_gen = st.button(
        "✨ Generate Doubt Clearing Message",
        key="d12_gen_btn",
        use_container_width=True,
        disabled=d12_selected is None,
    )

with col_d12_prev:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown("#### Doubt Message Preview")

    if d12_gen and d12_selected:
        with st.spinner("Generating doubt clearing message..."):
            try:
                _d12_lang = (d12_selected.get("language") or "ENG")
                _d12_medium = db_language_to_medium(_d12_lang)
                _d12_ht = (d12_selected.get("hindi_title") or "").strip()
                _d12_chapter = _d12_ht if (_d12_medium == "Hindi" and _d12_ht) else d12_selected["chapter_name"]

                _d12_template = load_doubt_prompt(_d12_medium)
                if not _d12_template:
                    st.error("Doubt clearing prompt file not found.")
                else:
                    _d12_prompt = _d12_template.format(chapter=_d12_chapter)
                    _d12_msg = generate_message(_d12_prompt, api_key)
                    st.session_state["d12_generated"] = _d12_msg
                    st.session_state["d12_chapter_used"] = _d12_chapter
                    st.session_state["d12_medium_used"] = _d12_medium
                    logger.info(f"[D12] Generated  medium={_d12_medium}  chapter='{_d12_chapter}'")
            except Exception as e:
                st.error(f"Error: {e}")
                logger.error(f"[D12] generation error: {e}")

    if "d12_generated" in st.session_state:
        import re as _re_d12
        _d12_raw = st.session_state["d12_generated"]
        _d12_html = _re_d12.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', _d12_raw, flags=_re_d12.DOTALL)
        _d12_html = _re_d12.sub(r'\*([^*\n]+)\*', r'<strong>\1</strong>', _d12_html)
        _d12_html = _d12_html.replace('\n', '<br>')
        st.markdown(
            f'<div style="background:#f5f5f7;border-radius:44px;padding:16px 12px;'
            f'border:8px solid #1d1d1f;max-width:360px;margin:0 auto;">'
            f'<div style="background:#eae6df;border-radius:32px;padding:12px 8px 8px 8px;">'
            f'<div class="wa-bubble-wrap"><div class="wa-bubble">{_d12_html}'
            f'<span class="wa-time">✓✓</span></div></div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )
        st.markdown("---")
        st.caption(
            f"**{st.session_state.get('d12_chapter_used', '')}** · "
            f"{st.session_state.get('d12_medium_used', '')}"
        )
    else:
        st.markdown("""
        <div style="text-align:center;padding:60px 20px;color:#a0aec0;">
            <div style="font-size:48px;margin-bottom:16px;">🙋</div>
            <p style="font-size:15px;font-weight:500;">Fetch a batch, then click Generate —<br>AI picks a fresh angle every time</p>
        </div>""", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


# ── Category F — Festival / Holiday Message ───────────────────────────────────
st.markdown("""
<div class="section-card" style="margin-top:28px;">
    <p class="section-label">Category F — Festival / Holiday</p>
    <p class="section-title">Festival & Holiday Message</p>
    <p class="section-desc">Sent on festival and national holiday days. Auto-detects today's festival from the calendar. Use test mode to preview any festival.</p>
</div>
""", unsafe_allow_html=True)

col_fest_form, col_fest_prev = st.columns([1, 1], gap="large")

with col_fest_form:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown("#### Enter Batch Code")

    fest_test = st.toggle("🧪 Test mode (pick any festival)", value=False, key="fest_test_toggle")

    fest_batch = st.text_input(
        "Batch Code",
        placeholder="e.g. MPBSE_CLASS_12_PCM_ENG_2027",
        key="fest_batch_input",
    )

    fest_fetch_clicked = st.button("🔍 Fetch Batch Medium", key="fest_fetch_btn", use_container_width=True)

    if fest_fetch_clicked:
        if not fest_batch.strip():
            st.warning("Please enter a batch code first.")
        else:
            with st.spinner("Fetching batch info..."):
                try:
                    if fest_test:
                        _fest_classes, _ = _fetch_mistake_test(fest_batch.strip(), limit=1)
                    else:
                        _fest_classes, _ = _fetch_mistake_prod(fest_batch.strip())
                    if _fest_classes:
                        _fest_lang = db_language_to_medium(_fest_classes[0].get("language", "ENG"))
                        st.session_state["fest_medium"] = _fest_lang
                        st.session_state["fest_batch"] = fest_batch.strip()
                        st.success(f"Batch medium: **{_fest_lang}**")
                    else:
                        st.warning("No classes found — defaulting to English.")
                        st.session_state["fest_medium"] = "English"
                        st.session_state["fest_batch"] = fest_batch.strip()
                except Exception as e:
                    st.error(f"DB error: {e}")
                    logger.error(f"[Fest] fetch error: {e}")

    _fest_medium = st.session_state.get("fest_medium", "")
    if _fest_medium:
        st.markdown(
            f'<div style="margin:6px 0"><span class="info-pill green">Medium: {_fest_medium}</span></div>',
            unsafe_allow_html=True,
        )

    _fest_selected = None

    if fest_test:
        _all_festivals = get_all_festivals_sorted()
        _fest_opts = {f"{f['name']}  ·  {f['date']}  ({f['type']})": f for f in _all_festivals}
        _fest_sel_label = st.selectbox("Select Festival", list(_fest_opts.keys()), key="fest_select")
        _fest_selected = _fest_opts[_fest_sel_label]
    else:
        _today_festival = get_festival_for_date()
        if _today_festival:
            st.success(f"🎉 Today is **{_today_festival['name']}** ({_today_festival['date']})")
            _fest_selected = _today_festival
        else:
            _today_str = date.today().strftime("%d %B %Y")
            st.info(f"No festival today ({_today_str}). Enable test mode to pick one.")

    if _fest_selected:
        st.markdown(
            f'<div style="margin:8px 0">'
            f'<span class="info-pill">🎊 {_fest_selected["name"]}</span>'
            f'<span class="info-pill">{_fest_selected["hindi"]}</span>'
            f'<span class="info-pill orange">{_fest_selected["type"]}</span>'
            f'<span class="info-pill">📅 {_fest_selected["date"]}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)

    fest_img_gen = st.button(
        "🎨 Generate Festival Image",
        key="fest_img_gen_btn",
        use_container_width=True,
        disabled=(_fest_selected is None),
    )

with col_fest_prev:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown("#### Festival Image Preview")

    if fest_img_gen and _fest_selected:
        with st.spinner("Generating festival image..."):
            try:
                from google import genai as _gai
                from google.genai import types as _gtypes

                _gemini_key = os.getenv("GEMINI_API_KEY", "")
                if not _gemini_key:
                    st.error("GEMINI_API_KEY not set in environment.")
                else:
                    _img_client = _gai.Client(api_key=_gemini_key)

                    # Reference images of Ritesh Sir
                    _ref_parts = []
                    for _rname in ["Ritesh.png", "RITESH1.png"]:
                        _rp = BASE_DIR / "assets" / _rname
                        if _rp.exists():
                            _ref_parts.append(
                                _gtypes.Part(
                                    inline_data=_gtypes.Blob(
                                        data=_rp.read_bytes(),
                                        mime_type="image/png",
                                    )
                                )
                            )

                    # Build prompt
                    _img_prompt_base = (BASE_DIR / "prompts" / "english" / "festival.txt").read_text(encoding="utf-8").strip()
                    _img_prompt = f"Festival: {_fest_selected['name']}\n\n{_img_prompt_base}"

                    _img_response = _img_client.models.generate_content(
                        model="gemini-3-pro-image-preview",
                        contents=[
                            _gtypes.Content(
                                role="user",
                                parts=_ref_parts + [_gtypes.Part(text=_img_prompt)],
                            )
                        ],
                        config=_gtypes.GenerateContentConfig(
                            response_modalities=["IMAGE", "TEXT"],
                        ),
                    )

                    _img_bytes = None
                    _candidates = _img_response.candidates or []
                    logger.info(f"[Fest Image] candidates={len(_candidates)}")
                    for _cand in _candidates:
                        _content = getattr(_cand, "content", None)
                        _parts = getattr(_content, "parts", None) or []
                        logger.info(f"[Fest Image] parts={len(_parts)}")
                        for _part in _parts:
                            _idata = getattr(_part, "inline_data", None)
                            if _idata and getattr(_idata, "data", None):
                                _img_bytes = _idata.data
                                logger.info(f"[Fest Image] mime={getattr(_idata,'mime_type','?')} size={len(_img_bytes)}")
                                break
                        if _img_bytes:
                            break

                    if not _img_bytes:
                        # Log full response for debugging
                        logger.warning(f"[Fest Image] full response: {_img_response}")
                        st.error("No image in Gemini response. Check logs for details.")
                    else:
                        st.session_state["fest_image"] = _img_bytes
                        st.session_state["fest_image_name"] = _fest_selected["name"]
                        logger.info(f"[Fest Image] Generated for '{_fest_selected['name']}'")

            except Exception as e:
                st.error(f"Image generation error: {e}")
                logger.error(f"[Fest Image] error: {e}")

    if "fest_image" in st.session_state:
        st.image(st.session_state["fest_image"], width="stretch")
        st.download_button(
            label="⬇️ Download Image",
            data=st.session_state["fest_image"],
            file_name=f"festival_{st.session_state.get('fest_image_name','').replace(' ','_')}.png",
            mime="image/png",
            use_container_width=True,
        )
    else:
        st.markdown("""
        <div style="text-align:center;padding:60px 20px;color:#a0aec0;">
            <div style="font-size:48px;margin-bottom:16px;">🎉</div>
            <p style="font-size:15px;font-weight:500;">Select a festival and click<br>Generate Festival Image</p>
        </div>""", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


# ── Category T — Topper Image ─────────────────────────────────────────────────
st.markdown("""
<div class="section-card">
    <p class="section-label">Category T — Topper Spotlight</p>
    <p class="section-title">Topper Image Generator</p>
    <p class="section-desc">Generates a webtoon-style image of Ritesh Sir interviewing a board exam topper. Enter the batch code to auto-detect stream/class/medium, then fill in student details.</p>
</div>
""", unsafe_allow_html=True)

_t_col_left, _t_col_right = st.columns([1, 1])

with _t_col_left:
    st.markdown('<div class="card">', unsafe_allow_html=True)

    _t_batch = st.text_input("Batch Code", placeholder="e.g. BATCH001", key="topper_batch_code")
    _t_fetch_btn = st.button("🔍 Fetch Batch Info", key="topper_fetch_btn", use_container_width=True)

    if _t_fetch_btn:
        if not _t_batch.strip():
            st.warning("Enter a batch code first.")
        else:
            with st.spinner("Fetching batch info..."):
                try:
                    _t_meta = _fetch_batch_meta(_t_batch.strip())
                    if not _t_meta:
                        st.error("Batch not found.")
                    else:
                        st.session_state["topper_meta"] = _t_meta
                        st.session_state.pop("topper_image", None)
                        _t_key = _topper_file_key(
                            _t_meta.get("grade_name", ""),
                            _t_meta.get("stream_name", ""),
                            _t_meta.get("language", "ENG"),
                        )
                        st.session_state["topper_file_key"] = _t_key
                        st.success(
                            f"✅ Grade: **{_t_meta.get('grade_name')}** · "
                            f"Stream: **{_t_meta.get('stream_name')}** · "
                            f"Medium: **{db_language_to_medium(_t_meta.get('language','ENG'))}**"
                        )
                        st.caption(f"Image key: `{_t_key}`")
                except Exception as _te:
                    st.error(f"DB error: {_te}")

    if st.session_state.get("topper_meta"):
        _t_meta_cur = st.session_state["topper_meta"]
        _t_key_cur  = st.session_state.get("topper_file_key", "")

        _t_board = db_exam_to_board_key(
            _t_meta_cur.get("exam_name", ""),
            _t_meta_cur.get("exam_code", ""),
        ).upper()

        _t_name = st.text_input("Student Name", placeholder="e.g. Rahul Sharma", key="topper_name")

        # Load Q&A from CSV
        _t_csv_path = BASE_DIR / "toppers" / "sheets" / f"{_t_key_cur}.csv"
        _t_qa_pairs = []
        if _t_csv_path.exists():
            import csv as _csv
            with open(_t_csv_path, encoding="utf-8") as _tf:
                for _row in _csv.reader(_tf):
                    if len(_row) >= 2 and _row[0].strip():
                        _t_qa_pairs.append((_row[0].strip(), _row[1].strip()))
            st.caption(f"📋 {len(_t_qa_pairs)} Q&A pairs loaded from CSV")
        else:
            st.warning(f"No CSV found for key `{_t_key_cur}` — Q&A will be blank.")

        _t_gen_btn = st.button(
            "🎨 Generate Topper Image",
            key="topper_gen_btn",
            use_container_width=True,
            disabled=(not _t_name.strip()),
        )
    else:
        _t_gen_btn = False
        _t_name = ""
        _t_board = ""
        _t_key_cur = ""
        _t_qa_pairs = []
        _t_meta_cur = {}

    st.markdown("</div>", unsafe_allow_html=True)

with _t_col_right:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown("#### Topper Image Preview")

    if _t_gen_btn and st.session_state.get("topper_meta"):
        with st.spinner("Generating topper image..."):
            try:
                import random as _rand
                from google import genai as _gai
                from google.genai import types as _gtypes

                _gemini_key = os.getenv("GEMINI_API_KEY", "")
                if not _gemini_key:
                    st.error("GEMINI_API_KEY not set.")
                else:
                    # Pick random Q&A
                    if _t_qa_pairs:
                        _t_q, _t_a = _rand.choice(_t_qa_pairs)
                    else:
                        _t_q = "Padhai kaise ki?"
                        _t_a = "Regular revision aur practice se."

                    # Load topper reference image
                    _t_img_path = BASE_DIR / "toppers" / "images" / f"{_t_key_cur}.png"
                    _t_ref_parts = []

                    # Ritesh Sir photos first
                    for _rname in ["Ritesh.png", "RITESH1.png"]:
                        _rp = BASE_DIR / "assets" / _rname
                        if _rp.exists():
                            _t_ref_parts.append(
                                _gtypes.Part(
                                    inline_data=_gtypes.Blob(
                                        data=_rp.read_bytes(),
                                        mime_type="image/png",
                                    )
                                )
                            )

                    # Topper student photo
                    if _t_img_path.exists():
                        _t_ref_parts.append(
                            _gtypes.Part(
                                inline_data=_gtypes.Blob(
                                    data=_t_img_path.read_bytes(),
                                    mime_type="image/png",
                                )
                            )
                        )
                    else:
                        st.warning(f"Topper image not found: `{_t_img_path.name}` — generating without it.")

                    # Build prompt
                    _t_guidance = (BASE_DIR / "prompts" / "english" / "toppers_guidance.txt").read_text(encoding="utf-8").strip()
                    _t_stream_label = _t_meta_cur.get("stream_name") or "PCB"
                    _t_medium_label = db_language_to_medium(_t_meta_cur.get("language", "ENG"))
                    _t_prompt = (
                        _t_guidance
                        .replace("{{NAME}}", _t_name.strip())
                        .replace("{{STREAM}}", _t_stream_label)
                        .replace("{{MEDIUM}}", _t_medium_label)
                        .replace("{{BOARD}}", _t_board)
                        .replace("{{ACHIEVEMENT}}", "Board Topper")
                        .replace("{{QUESTION}}", _t_q)
                        .replace("{{ANSWER}}", _t_a)
                    )

                    _t_client = _gai.Client(api_key=_gemini_key)
                    _t_response = _t_client.models.generate_content(
                        model="gemini-3-pro-image-preview",
                        contents=[
                            _gtypes.Content(
                                role="user",
                                parts=_t_ref_parts + [_gtypes.Part(text=_t_prompt)],
                            )
                        ],
                        config=_gtypes.GenerateContentConfig(
                            response_modalities=["IMAGE", "TEXT"],
                        ),
                    )

                    _t_img_bytes = None
                    for _cand in (_t_response.candidates or []):
                        _content = getattr(_cand, "content", None)
                        for _part in (getattr(_content, "parts", None) or []):
                            _idata = getattr(_part, "inline_data", None)
                            if _idata and getattr(_idata, "data", None):
                                _t_img_bytes = _idata.data
                                break
                        if _t_img_bytes:
                            break

                    if not _t_img_bytes:
                        logger.warning(f"[Topper Image] full response: {_t_response}")
                        st.error("No image in Gemini response. Check logs.")
                    else:
                        st.session_state["topper_image"] = _t_img_bytes
                        st.session_state["topper_image_name"] = _t_name.strip()
                        logger.info(f"[Topper Image] Generated for '{_t_name}' key='{_t_key_cur}'")

            except Exception as _te2:
                st.error(f"Image generation error: {_te2}")
                logger.error(f"[Topper Image] error: {_te2}")

    if "topper_image" in st.session_state:
        st.image(st.session_state["topper_image"], width="stretch")
        st.download_button(
            label="⬇️ Download Image",
            data=st.session_state["topper_image"],
            file_name=f"topper_{st.session_state.get('topper_image_name','').replace(' ','_')}.png",
            mime="image/png",
            use_container_width=True,
        )
    else:
        st.markdown("""
        <div style="text-align:center;padding:60px 20px;color:#a0aec0;">
            <div style="font-size:48px;margin-bottom:16px;">🏆</div>
            <p style="font-size:15px;font-weight:500;">Fetch batch info, fill student details<br>and click Generate Topper Image</p>
        </div>""", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


# ── Category W — Weekly Schedule (HTML Timetable) ─────────────────────────────
st.markdown("""
<div class="section-card">
    <p class="section-label">Category W — Weekly Schedule</p>
    <p class="section-title">Weekly Timetable</p>
    <p class="section-desc">Generates a visual HTML timetable with Subject · Chapter · Teacher per cell. Screenshot saved as PNG — ready to share on WhatsApp.</p>
</div>
""", unsafe_allow_html=True)

st.markdown("<div class='card'>", unsafe_allow_html=True)

_w_batch = st.text_input("Batch Code", placeholder="e.g. BATCH001", key="w_batch_code")
_w_test  = st.toggle("🧪 Test mode (fetch recent classes, any date)", value=False, key="w_test_mode")
if _w_test:
    st.caption("Test mode: fetches last 15 classes grouped by weekday.")
else:
    st.caption("Normal mode: fetches all classes for Mon–Sat of the current week.")

_w_fetch_label   = "🔍 Fetch Recent Classes (Test)" if _w_test else "🔍 Fetch This Week's Schedule"
_w_fetch_clicked = st.button(_w_fetch_label, key="w_fetch_btn", use_container_width=True)

if _w_fetch_clicked:
    if not _w_batch.strip():
        st.warning("Enter a batch code first.")
    else:
        with st.spinner("Fetching schedule..."):
            try:
                if _w_test:
                    _w_classes = _fetch_week_test(_w_batch.strip(), limit=15)
                else:
                    _w_classes = _fetch_week_prod(_w_batch.strip())
                st.session_state["w_classes"]         = _w_classes
                st.session_state["w_fetched_in_test"] = _w_test
                st.session_state.pop("w_timetable_png", None)
                st.session_state.pop("w_timetable_html", None)
                if _w_classes:
                    st.success(f"✅ Found {len(_w_classes)} class(es).")
                else:
                    st.warning("No classes found. Try test mode or check the batch code.")
            except Exception as e:
                st.error(f"DB error: {e}")
                logger.error(f"[Weekly] fetch error: {e}")

if st.session_state.get("w_classes"):
    _wc       = st.session_state["w_classes"]
    _w_lang   = (_wc[0].get("language") or "ENG")
    _w_medium = db_language_to_medium(_w_lang)
    st.caption(f"Medium: **{_w_medium}** · {len(_wc)} class(es) found")

    _w_gen = st.button("🖼️ Generate Timetable Image", key="w_gen_btn", use_container_width=True)
    if _w_gen:
        # ── Build slot → day grid ────────────────────────────────────────────
        from datetime import datetime, timezone, timedelta
        _IST = timezone(timedelta(hours=5, minutes=30))

        # ── Hindi medium: translate missing chapter + teacher + subject names via LLM ────
        if _w_medium == "Hindi":
            _needs = [
                c for c in _wc
                if not (c.get("hindi_title") or "").strip()
                or not (c.get("teacher_name_hindi") or "").strip()
            ]
            # subjects never have a Hindi field in DB — always translate them
            _unique_subjects = list({c.get("subject_name", "") for c in _wc if c.get("subject_name")})

            if _needs or _unique_subjects:
                _entries = []
                for _c in _needs:
                    _ch = _c["chapter_name"] if not ((_c.get("hindi_title") or "").strip()) else None
                    _th = _c["teacher_name"] if not ((_c.get("teacher_name_hindi") or "").strip()) else None
                    _entries.append({"chapter": _ch, "teacher": _th})

                _unique_chapters = list({e["chapter"] for e in _entries if e["chapter"]})
                _unique_teachers = list({e["teacher"] for e in _entries if e["teacher"]})

                _trans_prompt = (
                    "Return a JSON object with three keys:\n"
                    "1. \"chapters\": map each English chapter name to its official Hindi (Devanagari) name "
                    "as it appears in NCERT/board Hindi medium textbooks. Use exact official title, not word-by-word translation.\n"
                    "2. \"teachers\": map each English teacher name to its Devanagari transliteration "
                    "(e.g. 'Amber Sir' → 'अम्बर सर', 'Hardik Sir' → 'हार्दिक सर', 'Ms. Priya' → 'प्रिया मैम').\n"
                    "3. \"subjects\": map each English subject name to its standard Hindi (Devanagari) name "
                    "(e.g. 'Physics' → 'भौतिकी', 'Chemistry' → 'रसायन विज्ञान', 'Mathematics' → 'गणित', "
                    "'Biology' → 'जीव विज्ञान', 'Accountancy' → 'लेखाशास्त्र', 'Economics' → 'अर्थशास्त्र', "
                    "'English' → 'अंग्रेज़ी', 'Hindi' → 'हिंदी').\n\n"
                    f"Chapters:\n" + "\n".join(f"- {n}" for n in _unique_chapters) +
                    f"\n\nTeachers:\n" + "\n".join(f"- {n}" for n in _unique_teachers) +
                    f"\n\nSubjects:\n" + "\n".join(f"- {n}" for n in _unique_subjects)
                )
                try:
                    _trans_resp = generate_message(_trans_prompt, api_key)
                    import json as _wjson, re as _wjre
                    _jm = _wjre.search(r'\{.*\}', _trans_resp, _wjre.DOTALL)
                    _trans_data: dict = _wjson.loads(_jm.group()) if _jm else {}
                except Exception as _te:
                    _trans_data = {}
                    logger.warning(f"[Weekly] translation failed: {_te}")

                _ch_map = _trans_data.get("chapters", {})
                _th_map = _trans_data.get("teachers", {})
                _subj_map = _trans_data.get("subjects", {})

                for _cls in _wc:
                    if not ((_cls.get("hindi_title") or "").strip()):
                        _cls["hindi_title"] = _ch_map.get(_cls["chapter_name"], _cls["chapter_name"])
                    if not ((_cls.get("teacher_name_hindi") or "").strip()):
                        _cls["teacher_name_hindi"] = _th_map.get(_cls["teacher_name"], _cls["teacher_name"])
                    # subject_name_hindi always set from translation (fallback to English)
                    _cls["subject_name_hindi"] = _subj_map.get(_cls.get("subject_name", ""), _cls.get("subject_name", ""))

        def _fmt_time(ms):
            if not ms:
                return ""
            _t = datetime.fromtimestamp(ms / 1000, tz=_IST)
            return _t.strftime("%-I:%M %p")

        # Color rotation per subject (8 palette colors, teal first)
        _subj_colors: dict = {}
        _color_cycle = ["c1","c2","c3","c4","c5","c6","c7","c8"]
        _color_idx   = 0
        for _cls in sorted(_wc, key=lambda x: x.get("subject_name","")):
            _sn = _cls.get("subject_name","")
            if _sn not in _subj_colors:
                _subj_colors[_sn] = _color_cycle[_color_idx % len(_color_cycle)]
                _color_idx += 1

        # ── Build vertical HTML (day by day) ────────────────────────────────
        from collections import defaultdict as _wdd2
        _DAY_FULL = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
        _DAY_SHORT = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]

        # group by weekday
        _by_day: dict = _wdd2(list)
        for _cls in _wc:
            _by_day[_cls["weekday"]].append(_cls)

        def _color_css(c):
            _colors = {
                "c1": ("#e0f7f5","#26a69a","#00796b","#004d40"),
                "c2": ("#e8f4ff","#5b9bd5","#1565c0","#0d47a1"),
                "c3": ("#f5eeff","#b39ddb","#7e57c2","#4527a0"),
                "c4": ("#fff4e6","#ffa726","#e65100","#bf360c"),
                "c5": ("#edf7ee","#66bb6a","#2e7d32","#1b5e20"),
                "c6": ("#ffecee","#ef5350","#c62828","#b71c1c"),
                "c7": ("#fffde7","#ffca28","#f57f17","#e65100"),
                "c8": ("#f3f9e8","#9ccc65","#558b2f","#33691e"),
            }
            return _colors.get(c, _colors["c1"])

        def _class_card(cls_dict):
            subj_en = cls_dict.get("subject_name", "")   # English key — used for color lookup
            subj    = (cls_dict.get("subject_name_hindi") or subj_en).strip() if _w_medium == "Hindi" else subj_en
            chapter = (cls_dict.get("hindi_title") or cls_dict.get("chapter_name","")).strip() if _w_medium == "Hindi" else cls_dict.get("chapter_name","")
            teacher = (cls_dict.get("teacher_name_hindi") or cls_dict.get("teacher_name","")).strip() if _w_medium == "Hindi" else cls_dict.get("teacher_name","")
            start_t = _fmt_time(cls_dict.get("start_ms"))
            end_t   = _fmt_time(cls_dict.get("end_ms")) if cls_dict.get("end_ms") else ""
            time_str = f"{start_t} – {end_t}" if end_t else start_t
            color   = _subj_colors.get(subj_en, "c1")   # always look up by English name
            bg, border, subj_col, chap_col = _color_css(color)
            return (
                f'<div style="background:{bg};border-left:4px solid {border};border-radius:14px;'
                f'padding:12px 14px;margin-bottom:10px;display:flex;align-items:center;gap:12px;'
                f'box-shadow:0 2px 8px rgba(0,0,0,0.06);">'
                f'<div style="background:{border};color:white;border-radius:9px;padding:7px 10px;'
                f'font-size:11px;font-weight:700;white-space:nowrap;min-width:76px;text-align:center;'
                f'line-height:1.3;box-shadow:0 2px 4px rgba(0,0,0,0.12);">'
                f'{time_str}</div>'
                f'<div style="flex:1;">'
                f'<div style="font-size:9px;font-weight:800;color:{subj_col};text-transform:uppercase;letter-spacing:0.08em;margin-bottom:3px;">{subj}</div>'
                f'<div style="font-size:13px;font-weight:700;color:{chap_col};line-height:1.35;">{chapter}</div>'
                f'<div style="font-size:10px;color:#777;margin-top:4px;font-weight:500;">👤 {teacher}</div>'
                f'</div></div>'
            )

        _days_html = ""
        for _di in sorted(_by_day.keys()):
            _day_classes = sorted(_by_day[_di], key=lambda x: x["start_ms"])
            _day_name  = _DAY_FULL[_di]
            _day_short = _DAY_SHORT[_di]
            _days_html += (
                f'<div style="margin-bottom:20px;">'
                f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
                f'<div style="background:#00897b;color:white;border-radius:8px;padding:4px 12px;'
                f'font-size:11px;font-weight:800;letter-spacing:0.06em;'
                f'box-shadow:0 2px 6px rgba(0,137,123,0.25);">{_day_short}</div>'
                f'<div style="font-size:14px;font-weight:800;color:#00695c;letter-spacing:0.01em;">{_day_name}</div>'
                f'<div style="flex:1;height:1.5px;background:linear-gradient(90deg,#b2dfdb,transparent);border-radius:2px;"></div>'
                f'</div>'
            )
            for _c in _day_classes:
                _days_html += _class_card(_c)
            _days_html += '</div>'

        _w_tmpl = (Path(__file__).parent / "templates" / "weekly_timetable.html").read_text(encoding="utf-8")
        _html = _w_tmpl.replace("{{days_html}}", _days_html)

        st.session_state["w_timetable_html"] = _html

        # ── Screenshot via Playwright ────────────────────────────────────────
        import tempfile, subprocess, sys
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8") as _tf:
            _tf.write(_html)
            _tf_path = _tf.name

        _png_path = _tf_path.replace(".html", ".png")
        _screenshot_script = f"""
import pathlib
from playwright.sync_api import sync_playwright
html_content = pathlib.Path(r"{_tf_path}").read_text(encoding="utf-8")
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(device_scale_factor=3)
    page.set_content(html_content, wait_until="networkidle")
    page.wait_for_timeout(500)
    wrapper = page.query_selector(".wrapper")
    wrapper.screenshot(path="{_png_path}")
    browser.close()
"""
        _py = "/usr/local/bin/python3.11"
        print(f"\n[Weekly] Taking screenshot → {_png_path}")
        _result = subprocess.run([_py, "-c", _screenshot_script], capture_output=True, text=True)
        if _result.returncode == 0:
            print(f"[Weekly] Screenshot saved: {_png_path}")
            with open(_png_path, "rb") as _pf:
                _png_bytes = _pf.read()
            st.session_state["w_timetable_png"] = _png_bytes

            # ── Upload to S3 ─────────────────────────────────────────────────
            import boto3 as _boto3, os as _os
            from datetime import datetime as _dt
            _s3_bucket = "mldatabase"
            _s3_region = _os.getenv("AWS_REGION", "ap-south-1")
            _s3_key    = f"virtual_chat_responses/weeklySchedule/{_dt.now().strftime('%Y%m%d_%H%M%S')}_{_w_batch.strip()}.png"
            print(f"\n[Weekly] ── S3 Upload ──────────────────────────────")
            print(f"[Weekly] Bucket : {_s3_bucket}")
            print(f"[Weekly] Key    : {_s3_key}")
            print(f"[Weekly] Region : {_s3_region}")
            print(f"[Weekly] Uploading...")
            try:
                _s3 = _boto3.client(
                    "s3",
                    region_name=_s3_region,
                    aws_access_key_id=_os.getenv("AWS_ACCESS_KEY_ID"),
                    aws_secret_access_key=_os.getenv("AWS_SECRET_ACCESS_KEY"),
                )
                _s3.put_object(
                    Bucket=_s3_bucket,
                    Key=_s3_key,
                    Body=_png_bytes,
                    ContentType="image/png",
                )
                _s3_url = f"https://{_s3_bucket}.s3.{_s3_region}.amazonaws.com/{_s3_key}"
                st.session_state["w_timetable_s3_url"] = _s3_url
                print(f"[Weekly] ✅ Upload successful!")
                print(f"[Weekly] 🔗 Pre-signed URL (7 days): {_s3_url}")
                print(f"[Weekly] ────────────────────────────────────────")
                logger.info(f"[Weekly] S3 URL: {_s3_url}")
            except Exception as _s3e:
                print(f"[Weekly] ❌ Upload FAILED: {_s3e}")
                print(f"[Weekly] ────────────────────────────────────────")
                logger.error(f"[Weekly] S3 upload error: {_s3e}")
                st.session_state.pop("w_timetable_s3_url", None)

            # Cleanup temp files
            import os as _ost
            for _fp in [_tf_path, _png_path]:
                try: _ost.remove(_fp)
                except: pass
        else:
            st.error(f"Screenshot failed: {_result.stderr[:300]}")
            logger.error(f"[Weekly] playwright error: {_result.stderr}")

# ── Show timetable ────────────────────────────────────────────────────────────
if st.session_state.get("w_timetable_png"):
    import base64 as _wb64
    _w_img_b64 = _wb64.b64encode(st.session_state["w_timetable_png"]).decode()

    _wcol_wa, _wcol_info = st.columns([1, 1], gap="large")

    with _wcol_wa:
        st.markdown("**WhatsApp Preview**")
        st.markdown(
            f'<div style="background:#eae6df url(\'https://web.whatsapp.com/img/bg-chat-tile-dark_04fcacde539c58cca6745483d4858c52.png\');'
            f'border-radius:16px;padding:16px 12px 12px;max-width:360px;">'
            f'<div style="background:#dcf8c6;border-radius:12px;overflow:hidden;'
            f'box-shadow:0 2px 8px rgba(0,0,0,0.15);max-width:320px;">'
            f'<img src="data:image/png;base64,{_w_img_b64}" style="width:100%;display:block;border-radius:12px;">'
            f'<div style="padding:6px 10px 8px;text-align:right;">'
            f'<span style="font-size:11px;color:#667781;">✓✓</span>'
            f'</div></div></div>',
            unsafe_allow_html=True,
        )

    with _wcol_info:
        st.markdown("**Actions**")
        st.download_button(
            "⬇️ Download PNG",
            data=st.session_state["w_timetable_png"],
            file_name="weekly_timetable.png",
            mime="image/png",
            use_container_width=True,
        )
        if st.session_state.get("w_timetable_html"):
            st.download_button(
                "⬇️ Download HTML",
                data=st.session_state["w_timetable_html"],
                file_name="weekly_timetable.html",
                mime="text/html",
                use_container_width=True,
            )
        if st.session_state.get("w_timetable_s3_url"):
            _s3_display = st.session_state["w_timetable_s3_url"]
            st.markdown(
                f'<div style="background:#e8f5e9;border-radius:10px;padding:12px 16px;margin:8px 0;">'
                f'<div style="font-size:11px;font-weight:700;color:#2e7d32;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px;">☁️ S3 Public URL</div>'
                f'<div style="font-size:13px;word-break:break-all;"><a href="{_s3_display}" target="_blank">{_s3_display}</a></div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            st.code(_s3_display, language=None)

        st.markdown("**Full size preview**")
        st.image(st.session_state["w_timetable_png"], use_container_width=True)

st.markdown("</div>", unsafe_allow_html=True)

# ── Category 6 — Teacher Poll ─────────────────────────────────────────────────
import json as _c6_json
import importlib.util as _c6_ilu
from datetime import date as _c6_date

_c6_pb_path = BASE_DIR / "utils" / "teacher_poll_builder.py"
_c6_spec    = _c6_ilu.spec_from_file_location("teacher_poll_builder", _c6_pb_path)
_c6_pb      = _c6_ilu.module_from_spec(_c6_spec)
_c6_spec.loader.exec_module(_c6_pb)

st.markdown("""
<div class="section-card" style="margin-top:28px;">
    <p class="section-label">Category 6 — Teacher Poll</p>
    <p class="section-title">Teacher-Related Engagement Poll</p>
    <p class="section-desc">Fun Hinglish polls about teachers and subjects — 2× per month per batch. Teachers looked up automatically by board + medium + stream.</p>
</div>
""", unsafe_allow_html=True)

st.markdown("<div class='card'>", unsafe_allow_html=True)

_c6_col_form, _c6_col_prev = st.columns([1, 1], gap="large")

with _c6_col_form:
    _c6_batch = st.text_input("Batch Code", placeholder="e.g. BATCH001", key="c6_batch_input")
    _c6_test  = st.toggle("🧪 Test mode — show all 12 variations", value=False, key="c6_test_toggle")

    _today_c6     = _c6_date.today()
    _c6_slot      = _c6_pb.current_send_slot(_today_c6)
    _c6_t1, _c6_t2 = _c6_pb.pick_template_numbers(_today_c6)

    if _c6_test:
        st.caption("Test mode: all 12 templates generated at once.")
    else:
        if _c6_slot == 0:
            st.caption(f"ℹ️ Today (day {_today_c6.day}) is not a scheduled send day. Polls go out in week-2 (days 8–14) and week-4 (days 22–28).")
        else:
            tmpl_idx = _c6_t1 if _c6_slot == 1 else _c6_t2
            st.caption(f"📅 Send slot {_c6_slot} — template #{tmpl_idx + 1} will be used today.")

    _c6_fetch = st.button("🔍 Fetch Batch & Generate Poll", key="c6_fetch_btn", use_container_width=True)

    if _c6_fetch:
        if not _c6_batch.strip():
            st.warning("Enter a batch code first.")
        else:
            with st.spinner("Fetching batch meta..."):
                try:
                    _c6_meta = _fetch_batch_meta(_c6_batch.strip())
                    if not _c6_meta:
                        st.error("Batch not found.")
                    else:
                        st.session_state["c6_meta"]    = _c6_meta
                        st.session_state["c6_results"] = None
                        st.session_state["c6_batch"]   = _c6_batch.strip()
                        board_disp  = _c6_meta.get("exam_code", "?")
                        stream_disp = _c6_meta.get("stream_name", "?")
                        lang_disp   = _c6_meta.get("language", "ENG")
                        medium_disp = "Hindi" if lang_disp.upper().startswith("HIN") else "English"
                        st.success(f"✅ {board_disp} · {medium_disp} · {stream_disp}")
                except Exception as _e:
                    st.error(f"DB error: {_e}")

    if st.session_state.get("c6_meta"):
        _c6_meta     = st.session_state["c6_meta"]
        _c6_test_val = st.session_state.get("c6_test_toggle", False)

        if st.session_state.get("c6_results") is not None:
            if st.button("🔄 Regenerate", key="c6_regen_btn", use_container_width=True):
                st.session_state["c6_results"] = None
                st.rerun()
        else:
            _c6_gen_btn = st.button("✨ Generate Poll(s)", key="c6_gen_btn", use_container_width=True)

            if _c6_gen_btn:
                board  = _c6_meta.get("exam_code", "")
                medium = _c6_meta.get("language", "ENG")
                stream = _c6_meta.get("stream_name", "")

                st.info(f"Board: `{board}` · Medium: `{medium}` · Stream: `{stream}`")

                if not stream:
                    st.error("❌ Stream not found for this batch. Cannot pick teachers.")
                else:
                    _c6_status = st.empty()
                    _c6_status.info("⏳ Loading teacher lookup...")
                    try:
                        _c6_lookup    = _c6_pb.load_teacher_lookup()
                        _c6_templates = _c6_pb.load_poll_templates()
                        _c6_status.info(f"✅ Lookup loaded — {len(_c6_lookup)} subjects, {len(_c6_templates)} templates")

                        _c6_teachers = _c6_pb.get_teachers_for_batch(board, medium, stream, _c6_lookup)
                        if not _c6_teachers:
                            st.error(f"❌ No teachers found for stream `{stream}`. Check teacherdetails.xlsx.")
                        else:
                            _c6_status.info(f"✅ Teachers: {', '.join(f'{s}→{t}' for s,t in _c6_teachers)}")

                            if _c6_test_val:
                                _c6_variations = _c6_pb.get_all_variations(_c6_meta, _c6_lookup, _c6_templates)
                            else:
                                slot = _c6_pb.current_send_slot(_today_c6)
                                t1_idx, t2_idx = _c6_pb.pick_template_numbers(_today_c6)
                                tmpl_idx   = t1_idx if slot != 2 else t2_idx
                                tmpl       = _c6_templates[tmpl_idx] if tmpl_idx < len(_c6_templates) else _c6_templates[0]
                                import re as _c6re2
                                stream_key = _c6re2.sub(r'\(.*?\)', '', stream).strip().lower().replace(" ", "")
                                col_map    = {"pcm": "pcm", "pcb": "pcb", "pcmb": "pcm", "commerce": "commerce", "arts": "arts"}
                                col_key    = col_map.get(stream_key, "pcm")
                                raw_q      = tmpl.get(col_key) or tmpl["base"]
                                filled     = _c6_pb.fill_template(raw_q, _c6_teachers)
                                prompt     = _c6_pb.build_poll_llm_prompt(_c6_meta, filled, _c6_teachers, stream)
                                _c6_variations = [{
                                    "template_number": tmpl["number"],
                                    "send_slot":       slot or 1,
                                    "base_question":   tmpl["base"],
                                    "filled_question": filled,
                                    "llm_prompt":      prompt,
                                }]

                            _c6_status.info(f"⏳ Calling LLM for {len(_c6_variations)} variation(s)...")
                            import re as _c6re
                            _c6_generated = []
                            for _vi, var in enumerate(_c6_variations):
                                _c6_status.info(f"⏳ LLM call {_vi+1}/{len(_c6_variations)} — template #{var['template_number']}...")
                                try:
                                    _oc6 = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
                                    _resp6 = _oc6.chat.completions.create(
                                        model="gpt-5.4-mini",
                                        max_completion_tokens=400,
                                        temperature=0.9,
                                        messages=[{"role": "user", "content": var["llm_prompt"]}],
                                    )
                                    raw_out = _resp6.choices[0].message.content.strip()
                                    _jm     = _c6re.search(r'\{.*\}', raw_out, _c6re.DOTALL)
                                    parsed  = _c6_json.loads(_jm.group()) if _jm else {}
                                    if not parsed:
                                        st.warning(f"⚠️ Template #{var['template_number']}: LLM returned no JSON. Raw: {raw_out[:200]}")
                                except Exception as _pe:
                                    parsed = {"message": "", "question": var["filled_question"], "options": []}
                                    st.warning(f"⚠️ LLM error for template #{var['template_number']}: {_pe}")
                                    logger.warning(f"[Cat6] LLM error: {_pe}")
                                _c6_generated.append({**var, "parsed": parsed})

                            st.session_state["c6_results"]  = _c6_generated
                            st.session_state["c6_teachers"] = _c6_teachers
                            _c6_status.success(f"✅ Done — {len(_c6_generated)} poll(s) generated.")
                    except Exception as _ge:
                        import traceback as _c6tb
                        st.error(f"❌ Error: {_ge}")
                        st.code(_c6tb.format_exc(), language="python")
                        logger.error(f"[Cat6] {_ge}", exc_info=True)

with _c6_col_prev:
    _c6_results  = st.session_state.get("c6_results")
    _c6_teachers = st.session_state.get("c6_teachers", [])

    if _c6_results:
        st.markdown("**Teachers resolved for this batch:**")
        for subj, name in _c6_teachers:
            st.markdown(f"- **{subj}** → {name}")
        st.markdown("---")

        if len(_c6_results) == 1:
            _r = _c6_results[0]
            p  = _r.get("parsed", {})
            st.markdown(f"**Template #{_r['template_number']} · Send slot {_r['send_slot']}**")
            st.caption(f"Base: {_r['base_question']}")
            poll_q    = p.get("question", _r["filled_question"])
            opts      = p.get("options", [])
            opts_html = "".join(
                f'<div style="padding:7px 10px;margin:4px 0;background:#f0f0f0;border-radius:8px;font-size:13px;">📊 {o}</div>'
                for o in opts
            )
            st.markdown(
                f'<div style="background:#eae6df;border-radius:16px;padding:16px 12px;max-width:340px;">'
                f'<div style="background:#fff;border-radius:12px;padding:12px 14px;">'
                f'<div style="font-weight:600;font-size:13px;margin-bottom:8px;">📊 {poll_q}</div>'
                f'{opts_html}'
                f'</div></div>',
                unsafe_allow_html=True,
            )
            with st.expander("🔍 Raw LLM output", expanded=False):
                st.json(p)
        else:
            # Test mode — tabs for all 12
            _c6_tab_labels = [f"#{r['template_number']}" for r in _c6_results]
            _c6_tabs = st.tabs(_c6_tab_labels)
            for tab, _r in zip(_c6_tabs, _c6_results):
                with tab:
                    p      = _r.get("parsed", {})
                    poll_q = p.get("question", _r["filled_question"])
                    opts   = p.get("options", [])
                    opts_html = "".join(
                        f'<div style="padding:6px 10px;margin:3px 0;background:#f0f0f0;border-radius:8px;font-size:12px;">📊 {o}</div>'
                        for o in opts
                    )
                    st.caption(f"Base: {_r['base_question']}")
                    st.markdown(
                        f'<div style="background:#eae6df;border-radius:16px;padding:12px 10px;max-width:320px;">'
                        f'<div style="background:#fff;border-radius:10px;padding:10px 12px;">'
                        f'<div style="font-weight:600;font-size:12px;margin-bottom:6px;">📊 {poll_q}</div>'
                        f'{opts_html}'
                        f'</div></div>',
                        unsafe_allow_html=True,
                    )

st.markdown("</div>", unsafe_allow_html=True)
