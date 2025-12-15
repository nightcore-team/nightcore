from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from ._groups import system as config_group

# SIDE-EFFECT IMPORTS
from .commands.config import access, info

__all__ = ("access", "info")


async def setup(bot: Nightcore):
    """Setup the configuration commands for the Nightcore bot."""
    bot.tree.add_command(config_group)
