"""Utility functions for winter holidays feature."""

from contextlib import suppress
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

HOLIDAYS = {
    "gregorian": {
        "<:snowflake1:1449139461215490078>  Новый Год": (1, 1, "1 Января"),
        "<:christmastree:1449140197051601077> Рождество": (
            12,
            25,
            "25 Декабря",
        ),
    },
    "julian": {
        "<:snowflake1:1449139461215490078>  Новый Год": (1, 14, "14 Января"),
        "<:christmastree:1449140197051601077> Рождество": (1, 7, "7 Января"),
    },
}

CITY_MAP = {
    "київ": "Europe/Kyiv",
    "киев": "Europe/Kyiv",
    "kyiv": "Europe/Kyiv",
    "prague": "Europe/Prague",
    "прага": "Europe/Prague",
    "warsaw": "Europe/Warsaw",
    "new york": "America/New_York",
    "нью йорк": "America/New_York",
    "london": "Europe/London",
    "лондон": "Europe/London",
    "moscow": "Europe/Moscow",
    "москва": "Europe/Moscow",
    "beijing": "Asia/Shanghai",
    "пекин": "Asia/Shanghai",
    "berlin": "Europe/Berlin",
    "берлин": "Europe/Berlin",
    "dresden": "Europe/Berlin",
    "дрезден": "Europe/Berlin",
}


def parse_timezone(user_input: str) -> ZoneInfo | None:
    """Parse user input into a valid timezone string."""

    original_input = user_input.strip()
    user_input_lower = original_input.lower()

    with suppress(ZoneInfoNotFoundError):
        result = ZoneInfo(original_input)  # ✅ Використовуємо original_input
        return result

    with suppress(ZoneInfoNotFoundError):
        parts = user_input_lower.split("/")
        if len(parts) == 2:
            tz_name = f"{parts[0].title()}/{parts[1].title()}"
            result = ZoneInfo(tz_name)
            return result

    # 3. UTC ± X
    if user_input_lower.startswith("utc"):
        with suppress(Exception):
            offset = int(user_input_lower[3:])
            result = ZoneInfo(f"Etc/GMT{-offset}")
            return result

    # 4. Cities map
    if user_input_lower in CITY_MAP:
        result = ZoneInfo(CITY_MAP[user_input_lower])
        return result

    return None


def get_all_holidays(timezone: ZoneInfo, calendar: str):
    """
    Return a list of dictionaries with:
    - name: holiday name (e.g. "1 Января")
    - target: datetime of the holiday in user's timezone
    - days, hours, minutes, seconds: time remaining.
    """  # noqa: D205

    now = datetime.now(tz=timezone)
    results: list[dict[str, object]] = []

    for name, (month, day, date) in HOLIDAYS[calendar].items():
        target = datetime(year=now.year, month=month, day=day, tzinfo=timezone)

        if target <= now:
            target = target.replace(year=now.year + 1)

        diff = target - now

        days = diff.days
        seconds = diff.seconds

        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        results.append(
            {
                "name": name,
                "month": date,
                "target": target,
                "days": days,
                "hours": hours,
                "minutes": minutes,
                "seconds": secs,
            }
        )

    return results
