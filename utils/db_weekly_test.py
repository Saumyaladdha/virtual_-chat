"""
Test-mode DB helper — fetches recent classes (any date/status) and groups by weekday.
Simulates a full-week schedule for local testing without needing real scheduled data.
"""
import logging
from utils.db_connection import get_connection, close_connection, epoch_ms_to_ist, format_time_hinglish, _log

logger = logging.getLogger(__name__)

WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def fetch_week_classes_test(batch_code: str, limit: int = 15):
    """
    Returns last `limit` classes for this batch (any date, any status),
    each tagged with the weekday of their actual start_time.
    Grouped output mirrors what prod would return for a full week.
    """
    _log("")
    _log("=" * 60)
    _log(f"  [WEEKLY TEST] RECENT CLASS LOOKUP")
    _log(f"  batch_code={batch_code}  limit={limit}")
    _log("=" * 60)

    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:

            # STEP 1 — batch
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
                return []
            batch_id = batch["id"]
            _log(f"  ✓ batch_id={batch_id}  exam={batch['exam_name']}")

            # STEP 2 — chapter ids
            cur.execute("SELECT chapter_id FROM av_batch_chapters WHERE batch_id = %s", (batch_id,))
            chapter_ids = [r["chapter_id"] for r in cur.fetchall()]
            if not chapter_ids:
                _log("  ✗ No chapters in batch.")
                return []
            _log(f"  ✓ {len(chapter_ids)} chapter(s) in batch")

            # STEP 3 — last N sessions, any date / any status
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
            _log(f"  ✓ {len(live_rows)} row(s) returned (recent, any date)")

            if not live_rows:
                _log("  ✗ No rows in chapter_live_mapping for this batch.")
                return []

            # STEP 4 — chapter + subject
            unique_chapter_ids = list({r["chapter_id"] for r in live_rows})

            placeholders2 = ",".join(["%s"] * len(unique_chapter_ids))
            cur.execute(
                f"""
                SELECT c.id, c.title AS chapter_name, c.teacher_name,
                       c.video_image, c.hindi_title, c.teacher_name_hindi,
                       s.name AS subject_name
                FROM   chapter c
                LEFT JOIN subject s ON s.id = c.subject_id
                WHERE  c.id IN ({placeholders2})
                """,
                unique_chapter_ids,
            )
            chapter_map = {c["id"]: c for c in cur.fetchall()}

            # Iterate live_rows so every session row is preserved
            results = []
            for row in live_rows:
                c = chapter_map.get(row["chapter_id"])
                if not c:
                    continue
                start_ms  = row["start_time"]
                end_ms    = row["end_time"]
                start_ist = epoch_ms_to_ist(start_ms)
                end_ist   = epoch_ms_to_ist(end_ms) if end_ms else None
                wd        = start_ist.weekday()  # 0=Mon … 6=Sun

                raw_teacher = (c["teacher_name"] or "").strip()
                teacher_name = raw_teacher.removeprefix("By ").strip()
                teacher_gender = "female" if teacher_name.lower().endswith("ma'am") else "male"

                raw_teacher_hindi = (c.get("teacher_name_hindi") or "").strip()
                teacher_name_hindi = raw_teacher_hindi.removesuffix("द्वारा").strip()

                subject_clean = (c["subject_name"] or "").strip().replace(" Board", "").strip()

                results.append({
                    "chapter_id":         c["id"],
                    "chapter_name":       (c["chapter_name"] or "").strip(),
                    "hindi_title":        (c.get("hindi_title") or "").strip(),
                    "teacher_name":       teacher_name,
                    "teacher_name_hindi": teacher_name_hindi,
                    "teacher_gender":     teacher_gender,
                    "subject_name":       subject_clean,
                    "class_time":         format_time_hinglish(start_ist.hour, start_ist.minute),
                    "end_time":           format_time_hinglish(end_ist.hour, end_ist.minute) if end_ist else "",
                    "start_ms":           start_ms,
                    "end_ms":             end_ms,
                    "weekday":            wd,
                    "weekday_name":       WEEKDAY_NAMES[wd] if wd < 7 else "Unknown",
                    "exam_name":          batch["exam_name"],
                    "exam_code":          (batch.get("exam_code") or "").strip(),
                    "grade_name":         batch["grade_name"],
                    "stream_name":        batch["stream_name"],
                    "language":           batch["language"],
                })

            results.sort(key=lambda x: x["start_ms"])
            _log(f"  ✓ [TEST] {len(results)} class(es) across weekdays")
            for r in results:
                _log(f"      {r['weekday_name']} · {r['chapter_name']} · {r['class_time']}")
            return results

    except Exception as e:
        _log(f"  ✗ ERROR: {e}")
        raise
    finally:
        close_connection(conn)
