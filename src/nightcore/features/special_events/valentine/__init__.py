from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

# SIDE-EFFECT IMPORTS
from ._groups import valentine as valentine_group
from .commands import send, top

__all__ = (
    "send",
    "top",
)


async def setup(bot: Nightcore):
    """Setup the valentine commands for the Nightcore bot."""
    bot.tree.add_command(valentine_group)
