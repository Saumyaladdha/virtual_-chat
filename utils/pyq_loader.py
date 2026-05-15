"""
DynamoDB-backed PYQ loader.
Table: pyq_question_table (ap-south-1)
Filters by subject, language, board, class, Marks > 2.
Chapter matching done in Python with fuzzy scoring.
"""
import os
import re
import random
import logging
from difflib import SequenceMatcher
from typing import List, Dict

import boto3
from boto3.dynamodb.conditions import Attr

logger = logging.getLogger(__name__)

_DYNAMO_TABLE  = "pyq_question_table"
_DYNAMO_REGION = "ap-south-1"

# App subject name → DynamoDB subject key
_SUBJECT_NORM: Dict[str, str] = {
    # PCM
    "physics":               "physics",
    "chemistry":             "chemistry",
    "mathematics":           "mathematics",
    "maths":                 "mathematics",
    "math":                  "mathematics",
    # PCB
    "biology":               "biology",
    # Commerce
    "accountancy":           "accountancy",
    "economics":             "economics",
    "business studies":      "business_studies",
    "business_studies":      "business_studies",
    "business study":        "business_studies",
    # Arts / Humanities
    "political science":     "political_science",
    "political_science":     "political_science",
    "history":               "history",
    "geography":             "geography",
    "sociology":             "sociology",
    "psychology":            "psychology",
    "philosophy":            "philosophy",
    "home science":          "home_science",
    "home_science":          "home_science",
    # Languages
    "english":               "english",
    "hindi":                 "hindi",
    "sanskrit":              "sanskrit",
    "urdu":                  "urdu",
    # Other
    "physical education":    "physical_education",
    "physical_education":    "physical_education",
    "computer science":      "computer_science",
    "computer_science":      "computer_science",
    "informatics practices": "informatics_practices",
    "informatics_practices": "informatics_practices",
}


def _norm_subject(s: str) -> str:
    k = s.lower().strip()
    return _SUBJECT_NORM.get(k, k.replace(" ", "_"))


def _norm_board(exam_code: str = "", exam_name: str = "") -> str:
    code = (exam_code or "").upper()
    name = (exam_name or "").lower()
    logger.debug(f"[PYQ] _norm_board: code='{code}' name='{name}'")
    if "MPBSE" in code or "mp board" in name or "madhya pradesh" in name or "mpbse" in name:
        return "mpboard"
    if "UPBOARD" in code or "UP_" in code or "up board" in name or "uttar pradesh" in name or "upbse" in name:
        return "upboard"
    if "CBSE" in code or "cbse" in name:
        return "cbse"
    if "RBSE" in code or "RB" in code or "rajasthan" in name or "rbse" in name or "rb board" in name:
        return "rbse"
    if "BIHAR" in code or "bseb" in code or "bihar" in name or "bseb" in name:
        return "bseb"
    if "HBSE" in code or "haryana" in name or "hbse" in name:
        return "hbse"
    return ""


def _norm_class(grade_name: str = "") -> int:
    m = re.search(r'\d+', grade_name or "")
    return int(m.group()) if m else 0


def _clean(text: str) -> str:
    """Lowercase, strip Part/भाग suffix, collapse whitespace."""
    text = re.sub(r'\s*[-–]\s*(Part|भाग)\s*\d+\s*$', '', text, flags=re.I)
    text = re.sub(r'[^\w\s]', ' ', text)
    return re.sub(r'\s+', ' ', text).lower().strip()


def _similarity(query: str, candidate: str) -> float:
    """
    Combined score: SequenceMatcher + Jaccard token overlap.
    Substring containment short-circuits with a high fixed score.
    """
    q = _clean(query)
    c = _clean(candidate)

    if not q or not c:
        return 0.0

    if q in c or c in q:
        return 0.95

    seq = SequenceMatcher(None, q, c).ratio()

    tq = set(q.split())
    tc = set(c.split())
    union = tq | tc
    jaccard = len(tq & tc) / len(union) if union else 0.0

    return 0.55 * seq + 0.45 * jaccard


def _scan(subject_key: str, language: str, board: str, class_num: int,
          min_marks: int = 3) -> List[Dict]:
    dynamo = boto3.resource(
        "dynamodb",
        region_name=_DYNAMO_REGION,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )
    table = dynamo.Table(_DYNAMO_TABLE)

    fexpr = (
        Attr("subject").eq(subject_key) &
        Attr("language").eq(language) &
        Attr("Marks").gte(min_marks)
    )
    if board:
        fexpr = fexpr & Attr("board").eq(board)
    if class_num:
        fexpr = fexpr & Attr("Class").eq(class_num)

    items, kwargs = [], {"FilterExpression": fexpr}
    while True:
        resp = table.scan(**kwargs)
        items.extend(resp.get("Items", []))
        last = resp.get("LastEvaluatedKey")
        if not last:
            break
        kwargs["ExclusiveStartKey"] = last

    return items


def pick_questions(
    chapter_name: str,
    subject: str,
    n: int = 8,
    language: str = "English",
    exam_code: str = "",
    exam_name: str = "",
    grade_name: str = "",
) -> list:
    """
    Fetch up to n PYQs from DynamoDB for the given chapter.
    Marks > 2. Fuzzy chapter match threshold: 0.70.
    """
    subject_key = _norm_subject(subject)
    board       = _norm_board(exam_code, exam_name)
    class_num   = _norm_class(grade_name)
    lang        = "Hindi" if (language or "").lower().startswith("hin") else "English"

    logger.info(f"[PYQ] subject={subject_key} lang={lang} board={board} class={class_num} chapter='{chapter_name}'")

    try:
        items = _scan(subject_key, lang, board, class_num, min_marks=3)
        if not items:
            logger.info(f"[PYQ] No items with marks>=3, retrying with marks>=1")
            items = _scan(subject_key, lang, board, class_num, min_marks=1)
    except Exception as e:
        logger.error(f"[PYQ] DynamoDB scan error: {e}")
        return []

    if not items:
        logger.info(f"[PYQ] No items for subject={subject_key} lang={lang} board={board} class={class_num}")
        return []

    # Score every item by chapter name similarity
    scored = [
        (s, item) for item in items
        if (s := _similarity(chapter_name, item.get("Chapter_Name", ""))) >= 0.70
    ]

    if not scored:
        logger.info(f"[PYQ] No match >= 0.70 for '{chapter_name}' among {len(items)} candidates")
        return []

    scored.sort(key=lambda x: x[0], reverse=True)
    logger.info(
        f"[PYQ] {len(scored)} match(es) | best={scored[0][0]:.2f} "
        f"chapter='{scored[0][1].get('Chapter_Name')}'"
    )

    # Shuffle within top band (best score ± 0.05) for variety per call
    best = scored[0][0]
    top  = [item for sc, item in scored if sc >= best - 0.05]
    rest = [item for sc, item in scored if sc <  best - 0.05]
    random.shuffle(top)
    pool = top + rest

    _NO_LIMIT_SUBJECTS = {"accountancy", "accounts", "business_studies", "business studies"}
    _MAX_Q_CHARS = None if subject_key in _NO_LIMIT_SUBJECTS else 300

    def _collect(pool_items, selected, seen, limit):
        for item in pool_items:
            if len(selected) >= limit:
                break
            q  = item.get("Question", "")
            if not q or (_MAX_Q_CHARS and len(q) > _MAX_Q_CHARS):
                continue
            fp = " ".join(q.lower().split())[:120]
            if fp not in seen:
                selected.append({
                    "chapter":  item.get("Chapter_Name", ""),
                    "subject":  item.get("subject", ""),
                    "marks":    int(item.get("Marks", 0)),
                    "year":     str(item.get("Year", "")),
                    "type":     item.get("Question_Type", ""),
                    "question": q,
                    "language": item.get("language", "English"),
                })
                seen.add(fp)

    selected, seen = [], set()
    _collect(pool, selected, seen, n)

    # If still short, top-up with 1-2 mark questions from a fresh scan
    if len(selected) < n:
        logger.info(f"[PYQ] Only {len(selected)} found with marks>=3, topping up with marks>=1")
        try:
            low_items = _scan(subject_key, lang, board, class_num, min_marks=1)
            low_scored = [
                (s, item) for item in low_items
                if (s := _similarity(chapter_name, item.get("Chapter_Name", ""))) >= 0.70
            ]
            low_scored.sort(key=lambda x: x[0], reverse=True)
            low_pool = [item for _, item in low_scored]
            random.shuffle(low_pool)
            _collect(low_pool, selected, seen, n)
        except Exception as e:
            logger.warning(f"[PYQ] Top-up scan failed: {e}")

    logger.info(f"[PYQ] Returning {len(selected)} question(s)")
    return selected
