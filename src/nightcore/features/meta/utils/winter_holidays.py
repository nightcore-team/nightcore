"""Utility functions related to winter hlidays command."""

from contextlib import suppress

# from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

HOLIDAYS: dict[str, dict[str, tuple[int, int, str]]] = {
    "gregorian": {
        "new_year": (1, 1, "1 Января"),
        "christmas": (12, 25, "25 Декабря"),
    },
    "julian": {
        "new_year": (1, 14, "14 Января"),
        "christmas": (1, 7, "7 Января"),
    },
}

CITY_MAP = {
    "київ": "Europe/Kyiv",
    "kyiv": "Europe/Kyiv",
    "prague": "Europe/Prague",
    "прага": "Europe/Prague",
    "warsaw": "Europe/Warsaw",
    "new york": "America/New_York",
    "нью йорк": "America/New_York",
    "los angeles": "America/Los_Angeles",
    "лос анджелес": "America/Los_Angeles",
    "london": "Europe/London",
    "лондон": "Europe/London",
    "berlin": "Europe/Berlin",
    "берлин": "Europe/Berlin",
    "moscow": "Europe/Moscow",
    "москва": "Europe/Moscow",
}


def parse_timezone(user_input: str) -> str | None:
    """Parse user input into a valid timezone string."""
    user_input = user_input.strip().lower()

    try:
        ZoneInfo(user_input)
        return user_input
    except ZoneInfoNotFoundError:
        pass

    # 2. UTC±X
    if user_input.startswith("utc"):
        with suppress(Exception):
            offset = int(user_input[3:])
            return f"Etc/GMT{-offset}"

    # 3. Cities
    if user_input in CITY_MAP:
        return CITY_MAP[user_input]

    return None


# def get_time_to_holiday(
#     timezone: str,
#     calendar: str,
# ) -> tuple[int, int, int, int, str]:
#     """Get time to the nearest holiday in the given timezone and calendar."""

#     now = datetime.now(ZoneInfo(timezone))

#     nearest_diff: datetime | None = None
#     nearest_holiday_name = ""

#     for month, day, display_name in HOLIDAYS[calendar].values():
#         target = datetime(now.year, month, day, tzinfo=ZoneInfo(timezone))

#         if target <= now:
#             target = target.replace(year=now.year + 1)

#         diff = target - now

#         if nearest_diff is None or diff < nearest_diff:
#             nearest_diff = diff
#             nearest_holiday_name = display_name

#     days = nearest_diff.days
#     seconds = nearest_diff.seconds
#     hours = seconds // 3600
#     minutes = (seconds % 3600) // 60
#     secs = seconds % 60

#     return days, hours, minutes, secs, nearest_holiday_name
