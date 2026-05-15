"""
DB helpers for Category 3 — Poll messages.
Today's class poll  → reuses fetch_today_classes from db_utils.
Yesterday watch-check poll → reuses fetch_yesterday_classes from db_utils_pyq.
"""
from utils.db_live import fetch_today_classes
from utils.db_pyq import fetch_yesterday_classes


def fetch_today_poll_class(batch_code: str):
    """
    Returns (class_dict | None) — one class picked from today's UPCOMING sessions.
    In production we return all classes and let the UI pick one randomly.
    """
    return fetch_today_classes(batch_code)


def fetch_yesterday_watch_class(batch_code: str):
    """
    Returns (classes, days_ago) — yesterday's (or 2-days-ago) classes for watch-check poll.
    """
    return fetch_yesterday_classes(batch_code)
