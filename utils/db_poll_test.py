"""
Test-mode DB helpers for Category 3 — Poll messages.
Fetches most recent classes regardless of date/status.
Never import this in production flows.
"""
from utils.db_test import fetch_recent_classes
from utils.db_pyq_test import fetch_yesterday_classes as _fetch_recent_pyq


def fetch_today_poll_class(batch_code: str, limit: int = 5):
    """
    Returns list of recent classes (any date) for today-poll test mode.
    """
    return fetch_recent_classes(batch_code, limit=limit)


def fetch_yesterday_watch_class(batch_code: str, limit: int = 5):
    """
    Returns (classes, days_ago=1) using most recent classes for watch-check test mode.
    """
    return _fetch_recent_pyq(batch_code, limit=limit)
