from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def parse_clock(value: str) -> time:
    hour, minute = value.split(":")
    return time(int(hour), int(minute))


def quiet_hours_end(moment: datetime, tz_name: str, start: str | None, end: str | None) -> datetime | None:
    if not start or not end or start == end:
        return None
    try:
        tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        tz = timezone.utc

    local = moment.astimezone(tz)
    start_t, end_t = parse_clock(start), parse_clock(end)
    now_t = local.time().replace(second=0, microsecond=0)

    if start_t < end_t:
        inside = start_t <= now_t < end_t
        end_day = local.date()
    else:
        inside = now_t >= start_t or now_t < end_t
        end_day = local.date() if now_t < end_t else local.date() + timedelta(days=1)

    if not inside:
        return None
    return datetime.combine(end_day, end_t, tzinfo=tz).astimezone(timezone.utc)
