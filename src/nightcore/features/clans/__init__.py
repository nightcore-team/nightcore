from discord import app_commands

from src.nightcore.bot import Nightcore

from ._groups import clan as clan_main_group

# SIDE-EFFECT IMPORTS
from .commands import info, leave, seq, top
from .commands.manage import (
    change_deputy,
    create,
    delete,
    invite,
    kick,
    settings,
)

__all__ = (
    "change_deputy",
    "create",
    "delete",
    "info",
    "invite",
    "kick",
    "leave",
    "seq",
    "settings",
    "top",
)


async def setup(bot: Nightcore):
    """Setup the clans commands for the Nightcore bot."""
    if not any(
        isinstance(cmd, app_commands.AppCommand) and cmd.name == "config"  # type: ignore
        for cmd in bot.tree.get_commands()
    ):
        bot.tree.add_command(clan_main_group)
