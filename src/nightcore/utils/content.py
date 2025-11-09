"""Utilities related to content."""

import re


def has_url_in_content(content: str) -> bool:
    """Check if the content contains a URL."""
    url_pattern = re.compile(
        r"(https?://[^\s]+)|(www\.[^\s]+)",
        re.IGNORECASE,
    )
    return bool(url_pattern.search(content))
