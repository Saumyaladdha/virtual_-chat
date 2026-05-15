"""
DB helpers for Category 1A — Daily Live Class Reminder.
Fetches today's UPCOMING live classes for a given batch code.
"""
import logging
from datetime import datetime
from typing import List, Dict

import pymysql

from utils.db_connection import (
    get_connection, close_connection,
    epoch_ms_to_ist, format_time_hinglish,
    IST, _log,
)

logger = logging.getLogger(__name__)


def fetch_today_classes(batch_code: str) -> List[Dict]:
    """
    Returns a list of today's UPCOMING live classes for the batch.
    Returns [] if no classes found or on error.
    """
    _log("")
    _log("=" * 60)
    _log("  BATCH LOOKUP STARTED")
    _log(f"  Input batch_code : {batch_code}")
    _log("=" * 60)

    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:

            # STEP 1 — batch metadata
            _log("\n" + "─" * 60)
            _log("  STEP 1 › av_batches")
            cur.execute(
                """
                SELECT b.id, b.code, b.language,
                       e.name AS exam_name, e.code AS exam_code,
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
            batch = cur.fetchone()
            if not batch:
                _log(f"  ✗ No batch found for code '{batch_code}'")
                return []

            batch_id = batch["id"]
            _log(f"  ✓ batch_id={batch_id} | exam={batch['exam_name']} | grade={batch['grade_name']} | lang={batch['language']}")

            # STEP 2 — chapter IDs in this batch
            _log("\n" + "─" * 60)
            _log("  STEP 2 › av_batch_chapters")
            cur.execute("SELECT chapter_id FROM av_batch_chapters WHERE batch_id = %s", (batch_id,))
            chapter_ids = [r["chapter_id"] for r in cur.fetchall()]
            _log(f"  ✓ {len(chapter_ids)} chapter(s) in batch")
            if not chapter_ids:
                return []

            # STEP 3 — today's UPCOMING sessions
            now_ist = datetime.now(IST)
            today_start_ms = int(datetime(now_ist.year, now_ist.month, now_ist.day, 0, 0, 0, tzinfo=IST).timestamp() * 1000)
            today_end_ms   = int(datetime(now_ist.year, now_ist.month, now_ist.day, 23, 59, 59, tzinfo=IST).timestamp() * 1000)

            _log("\n" + "─" * 60)
            _log(f"  STEP 3 › chapter_live_mapping  [{now_ist.strftime('%Y-%m-%d')} IST]")
            placeholders = ",".join(["%s"] * len(chapter_ids))
            cur.execute(
                f"""
                SELECT chapter_id, start_time, end_time, status
                FROM   chapter_live_mapping
                WHERE  chapter_id IN ({placeholders})
                  AND  status = 'UPCOMING'
                  AND  start_time >= %s AND start_time <= %s
                ORDER  BY start_time ASC
                """,
                chapter_ids + [today_start_ms, today_end_ms],
            )
            live_rows = cur.fetchall()
            _log(f"  ✓ {len(live_rows)} UPCOMING session(s) for today")
            if not live_rows:
                return []

            # STEP 4 — chapter + subject details
            today_chapter_ids = list({r["chapter_id"] for r in live_rows})  # unique ids for JOIN

            _log("\n" + "─" * 60)
            _log("  STEP 4 › chapter JOIN subject")
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
            chapter_map = {c["id"]: c for c in cur.fetchall()}

            # BUILD RESULT — iterate live_rows so every session row is preserved
            results = []
            for row in live_rows:
                c = chapter_map.get(row["chapter_id"])
                if not c:
                    continue
                start_ms   = row["start_time"]
                start_ist  = epoch_ms_to_ist(start_ms)
                class_time = format_time_hinglish(start_ist.hour, start_ist.minute)

                subject_clean      = (c["subject_name"] or "").strip().replace(" Board", "").strip()
                raw_teacher        = (c["teacher_name"] or "").strip()
                teacher_name       = raw_teacher.removeprefix("By ").strip()
                teacher_gender     = "female" if teacher_name.lower().endswith("ma'am") else "male"
                teacher_name_hindi = (c.get("teacher_name_hindi") or "").strip().removesuffix("द्वारा").strip()

                results.append({
                    "chapter_id":          c["id"],
                    "chapter_name":        (c["chapter_name"] or "").strip(),
                    "hindi_title":         (c.get("hindi_title") or "").strip(),
                    "teacher_name":        teacher_name,
                    "teacher_name_hindi":  teacher_name_hindi,
                    "teacher_gender":      teacher_gender,
                    "subject_name":        subject_clean,
                    "class_time":          class_time,
                    "start_ms":            start_ms,
                    "video_image":         (c.get("video_image") or "").strip(),
                    "exam_name":           batch["exam_name"],
                    "exam_code":           (batch.get("exam_code") or "").strip(),
                    "grade_name":          batch["grade_name"],
                    "stream_name":         batch["stream_name"],
                    "language":            batch["language"],
                })

            results.sort(key=lambda x: x["start_ms"])
            _log(f"\n  FINAL: {len(results)} class(es) ready")
            return results

    except pymysql.Error as e:
        _log(f"  ✗ MySQL ERROR: {e}")
        raise
    finally:
        close_connection(conn)
