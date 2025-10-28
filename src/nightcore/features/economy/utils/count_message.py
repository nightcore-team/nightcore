"""Module for experience calculation formulas."""

import math


def calculate_user_exp_to_level(level: int) -> int:
    """
    Calculate experience required for user to reach the next level.

    Formula: 70 * level^1.5 - 70 * level

    Args:
        level: Current user level

    Returns:
        Experience points required for next level
    """
    x = 70.0
    y = 1.5
    return int(x * math.pow(level, y) - (x * level))


def calculate_clan_exp_to_level(level: int) -> int:
    """
    Calculate experience required for clan to reach the next level.

    Formula: 40 * level^1.85 - 40 * level

    Args:
        level: Current clan level

    Returns:
        Experience points required for next level
    """
    x = 40.0
    y = 1.85
    return int(x * math.pow(level, y) - (x * level))
