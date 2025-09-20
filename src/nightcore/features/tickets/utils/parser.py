"""Utility functions for parsing ticket-related data."""

import re


def extract_id_from_str(component_str: str) -> int:
    """Extract an ID from a string formatted as <@123456789> or <@&123456789>."""  # noqa: E501
    match = re.search(r"<@&?(\d+)>", component_str)
    if match is None:
        raise ValueError(f"Could not extract ID from: {component_str!r}")
    return int(match.group(1))
