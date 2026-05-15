"""
Fetches recent classes for PYQ feature (yesterday, or 2 days ago as fallback).
"""
import logging
from datetime import datetime, timedelta
from utils.db_connection import (
    get_connection, close_connection,
    epoch_ms_to_ist, format_time_hinglish,
    IST, _log,
)

logger = logging.getLogger(__name__)


def _fetch_classes_for_day(cur, batch, chapter_ids, days_ago: int):
    """Query chapter_live_mapping for a specific day offset. Returns list of result dicts."""
    now_ist = datetime.now(IST)
    target = now_ist - timedelta(days=days_ago)
    day_start_ms = int(
        datetime(target.year, target.month, target.day, 0, 0, 0, tzinfo=IST).timestamp() * 1000
    )
    day_end_ms = int(
        datetime(target.year, target.month, target.day, 23, 59, 59, tzinfo=IST).timestamp() * 1000
    )

    label = "yesterday" if days_ago == 1 else f"{days_ago} days ago"
    _log(f"  Querying {label} ({target.strftime('%Y-%m-%d')})...")

    placeholders = ",".join(["%s"] * len(chapter_ids))
    cur.execute(
        f"""
        SELECT chapter_id, start_time, end_time, status
        FROM   chapter_live_mapping
        WHERE  chapter_id IN ({placeholders})
          AND  start_time >= %s
          AND  start_time <= %s
        ORDER  BY start_time ASC
        """,
        chapter_ids + [day_start_ms, day_end_ms],
    )
    live_rows = cur.fetchall()
    _log(f"  ✓ {len(live_rows)} session(s) found for {label}")
    if not live_rows:
        return []

    today_chapter_ids = [r["chapter_id"] for r in live_rows]
    time_map = {r["chapter_id"]: r["start_time"] for r in live_rows}

    placeholders2 = ",".join(["%s"] * len(today_chapter_ids))
    cur.execute(
        f"""
        SELECT c.id, c.title AS chapter_name, c.teacher_name,
               c.video_image, c.hindi_title, c.teacher_name_hindi,
               s.name AS subject_name
        FROM   chapter c
        LEFT JOIN subject s ON s.id = c.subject_id
        WHERE  c.id IN ({placeholders2})
        """,
        today_chapter_ids,
    )
    chapter_rows = cur.fetchall()

    results = []
    for c in chapter_rows:
        start_ms  = time_map.get(c["id"])
        start_ist = epoch_ms_to_ist(start_ms)
        class_time = format_time_hinglish(start_ist.hour, start_ist.minute)

        subject_raw   = (c["subject_name"] or "").strip()
        subject_clean = subject_raw.replace(" Board", "").strip()

        raw_teacher  = (c["teacher_name"] or "").strip()
        teacher_name = raw_teacher.removeprefix("By ").strip()
        teacher_gender = "female" if teacher_name.lower().endswith("ma'am") else "male"

        raw_teacher_hindi = (c.get("teacher_name_hindi") or "").strip()
        teacher_name_hindi = raw_teacher_hindi.removesuffix("द्वारा").strip()

        results.append({
            "chapter_id":         c["id"],
            "chapter_name":       (c["chapter_name"] or "").strip(),
            "hindi_title":        (c.get("hindi_title") or "").strip(),
            "teacher_name":       teacher_name,
            "teacher_name_hindi": teacher_name_hindi,
            "teacher_gender":     teacher_gender,
            "subject_name":       subject_clean,
            "class_time":         class_time,
            "start_ms":           start_ms,
            "video_image":        (c.get("video_image") or "").strip(),
            "exam_name":          batch["exam_name"],
            "exam_code":          (batch.get("exam_code") or "").strip(),
            "grade_name":         batch["grade_name"],
            "stream_name":        batch["stream_name"],
            "language":           batch["language"],
        })

    results.sort(key=lambda x: x["start_ms"])
    return results


def fetch_yesterday_classes(batch_code: str):
    """
    Returns (classes, days_ago) where days_ago is 1 (yesterday) or 2 (day before).
    Tries yesterday first; falls back to 2 days ago if no classes found.
    """
    _log("")
    _log("=" * 60)
    _log(f"  PYQ CLASS LOOKUP  batch_code={batch_code}")
    _log("=" * 60)

    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:

            # STEP 1 — batch metadata
            cur.execute(
                """
                SELECT b.id, b.code, b.language,
                       e.name  AS exam_name,
                       e.code  AS exam_code,
                       g.name  AS grade_name,
                       s.name  AS stream_name
                FROM   av_batches b
                LEFT JOIN av_exams        e ON e.id = b.exam_id
                LEFT JOIN av_grade_levels g ON g.id = b.grade_level_id
                LEFT JOIN av_streams      s ON s.id = b.stream_id
                WHERE  b.code = %s
                LIMIT  1
                """,
                (batch_code,),
            )
            batch = cur.fetchone()
            if not batch:
                _log(f"  ✗ No batch found for '{batch_code}'")
                return [], 1

            batch_id = batch["id"]
            _log(f"  ✓ batch_id={batch_id}  exam={batch['exam_name']}")

            # STEP 2 — chapter ids
            cur.execute(
                "SELECT chapter_id FROM av_batch_chapters WHERE batch_id = %s",
                (batch_id,),
            )
            chapter_ids = [r["chapter_id"] for r in cur.fetchall()]
            if not chapter_ids:
                _log("  ✗ Batch has no chapters.")
                return [], 1

            # Try yesterday (days_ago=1), then 2 days ago (days_ago=2)
            for days_ago in (1, 2):
                results = _fetch_classes_for_day(cur, batch, chapter_ids, days_ago)
                if results:
                    _log(f"  RESULT: {len(results)} class(es) found ({days_ago} day(s) ago)")
                    return results, days_ago

            _log("  ✗ No classes found for yesterday or 2 days ago.")
            return [], 1

    except Exception as e:
        _log(f"  ✗ ERROR: {e}")
        raise
    finally:
        if conn:
            proc = getattr(conn, "_ssh_proc", None)
            conn.close()
            _log("🔌 DB connection closed")
            if proc:
                proc.kill()
                proc.wait()
                _log("🔌 SSH tunnel closed")


def fetch_batch_meta(batch_code: str) -> dict:
    """Return exam_code, exam_name, grade_name, stream_name, language for a batch."""
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT b.language,
                       e.name AS exam_name,
                       e.code AS exam_code,
                       g.name AS grade_name,
                       s.name AS stream_name
                FROM   av_batches b
                LEFT JOIN av_exams        e ON e.id = b.exam_id
                LEFT JOIN av_grade_levels g ON g.id = b.grade_level_id
                LEFT JOIN av_streams      s ON s.id = b.stream_id
                WHERE  b.code = %s
                LIMIT  1
                """,
                (batch_code,),
            )
            row = cur.fetchone()
            if not row:
                return {}
            return {
                "exam_code":   (row.get("exam_code") or "").strip(),
                "exam_name":   (row.get("exam_name") or "").strip(),
                "grade_name":  (row.get("grade_name") or "").strip(),
                "stream_name": (row.get("stream_name") or "").strip(),
                "language":    (row.get("language") or "ENG").strip(),
            }
    except Exception as e:
        _log(f"  ✗ fetch_batch_meta ERROR: {e}")
        return {}
    finally:
        if conn:
            proc = getattr(conn, "_ssh_proc", None)
            conn.close()
            if proc:
                proc.kill()
                proc.wait()
