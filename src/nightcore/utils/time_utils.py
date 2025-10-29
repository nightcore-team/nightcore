"""Utility functions for time-related operations."""

from datetime import datetime, timezone


def discord_ts(dt: datetime, style: str = "f") -> str:
    """Convert a datetime to a Discord timestamp string."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return f"<t:{int(dt.timestamp())}:{style}>"


def format_voice_time(seconds: int) -> str:
    """Format voice activity time."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    remaining_seconds = seconds % 60

    if hours > 0:
        return f"{hours}ч {minutes}м"
    elif minutes > 0:
        return f"{minutes}м {remaining_seconds}с"  # noqa: RUF001
    else:
        return f"{remaining_seconds}с"  # noqa: RUF001
