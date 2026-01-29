"""Utility functions for forum operations."""

import re


def extract_discord_id(title: str) -> int | None:
    """Extract Discord ID from title after 'Жалоба' pattern.

    Expects format: '... | Жалоба на [role] [discord_id]. Причина: ...'
    """
    pattern = r"Жалоба\s+на\s+(?:модератора|руководство)\s+(\d+)"
    match = re.search(pattern, title)
    if match:
        return int(match.group(1))
    return None
