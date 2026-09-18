"""Generate Mon–Fri availability slots (America/Mexico_City)."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

MEXICO_CITY = ZoneInfo("America/Mexico_City")
DEFAULT_OPEN_HOUR = 9
DEFAULT_CLOSE_HOUR = 18
DEFAULT_DAYS_AHEAD = 30


def _is_weekday(day: date) -> bool:
    return day.weekday() < 5


def generate_signing_schedule_by_date(
    *,
    days_ahead: int = DEFAULT_DAYS_AHEAD,
    slot_minutes: int = 45,
    open_hour: int = DEFAULT_OPEN_HOUR,
    close_hour: int = DEFAULT_CLOSE_HOUR,
    start_from: datetime | None = None,
) -> dict[str, list[str]]:
    """Return {YYYY-MM-DD: [HH:MM, ...]} for weekdays in the next ``days_ahead`` days."""
    now = start_from or datetime.now(MEXICO_CITY)
    if now.tzinfo is None:
        now = now.replace(tzinfo=MEXICO_CITY)
    else:
        now = now.astimezone(MEXICO_CITY)

    last_day = now.date() + timedelta(days=days_ahead)
    current_day = now.date()
    schedule: dict[str, list[str]] = {}

    while current_day <= last_day:
        if _is_weekday(current_day):
            slot_start = datetime(
                current_day.year,
                current_day.month,
                current_day.day,
                open_hour,
                0,
                tzinfo=MEXICO_CITY,
            )
            day_end = datetime(
                current_day.year,
                current_day.month,
                current_day.day,
                close_hour,
                0,
                tzinfo=MEXICO_CITY,
            )
            times: list[str] = []
            while slot_start + timedelta(minutes=slot_minutes) <= day_end:
                if slot_start > now:
                    times.append(slot_start.strftime("%H:%M"))
                slot_start += timedelta(minutes=slot_minutes)
            if times:
                schedule[current_day.isoformat()] = times
        current_day += timedelta(days=1)

    return schedule


def generate_signing_slots(
    *,
    slot_minutes: int = 45,
    weeks_ahead: int = 4,
    days_ahead: int | None = None,
    open_hour: int = DEFAULT_OPEN_HOUR,
    close_hour: int = DEFAULT_CLOSE_HOUR,
    start_from: datetime | None = None,
) -> list[str]:
    """Return human-readable slot labels (legacy flat list)."""
    if days_ahead is not None:
        horizon_days = days_ahead
    else:
        horizon_days = max(1, weeks_ahead * 7)

    by_date = generate_signing_schedule_by_date(
        days_ahead=horizon_days,
        slot_minutes=slot_minutes,
        open_hour=open_hour,
        close_hour=close_hour,
        start_from=start_from,
    )
    labels: list[str] = []
    for day_iso, times in sorted(by_date.items()):
        day = date.fromisoformat(day_iso)
        day_name = day.strftime("%A")
        for time_label in times:
            labels.append(f"{day_name} {day.strftime('%d/%m/%Y')} {time_label} (CDMX)")
    return labels
