"""
Test-mode PYQ helpers — fetches recent classes regardless of date.
Never import this in production flows.
"""
import logging
from utils.db_connection import (
    get_connection, close_connection,
    epoch_ms_to_ist, format_time_hinglish,
    _log,
)

logger = logging.getLogger(__name__)


def fetch_yesterday_classes(batch_code: str, limit: int = 5):
    """
    Returns (classes, days_ago=1) using the most recent `limit` classes for this batch,
    regardless of date. days_ago is always returned as 1 so the prompt says "Kal".
    Used only for local testing when no recent classes exist in the normal date window.
    """
    _log("")
    _log("=" * 60)
    _log(f"  [TEST MODE] PYQ CLASS LOOKUP  batch_code={batch_code}  limit={limit}")
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
            _log(f"  ✓ batch_id={batch_id}  exam={batch['exam_name']}  grade={batch['grade_name']}")

            # STEP 2 — chapter ids in batch
            cur.execute(
                "SELECT chapter_id FROM av_batch_chapters WHERE batch_id = %s",
                (batch_id,),
            )
            chapter_ids = [r["chapter_id"] for r in cur.fetchall()]
            _log(f"  ✓ {len(chapter_ids)} chapter(s) in batch")
            if not chapter_ids:
                _log("  ✗ Batch has no chapters.")
                return [], 1

            # STEP 3 — most recent sessions (any date, any status)
            placeholders = ",".join(["%s"] * len(chapter_ids))
            cur.execute(
                f"""
                SELECT chapter_id, start_time, end_time, status
                FROM   chapter_live_mapping
                WHERE  chapter_id IN ({placeholders})
                ORDER  BY start_time DESC
                LIMIT  {limit}
                """,
                chapter_ids,
            )
            live_rows = cur.fetchall()
            _log(f"  ✓ {len(live_rows)} row(s) returned")
            if not live_rows:
                _log("  ✗ No rows in chapter_live_mapping for this batch.")
                return [], 1

            for row in live_rows:
                start_ist = epoch_ms_to_ist(row["start_time"])
                _log(
                    f"      chapter_id={row['chapter_id'][:16]}...  "
                    f"start={start_ist.strftime('%Y-%m-%d %H:%M IST')}  "
                    f"status={row['status']}"
                )

            # STEP 4 — chapter + subject details
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
            _log(f"  ✓ {len(chapter_rows)} chapter row(s) returned")

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

            results.sort(key=lambda x: x["start_ms"], reverse=True)

            _log("")
            _log(f"  [TEST MODE] RESULT: {len(results)} class(es) ready")
            for i, r in enumerate(results, 1):
                _log(f"  Class {i}: {r['chapter_name']} · {r['subject_name']} · {r['class_time']}")
            _log("=" * 60)

            return results, 1

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
