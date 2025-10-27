from typing import TYPE_CHECKING

from discord import app_commands

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from ._groups import give as give_group

# SIDE-EFFECT IMPORTS
from .commands.give import clanrep, coins

__all__ = ("clanrep", "coins")


async def setup(bot: "Nightcore"):
    """Setup the clans commands for the Nightcore bot."""
    if not any(
        isinstance(cmd, app_commands.AppCommand) and cmd.name == "config"  # type: ignore
        for cmd in bot.tree.get_commands()
    ):
        bot.tree.add_command(give_group)
