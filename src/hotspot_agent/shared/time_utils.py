from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def get_timezone(name: str) -> ZoneInfo:
    return ZoneInfo(name)


def now_in_timezone(timezone: ZoneInfo) -> datetime:
    return datetime.now(timezone)


def lookback_window(now: datetime, hours: int) -> tuple[datetime, datetime]:
    return now - timedelta(hours=hours), now
