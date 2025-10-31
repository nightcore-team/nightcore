"""Casino game utilities."""

import random
from typing import Literal

RouletteColor = Literal["red", "black", "green"]


class RouletteResult:
    """Roulette game result."""

    def __init__(
        self,
        number: int,
        color: RouletteColor,
        bet: int,
        selected_color: RouletteColor,
    ):
        self.number = number
        self.color = color
        self.bet = bet
        self.selected_color = selected_color

    @property
    def is_win(self) -> bool:
        """Check if user won."""
        return self.color == self.selected_color

    @property
    def multiplier(self) -> float:
        """Get win multiplier."""
        if self.color == "green":
            return 14.0
        return 2.0

    @property
    def coins_change(self) -> int:
        """Calculate coins change."""
        if self.is_win:
            return int(self.bet * self.multiplier) - self.bet  # clear win
        return -self.bet  # loss

    @property
    def color_emoji(self) -> str:
        """Get color emoji."""
        if self.color == "green":
            return "🟢"
        elif self.color == "red":
            return "🔴"
        return "⚫"

    @property
    def selected_color_emoji(self) -> str:
        """Get selected color emoji."""
        if self.selected_color == "green":
            return "🟢"
        elif self.selected_color == "red":
            return "🔴"
        return "⚫"


def spin_roulette() -> tuple[int, RouletteColor]:
    """Spin the roulette wheel.

    Returns:
        Tuple of (number, color)

    European roulette:
        - 0: green (1/37 chance)
        - 1-36: red/black (18/37 each)
    """
    number = random.randint(0, 36)

    if number == 0:
        return number, "green"

    red_numbers = {
        1,
        3,
        5,
        7,
        9,
        12,
        14,
        16,
        18,
        19,
        21,
        23,
        25,
        27,
        30,
        32,
        34,
        36,
    }

    if number in red_numbers:
        return number, "red"

    return number, "black"
