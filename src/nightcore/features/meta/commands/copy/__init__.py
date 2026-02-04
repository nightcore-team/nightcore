from src.nightcore.bot import Nightcore

from . import permissions

# SIDE-EFFECT IMPORTS
from ._groups import copy as copy_group

__all__ = ("permissions",)


async def setup(bot: Nightcore):
    """Setup the copy commands for the Nightcore bot."""
    bot.tree.add_command(copy_group)
