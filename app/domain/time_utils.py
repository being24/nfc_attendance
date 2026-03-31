from datetime import datetime
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")


def ensure_jst(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=JST)
    return dt.astimezone(JST)


def now_jst() -> datetime:
    return datetime.now(JST)


def to_unix_seconds(dt: datetime) -> int:
    return int(ensure_jst(dt).timestamp())


def from_unix_seconds(ts: int) -> datetime:
    return datetime.fromtimestamp(ts, JST)


def now_ts() -> int:
    return to_unix_seconds(now_jst())


def minutes_between(start: datetime, end: datetime) -> int:
    start_jst = ensure_jst(start)
    end_jst = ensure_jst(end)
    delta_minutes = int((end_jst - start_jst).total_seconds() // 60)
    return clamp_non_negative_minutes(delta_minutes)


def clamp_non_negative_minutes(value: int) -> int:
    return max(0, value)
