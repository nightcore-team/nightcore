"""Utility functions for forum operations."""


def extract_discord_id(title: str) -> int | None:
    """Extract the first sequence of digits from the title as a Discord ID."""
    i = 0
    n = len(title)
    while i < n:
        if title[i].isdigit():
            start = i
            while i < n and title[i].isdigit():
                i += 1
            return int(title[start:i])
        i += 1
    return None
