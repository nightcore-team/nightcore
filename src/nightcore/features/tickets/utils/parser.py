"""Utility functions for parsing ticket-related data."""

import re


def extract_id_from_str(component_str: str) -> int | None:
    """Extract an ID from a string formatted as <@123456789> or <@&123456789>."""  # noqa: E501
    match = re.search(r"<@&?(\d+)>", component_str)
    if match:
        return int(match.group(1))

    match = re.search(r"Предложение\s*#(\d+)", component_str)
    if match:
        return int(match.group(1))

    return None


def extract_str_by_pattern(component_str: str, pattern: str) -> str | None:
    """Extract a substring from a string using a regex pattern."""
    match = re.search(pattern, component_str)
    if match:
        return match.group(1)
    return None
