"""Utilities for parsing and formatting time durations."""

import re
from datetime import UTC, datetime, timedelta


def discord_ts(dt: datetime, style: str = "f") -> str:
    """Convert a datetime to a Discord timestamp string."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return f"<t:{int(dt.timestamp())}:{style}>"


def format_voice_time(seconds: int) -> str:
    """Format voice activity time."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    remaining_seconds = seconds % 60

    if hours > 0:
        return f"{hours}ч {minutes}м"
    elif minutes > 0:
        return f"{minutes}м {remaining_seconds}с"
    else:
        return f"{remaining_seconds}с"


_NUMERIC_FORMATS: tuple[str, ...] = (
    # Day-Month-Year
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%d.%m.%Y",
    "%d %m %Y",
    # Month-Day-Year
    "%m-%d-%Y",
    "%m/%d/%Y",
    "%m.%d.%Y",
    "%m %d %Y",
    # Year-Month-Day
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%Y.%m.%d",
    "%Y %m %d",
    # Two-digit year variants
    "%d-%m-%y",
    "%d/%m/%y",
    "%d.%m/%y",
    "%d %m %y",
    "%m-%d-%y",
    "%m/%d/%y",
    "%m.%d/%y".replace("/", "."),
    "%m %d %y",
    "%y-%m-%d",
    "%y/%m/%d",
    "%y.%m.%d",
    "%y %m %d",
)

_MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}

_SEP_PATTERN = re.compile(r"[.\-/\s]+")


_TIME_UNITS = {
    "s": 1,
    "m": 60,
    "h": 60 * 60,
    "d": 24 * 60 * 60,
    "w": 7 * 24 * 60 * 60,
}


def parse_duration(text: str) -> int | None:
    """Parse a duration string into total seconds.

    Valid formats:
        - "30s" → 30 seconds
        - "5m" → 300 seconds
        - "2h30m" → 9000 seconds
        - "1d" → 86400 seconds

    Invalid formats:
        - "123" → None (no unit)
        - "abc" → None (no numbers)
        - "" → None (empty)

    Returns:
        Total seconds or None if invalid format
    """

    if not text:
        return None

    if len(text) > 5:
        return None

    text = text.strip().lower()

    if not text:
        return None

    if text.isdigit():
        return None

    total = 0
    number_buf = ""
    has_valid_unit = False  # To ensure at least one valid unit is found

    for ch in text:
        if ch.isdigit():
            number_buf += ch
            continue

        if ch in _TIME_UNITS and number_buf:
            total += int(number_buf) * _TIME_UNITS[ch]
            number_buf = ""
            has_valid_unit = True
        else:
            return None

    if number_buf:
        return None

    if not has_valid_unit:
        return None

    return total if total > 0 else None


def calculate_end_time(duration: int) -> datetime:
    """Calculate the end time based on the current time and duration in seconds."""  # noqa: E501

    try:
        seconds = float(duration)
    except (ValueError, TypeError) as e:
        raise ValueError("Invalid duration format") from e

    return datetime.now(UTC) + timedelta(seconds=seconds)


def _normalize_two_digit_year(y: int, *, pivot: int = 70) -> int:
    if y < 100:
        return 2000 + y if y <= pivot - 1 else 1900 + y
    return y


def _try_strptime_numeric(s: str) -> datetime | None:
    for fmt in _NUMERIC_FORMATS:
        try:
            dt = datetime.strptime(s, fmt)
            # normalize two-digit year if needed
            y = (
                _normalize_two_digit_year(dt.year)
                if "%y" in fmt and "%Y" not in fmt
                else dt.year
            )
            return dt.replace(year=y)
        except ValueError:
            continue
    return None


def _parse_tokens_numeric(
    tokens: list[int], *, day_first: bool
) -> tuple[int, int, int] | None:
    """Infer day, month, year from three numeric tokens."""
    if len(tokens) != 3:
        return None

    a, b, c = tokens

    # Determine the year:
    if len(str(a)) == 4:
        year = a
        x, y = b, c
    elif len(str(b)) == 4:
        year = b
        x, y = a, c
    elif len(str(c)) == 4:
        year = c
        x, y = a, b
    else:
        # None is 4-digit year -> take last as year (two-digit)
        year = _normalize_two_digit_year(c)
        x, y = a, b

    # Infer month/day from x,y
    candidates: list[tuple[str, int, int]] = []
    # day_first
    if 1 <= x <= 31 and 1 <= y <= 12:
        candidates.append(("DM", x, y))
    # month_first
    if 1 <= x <= 12 and 1 <= y <= 31:
        candidates.append(("MD", y, x))

    if not candidates:
        return None

    # If unambiguous (one candidate):
    if len(candidates) == 1:
        _, d, m = candidates[0]
        return (d, m, year)

    # Two candidates (both <= 12) -> apply day_first priority
    if day_first:
        # look for "DM"
        for tag, d, m in candidates:
            if tag == "DM":
                return (d, m, year)
    else:
        for tag, d, m in candidates:
            if tag == "MD":
                return (d, m, year)

    # In case something goes wrong — return the first one
    _, d, m = candidates[0]
    return (d, m, year)


def _try_alpha_month(s: str, *, day_first: bool) -> datetime | None:
    parts = _SEP_PATTERN.split(s.strip().lower())
    if len(parts) < 3:
        return None

    # Convert parts: numbers or month
    nums: list[int] = []
    month: int | None = None
    for p in parts:
        if p.isdigit():
            nums.append(int(p))
        else:
            m = _MONTHS.get(p)
            if m:
                month = m

    if month is None or len(nums) < 2:
        return None

    # Determine the year: look for a 4-digit value or take the largest
    year_candidates = [n for n in nums if n >= 1000]
    if year_candidates:
        year = year_candidates[0]
        nums.remove(year)
    else:
        # two-digit year at the end/beginning
        # prefer the last number as the year
        year = _normalize_two_digit_year(nums[-1])
        nums = nums[:-1]

    if len(nums) < 1:
        return None

    # 1 or 2 numbers remain -> day/month
    if len(nums) == 1:
        # if only one — it's the day
        day = nums[0]
        m = month
    else:
        a, b = nums[0], nums[1]
        # if one of them matches the month — the other is the day
        if a == month:
            day, m = b, month
        elif b == month:
            day, m = a, month
        else:
            # ambiguous -> apply day_first
            if day_first:
                day, m = a, month
            else:
                day, m = b, month

    try:
        return datetime(year, m, day)
    except ValueError:
        return None


def parse_date_utc(
    s: str,
    *,
    day_first: bool = True,
    set_time_to_now: bool = False,
    only_date: bool = False,
) -> datetime:
    """Parse a date string into a timezone-aware datetime in UTC."""
    raw = s.strip()
    if not raw:
        raise ValueError("Empty date string")

    # 1) Try quick numeric formats
    dt = _try_strptime_numeric(raw)
    if dt is None:
        # 2) Try a textual month
        dt = _try_alpha_month(raw, day_first=day_first)

    if dt is None:
        # 3) Infer from three numbers (formatless case)
        parts = _SEP_PATTERN.split(raw)
        nums: list[int] = []
        for p in parts:
            if p.isdigit():
                nums.append(int(p))
        triple = _parse_tokens_numeric(nums, day_first=day_first)
        if triple is None:
            raise ValueError(f"Cannot parse date: {s!r}")
        d, m, y = triple
        try:
            dt = datetime(y, m, d)
        except ValueError as e:
            raise ValueError(f"Invalid date: {e}") from e

    # Got a naive datetime -> make it aware in UTC
    if set_time_to_now:
        now = datetime.now(UTC)
        dt = dt.replace(
            hour=now.hour,
            minute=now.minute,
            second=now.second,
            microsecond=now.microsecond,
            tzinfo=UTC,
        )
    else:
        dt = dt.replace(tzinfo=UTC)

    return dt


def compare_date_range(from_date: str | None, to_date: str | None):
    """Normalize a date range from strings to datetime objects."""

    if from_date:
        from_dt = parse_date_utc(from_date)
    else:
        now = datetime.now(UTC)
        monday = now.date() - timedelta(days=now.weekday())
        from_dt = datetime(monday.year, monday.month, monday.day, tzinfo=UTC)

    if to_date:
        to_dt = parse_date_utc(to_date)
    else:
        now = datetime.now(UTC)
        sunday = now.date() - timedelta(days=now.weekday() - 6)

        to_dt = datetime(
            sunday.year, sunday.month, sunday.day, tzinfo=UTC
        ) + timedelta(days=1)

    return from_dt, to_dt


"""
parse_date_utc("2025-01-15")
parse_date_utc("15/01/2025")
parse_date_utc("15 January 2025")
parse_date_utc("Jan 15, 2025")
parse_date_utc("15-01-25")
parse_date_utc("2025 01 15")
parse_date_utc("15.01.2025")

"""
