"""
Fetches recent class for Common Mistake Alert (Category 11).
Looks back up to 4 days — supports twice-a-week send pattern.
"""
import logging
from datetime import datetime, timedelta
from utils.db_connection import get_connection, close_connection, epoch_ms_to_ist, format_time_hinglish, IST, _log

logger = logging.getLogger(__name__)


def _fetch_classes_for_day(cur, batch, chapter_ids, days_ago: int):
    now_ist = datetime.now(IST)
    target  = now_ist - timedelta(days=days_ago)
    day_start_ms = int(datetime(target.year, target.month, target.day, 0, 0, 0, tzinfo=IST).timestamp() * 1000)
    day_end_ms   = int(datetime(target.year, target.month, target.day, 23, 59, 59, tzinfo=IST).timestamp() * 1000)

    placeholders = ",".join(["%s"] * len(chapter_ids))
    cur.execute(
        f"""
        SELECT chapter_id, start_time, status
        FROM   chapter_live_mapping
        WHERE  chapter_id IN ({placeholders})
          AND  start_time >= %s AND start_time <= %s
        ORDER  BY start_time ASC
        """,
        chapter_ids + [day_start_ms, day_end_ms],
    )
    live_rows = cur.fetchall()
    if not live_rows:
        return []

    ids      = [r["chapter_id"] for r in live_rows]
    time_map = {r["chapter_id"]: r["start_time"] for r in live_rows}

    placeholders2 = ",".join(["%s"] * len(ids))
    cur.execute(
        f"""
        SELECT c.id, c.title AS chapter_name, c.teacher_name,
               c.hindi_title, c.teacher_name_hindi, c.video_image,
               s.name AS subject_name
        FROM   chapter c
        LEFT JOIN subject s ON s.id = c.subject_id
        WHERE  c.id IN ({placeholders2})
        """,
        ids,
    )
    rows = cur.fetchall()

    results = []
    for c in rows:
        start_ms  = time_map.get(c["id"])
        start_ist = epoch_ms_to_ist(start_ms)
        raw_teacher = (c["teacher_name"] or "").strip().removeprefix("By ").strip()
        results.append({
            "chapter_id":         c["id"],
            "chapter_name":       (c["chapter_name"] or "").strip(),
            "hindi_title":        (c.get("hindi_title") or "").strip(),
            "teacher_name":       raw_teacher,
            "teacher_name_hindi": (c.get("teacher_name_hindi") or "").strip().removesuffix("द्वारा").strip(),
            "teacher_gender":     "female" if raw_teacher.lower().endswith("ma'am") else "male",
            "subject_name":       (c["subject_name"] or "").strip().replace(" Board", "").strip(),
            "class_time":         format_time_hinglish(start_ist.hour, start_ist.minute),
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


def fetch_mistake_class(batch_code: str):
    """
    Returns (classes, days_ago). Tries 1→4 days back, returns first non-empty day.
    """
    _log(f"\n{'='*60}\n  MISTAKE CLASS LOOKUP  batch_code={batch_code}\n{'='*60}")
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT b.id, b.code, b.language,
                       e.name AS exam_name, e.code AS exam_code,
                       g.name AS grade_name, s.name AS stream_name
                FROM   av_batches b
                LEFT JOIN av_exams        e ON e.id = b.exam_id
                LEFT JOIN av_grade_levels g ON g.id = b.grade_level_id
                LEFT JOIN av_streams      s ON s.id = b.stream_id
                WHERE  b.code = %s LIMIT 1
                """,
                (batch_code,),
            )
            batch = cur.fetchone()
            if not batch:
                _log(f"  ✗ No batch found for '{batch_code}'")
                return [], 1

            cur.execute("SELECT chapter_id FROM av_batch_chapters WHERE batch_id = %s", (batch["id"],))
            chapter_ids = [r["chapter_id"] for r in cur.fetchall()]
            if not chapter_ids:
                return [], 1

            for days_ago in (1, 2, 3, 4):
                results = _fetch_classes_for_day(cur, batch, chapter_ids, days_ago)
                if results:
                    _log(f"  RESULT: {len(results)} class(es) found ({days_ago} day(s) ago)")
                    return results, days_ago

            _log("  ✗ No classes found in last 4 days.")
            return [], 1
    except Exception as e:
        _log(f"  ✗ ERROR: {e}")
        raise
    finally:
        if conn:
            proc = getattr(conn, "_ssh_proc", None)
            conn.close()
            if proc:
                proc.kill(); proc.wait()
