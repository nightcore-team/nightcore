"""Utility functions for time-related operations."""

from datetime import datetime, timezone


def discord_ts(dt: datetime, style: str = "f") -> str:
    """Convert a datetime to a Discord timestamp string."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return f"<t:{int(dt.timestamp())}:{style}>"
