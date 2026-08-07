"""
Casino casino logic package.

Contains pure game logic (results, spin and per-game state contracts).
Game finalization wiring lives in ``...commands.casino._registry``.
"""

from .base import CasinoState
from .registry import GAME_FINALIZERS, register_finalizer
from .roulette import (
    COLORS,
    RouletteColor,
    RouletteResult,
    red_numbers,
    spin_roulette,
)

__all__ = (
    "COLORS",
    "GAME_FINALIZERS",
    "CasinoState",
    "RouletteColor",
    "RouletteResult",
    "red_numbers",
    "register_finalizer",
    "spin_roulette",
)
