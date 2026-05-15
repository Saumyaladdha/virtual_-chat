"""
Cat 6 — Teacher-Related Poll builder.

Flow:
  1. From batch meta (board, medium, stream) → resolve subjects
  2. Look up actual teacher names from teacherdetails.xlsx (strips "(Temp)")
  3. Pick a poll template from teacherPoll.xlsx
     - Stateless calendar rotation: month determines which 2 templates to use
     - send_slot 1 (week 2, days 8–14) → odd template index
     - send_slot 2 (week 4, days 22–28) → even template index
  4. Fill [Teacher1/2/3] and [Subject] placeholders
  5. Build LLM prompt to make the poll fun in Hinglish
"""

import re
import pathlib
from datetime import date
from typing import Optional

_BASE = pathlib.Path(__file__).parent.parent  # repo root
_DATA = _BASE / "data"

# ── Stream → subjects ─────────────────────────────────────────────────────────
_STREAM_SUBJECTS: dict[str, list[str]] = {
    "pcm":      ["Physics", "Chemistry", "Maths"],
    "pcb":      ["Physics", "Chemistry", "Biology"],
    "pcmb":     ["Physics", "Chemistry", "Maths", "Biology"],
    "commerce": ["Accountancy", "Economics", "Business Studies"],
    "arts":     ["History", "Pol Science", "Geography"],
}

# Stream column in teacherPoll templates
_STREAM_TEMPLATE_COL: dict[str, int] = {
    "pcm":      2,   # PCM column
    "pcb":      3,   # PCB column
    "pcmb":     2,   # treat as PCM
    "commerce": 4,   # Commerce column
    "arts":     5,   # Arts column
}

# Board → column pair (Hindi_col, English_col) in teacherdetails.xlsx (0-indexed)
_BOARD_COLS: dict[str, tuple[int, int]] = {
    "mp": (2, 3),
    "up": (4, 5),
    "rj": (6, 7),
    "br": (8, 9),
}

# Subject name normalisation → row keyword in teacherdetails
_SUBJECT_ROW_MAP: dict[str, str] = {
    "physics":          "physics",
    "chemistry":        "chemistry",
    "maths":            "maths",
    "mathematics":      "maths",
    "biology":          "biology",
    "accountancy":      "accountancy",
    "economics":        "economics",
    "business studies": "business studies",
    "history":          "history",
    "pol science":      "pol science",
    "political science":"pol science",
    "geography":        "geography",
    "hindi":            "hindi",
    "english":          "english",
}


def _strip_temp(name: str) -> str:
    """Remove '(Temp)', '(temp)', and trailing whitespace from a teacher name."""
    name = re.sub(r'\s*\(temp\)\s*', '', name, flags=re.IGNORECASE).strip()
    # Also strip slash-alternatives like "Pravin/Sumit" → take first name
    if "/" in name:
        name = name.split("/")[0].strip()
    return name


def load_teacher_lookup() -> dict[str, dict[str, str]]:
    """
    Returns a nested dict:
      teacher_lookup[subject_lower][board_medium_key] = teacher_name

    board_medium_key = e.g. "up_hindi", "mp_english"
    """
    try:
        import openpyxl
    except ImportError:
        return {}

    wb = openpyxl.load_workbook(_DATA / "teacherdetails.xlsx", data_only=True)
    ws = wb["Board Wise Teachers"]

    rows = list(ws.iter_rows(values_only=True))
    # Row 0: headers (SUBJECT, None, MP 12th, None, UP 12th, None, RJ 12th, None, BR 12th, None, ...)
    # Row 1: sub-headers (None, None, Hindi, English, Hindi, English, Hindi, English, Hindi, English, ...)
    # Rows 2+: data

    lookup: dict[str, dict[str, str]] = {}
    boards = ["mp", "up", "rj", "br"]

    for row in rows[2:]:
        subj_raw = row[0]
        if not subj_raw:
            continue
        subj_key = str(subj_raw).strip().lower()
        # normalise
        subj_key = _SUBJECT_ROW_MAP.get(subj_key, subj_key)

        lookup[subj_key] = {}
        for board, (hi_col, en_col) in _BOARD_COLS.items():
            hi_val = row[hi_col] if len(row) > hi_col else None
            en_val = row[en_col] if len(row) > en_col else None
            if hi_val:
                lookup[subj_key][f"{board}_hindi"]   = _strip_temp(str(hi_val))
            if en_val:
                lookup[subj_key][f"{board}_english"] = _strip_temp(str(en_val))

    return lookup


_BOARD_CODE_MAP = {
    # exam_code from DB → 2-letter key used in teacherdetails
    "mpbse": "mp", "mp": "mp",
    "upmsp": "up", "up": "up",
    "rbse":  "rj", "rj": "rj", "rajasthan": "rj",
    "bseb":  "br", "br": "br", "bihar": "br",
}


def _normalise_board(board: str) -> str:
    """'MPBSE' → 'mp',  'UP' → 'up', etc."""
    key = board.lower().strip()
    return _BOARD_CODE_MAP.get(key, key[:2])   # fallback: first 2 chars


def get_teachers_for_batch(
    board: str,
    medium: str,
    stream: str,
    teacher_lookup: dict,
) -> list[tuple[str, str]]:
    """
    Returns [(subject_display, teacher_name), ...] for the batch's stream.
    board: exam_code from DB e.g. "MPBSE" / "UPMSP" / "RBSE" / "BSEB"
    medium: language from DB e.g. "ENGLISH" / "HINDI"
    stream: stream_name from DB e.g. "PCB (Biology)" / "Commerce"
    """
    board_key  = _normalise_board(board)
    medium_key = "hindi" if medium.upper().startswith("HIN") else "english"
    lookup_key = f"{board_key}_{medium_key}"

    # Normalise stream: "PCB (Biology)" → "pcb", "Commerce" → "commerce"
    # Strip anything in parentheses, take first word only
    stream_clean = re.sub(r'\(.*?\)', '', stream).strip().lower().replace(" ", "")
    # Try exact match first, then prefix match
    subjects = _STREAM_SUBJECTS.get(stream_clean, [])
    if not subjects:
        for key in _STREAM_SUBJECTS:
            if stream_clean.startswith(key) or key.startswith(stream_clean):
                subjects = _STREAM_SUBJECTS[key]
                break
    result = []
    for subj_display in subjects:
        row_key = _SUBJECT_ROW_MAP.get(subj_display.lower(), subj_display.lower())
        teacher = teacher_lookup.get(row_key, {}).get(lookup_key, "")
        result.append((subj_display, teacher or subj_display + " Teacher"))
    return result


def load_poll_templates() -> list[dict]:
    """
    Returns list of 12 template dicts:
      {"number": 1, "base": "...", "pcm": "...", "pcb": "...", "commerce": "...", "arts": "..."}
    """
    try:
        import openpyxl
    except ImportError:
        return []

    wb = openpyxl.load_workbook(_DATA / "teacherPoll.xlsx", data_only=True)
    ws = wb["Question Templates"]
    rows = list(ws.iter_rows(values_only=True))
    # Row 0: header (#, Template (LLM Base), PCM, PCB, Commerce, Arts)
    templates = []
    for row in rows[1:]:
        if not row[0]:
            continue
        templates.append({
            "number":   int(row[0]),
            "base":     str(row[1] or "").strip(),
            "pcm":      str(row[2] or "").strip(),
            "pcb":      str(row[3] or "").strip(),
            "commerce": str(row[4] or "").strip(),
            "arts":     str(row[5] or "").strip(),
        })
    return templates


def pick_template_numbers(today: Optional[date] = None) -> tuple[int, int]:
    """
    Returns (send1_template_idx, send2_template_idx) — both 0-based indices into the 12-template list.

    Calendar rotation (stateless):
      month 0 (Jan) → templates 0,1
      month 1 (Feb) → templates 2,3
      ...
      month 5 (Jun) → templates 10,11
      month 6 (Jul) → wraps to 0,1
    """
    if today is None:
        today = date.today()
    offset = ((today.month - 1) % 6) * 2
    return offset, offset + 1          # send-slot 1, send-slot 2


def current_send_slot(today: Optional[date] = None) -> int:
    """
    Returns 1 if today is in week-2 window (days 8–14),
    returns 2 if today is in week-4 window (days 22–28),
    returns 0 otherwise (not a scheduled send day).
    """
    if today is None:
        today = date.today()
    if 8 <= today.day <= 14:
        return 1
    if 22 <= today.day <= 28:
        return 2
    return 0


def fill_template(template_str: str, teachers: list[tuple[str, str]]) -> str:
    """Replace [Teacher1], [Teacher2], [Teacher3] with actual names."""
    teacher_names = [t[1] for t in teachers]
    for i, name in enumerate(teacher_names[:3], start=1):
        template_str = template_str.replace(f"[Teacher{i}]", name)
    # Replace leftover placeholders with empty
    template_str = re.sub(r'\[Teacher\d\]', '', template_str)
    # Replace [Subject] with first subject
    if teachers:
        template_str = template_str.replace("[Subject]", teachers[0][0])
    return template_str.strip()


def build_poll_llm_prompt(
    batch_meta: dict,
    filled_question: str,
    teachers: list[tuple[str, str]],
    stream: str,
) -> str:
    """
    Loads prompt template from prompts/english/teacher_poll/prompt.txt and fills variables.
    Returns the prompt string.
    """
    board        = batch_meta.get("exam_code", "Board").upper()
    grade        = batch_meta.get("grade_name", "12th")
    teacher_list = "\n".join(f"- {subj}: {name}" for subj, name in teachers)

    prompt_file = _BASE / "prompts" / "english" / "teacher_poll" / "prompt.txt"
    template    = prompt_file.read_text(encoding="utf-8")

    return (
        template
        .replace("{grade}",           grade)
        .replace("{stream}",          stream)
        .replace("{board}",           board)
        .replace("{teacher_list}",    teacher_list)
        .replace("{filled_question}", filled_question)
    )


def get_all_variations(
    batch_meta: dict,
    teacher_lookup: dict,
    templates: list[dict],
) -> list[dict]:
    """
    Testing mode: returns all 12 variations filled + ready for LLM.
    Each item: {{"template_number": N, "send_slot": 1/2, "filled_question": "...", "llm_prompt": "..."}}
    """
    board  = batch_meta.get("exam_code", "")
    medium = batch_meta.get("language", "ENG")
    stream = batch_meta.get("stream_name", "PCM")
    teachers = get_teachers_for_batch(board, medium, stream, teacher_lookup)

    stream_clean = re.sub(r'\(.*?\)', '', stream).strip().lower().replace(" ", "")
    tmpl_col_key = {
        "pcm": "pcm", "pcb": "pcb", "pcmb": "pcm",
        "commerce": "commerce", "arts": "arts",
    }.get(stream_clean, "pcm")

    results = []
    for idx, tmpl in enumerate(templates):
        send_slot = 1 if idx % 2 == 0 else 2
        raw_q = tmpl.get(tmpl_col_key) or tmpl["base"]
        filled = fill_template(raw_q, teachers)
        prompt = build_poll_llm_prompt(batch_meta, filled, teachers, stream)
        results.append({
            "template_number": tmpl["number"],
            "send_slot":       send_slot,
            "base_question":   tmpl["base"],
            "filled_question": filled,
            "llm_prompt":      prompt,
        })
    return results
