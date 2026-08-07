"""
Registry of casino game finalizers.

Maps a casino game type to the callable that finishes the game: applies
payouts and updates the game message. Each game module registers its own
finalizer via :func:`register_finalizer`.
"""

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from src.utils._enums import CasinoGameTypeEnum

if TYPE_CHECKING:
    from src.infra.db.models.casino import CasinoGame
    from src.nightcore.bot import Nightcore

FinalizerT = Callable[["Nightcore", "CasinoGame"], Awaitable[None]]

GAME_FINALIZERS: dict[CasinoGameTypeEnum, FinalizerT] = {}


def register_finalizer(
    game_type: CasinoGameTypeEnum,
) -> Callable[[FinalizerT], FinalizerT]:
    """Register a finalizer for a casino game type.

    Args:
        game_type: The casino game type the finalizer belongs to.

    Returns:
        A decorator that registers the wrapped callable.
    """

    def decorator(finalizer: FinalizerT) -> FinalizerT:
        GAME_FINALIZERS[game_type] = finalizer
        return finalizer

    return decorator
