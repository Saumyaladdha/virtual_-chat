"""
Test-mode DB helpers — fetches recent classes regardless of date or status.
Never import this in production flows.
"""
import logging
from utils.db_connection import (
    get_connection, close_connection,
    epoch_ms_to_ist, format_time_hinglish,
    _log,
)

logger = logging.getLogger(__name__)


def fetch_recent_classes(batch_code: str, limit: int = 5):
    """
    Returns the most recent `limit` classes for this batch from any date / any status.
    Used only for local testing when no UPCOMING classes exist today.
    """
    _log("")
    _log("=" * 60)
    _log(f"  [TEST MODE] RECENT CLASS LOOKUP")
    _log(f"  Input batch_code : {batch_code}  |  limit : {limit}")
    _log("=" * 60)

    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:

            # ── STEP 1  av_batches ────────────────────────────────────────
            _log("")
            _log("─" * 60)
            _log("  STEP 1 › av_batches")
            _log("─" * 60)

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
                _log(f"  ✗ No batch found for code '{batch_code}'")
                return []

            batch_id = batch["id"]
            _log(f"  ✓ batch_id={batch_id}  exam={batch['exam_name']}  grade={batch['grade_name']}")

            # ── STEP 2  av_batch_chapters ─────────────────────────────────
            _log("")
            _log("─" * 60)
            _log("  STEP 2 › av_batch_chapters")
            _log("─" * 60)

            cur.execute(
                "SELECT chapter_id FROM av_batch_chapters WHERE batch_id = %s",
                (batch_id,),
            )
            chapter_ids = [r["chapter_id"] for r in cur.fetchall()]
            _log(f"  ✓ {len(chapter_ids)} chapter(s) in batch")

            if not chapter_ids:
                _log("  ✗ Batch has no chapters. Stopping.")
                return []

            # ── STEP 3  chapter_live_mapping  (no date / status filter) ───
            _log("")
            _log("─" * 60)
            _log(f"  STEP 3 › chapter_live_mapping  (any date, any status, last {limit})")
            _log("─" * 60)

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
                _log("  ✗ No rows at all in chapter_live_mapping for this batch.")
                return []

            for row in live_rows:
                start_ist = epoch_ms_to_ist(row["start_time"])
                _log(
                    f"      chapter_id={row['chapter_id'][:16]}...  "
                    f"start={start_ist.strftime('%Y-%m-%d %H:%M IST')}  "
                    f"status={row['status']}"
                )

            # ── STEP 4  chapter JOIN subject ──────────────────────────────
            unique_chapter_ids = list({r["chapter_id"] for r in live_rows})

            _log("")
            _log("─" * 60)
            _log("  STEP 4 › chapter JOIN subject")
            _log("─" * 60)

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
            _log(f"  ✓ {len(chapter_map)} chapter row(s) returned")

            # ── BUILD RESULT — iterate live_rows so every session is preserved ──
            results = []
            for row in live_rows:
                c = chapter_map.get(row["chapter_id"])
                if not c:
                    continue
                start_ms  = row["start_time"]
                start_ist = epoch_ms_to_ist(start_ms)
                class_time = format_time_hinglish(start_ist.hour, start_ist.minute)

                subject_clean = (c["subject_name"] or "").strip().replace(" Board", "").strip()

                raw_teacher    = (c["teacher_name"] or "").strip()
                teacher_name   = raw_teacher.removeprefix("By ").strip()
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
            _log("─" * 60)
            _log(f"  [TEST MODE] RESULT : {len(results)} class(es) ready")
            _log("─" * 60)
            for i, r in enumerate(results, 1):
                _log(f"  Class {i}: {r['chapter_name']} · {r['subject_name']} · {r['class_time']}")

            _log("")
            _log("=" * 60)
            _log("  [TEST MODE] LOOKUP COMPLETE")
            _log("=" * 60)
            return results

    except Exception as e:
        _log(f"  ✗ ERROR: {e}")
        raise
    finally:
        close_connection(conn)
