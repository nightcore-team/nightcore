"""Utilities for handling cases opening in the economy feature."""

import random
from typing import Final

from src.infra.db.models._annot import CoinDropAnnot, ColorDropAnnot

CASES_NAMES: Final[dict[str, str]] = {
    "coins_case": "Кейс с коинами",
    "colors_case": "Кейс с цветами",
}


def open_coins_case(drops: list[CoinDropAnnot]) -> tuple[int, int]:
    """Open coins case and get reward.

    Args:
        drops: List of coin drops with amount and chance

    Returns:
        Tuple of (coins_amount, drop_chance)
    """
    if not drops:
        raise ValueError("Case has no drops configured")

    amounts = [drop["amount"] for drop in drops]
    chances = [drop["chance"] for drop in drops]

    # Weighted random choice
    selected_amount = random.choices(amounts, weights=chances, k=1)[0]

    # Get chance of this drop
    drop = next(d for d in drops if d["amount"] == selected_amount)

    return selected_amount, drop["chance"]


def open_colors_case(drops: dict[str, ColorDropAnnot]) -> tuple[str, int, int]:
    """Open colors case and get reward.

    Args:
        drops: Dictionary of color drops with role_id and chance

    Returns:
        Tuple of (color_key, role_id, chance)
        Example: ("color_1", 1433436907865378800, 20)
    """
    if not drops:
        raise ValueError("Case has no drops configured")

    color_keys = list(drops.keys())
    role_ids = [drop["role_id"] for drop in drops.values()]
    chances = [drop["chance"] for drop in drops.values()]

    selected_index = random.choices(range(len(drops)), weights=chances, k=1)[0]

    color_key = color_keys[selected_index]
    role_id = role_ids[selected_index]
    chance = chances[selected_index]

    return color_key, role_id, chance
