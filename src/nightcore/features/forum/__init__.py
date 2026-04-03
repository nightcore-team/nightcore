from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from ._groups import forum as forum_group

# SIDE-EFFECT IMPORTS
from .commands.forum import add, delete

__all__ = ("add", "delete")


async def setup(bot: "Nightcore"):
    """Setup the forum commands for the Nightcore bot."""

    bot.tree.add_command(forum_group)
