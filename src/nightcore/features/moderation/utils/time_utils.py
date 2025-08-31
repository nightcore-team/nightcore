"""Utilities for parsing and formatting time durations."""

from datetime import datetime, timedelta, timezone

_TIME_UNITS = {
    "s": 1,
    "m": 60,
    "h": 60 * 60,
    "d": 24 * 60 * 60,
    "w": 7 * 24 * 60 * 60,
}


def parse_duration(text: str) -> int | None:
    """Parse a duration string into total seconds."""
    if not text:
        return None

    text = text.strip().lower()

    if not text:
        return None

    if text.isdigit():
        return int(text)

    total = 0
    number_buf = ""
    for ch in text:
        if ch.isdigit():
            number_buf += ch
            continue
        if ch in _TIME_UNITS and number_buf:
            total += int(number_buf) * _TIME_UNITS[ch]
            number_buf = ""
        else:
            return None
    if number_buf:
        total += int(number_buf)

    return total if total > 0 else None


def calculate_end_time(duration: int) -> datetime:
    """Calculate the end time based on the current time and duration in seconds."""  # noqa: E501

    try:
        seconds = float(duration)
    except (ValueError, TypeError) as e:
        raise ValueError("Invalid duration format") from e

    return datetime.now(timezone.utc) + timedelta(seconds=seconds)
