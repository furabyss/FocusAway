from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def current_time_iso(timezone_name: str) -> str:
    return datetime.now(ZoneInfo(timezone_name)).isoformat()


def current_week_anchor(timezone_name: str) -> str:
    now = datetime.now(ZoneInfo(timezone_name))
    monday = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    return monday.isoformat()

