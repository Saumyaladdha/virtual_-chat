"""
Test-mode DB helpers for Common Mistake Alert (Category 11).
Fetches most recent classes regardless of date.
Never import this in production flows.
"""
from utils.db_pyq_test import fetch_yesterday_classes as _fetch_recent


def fetch_mistake_class(batch_code: str, limit: int = 5):
    """Returns (classes, days_ago=1) using most recent classes for test mode."""
    return _fetch_recent(batch_code, limit=limit)
