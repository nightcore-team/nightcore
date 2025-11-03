from discord import app_commands

from src.nightcore.bot import Nightcore

from ._groups import config as config_group

# SIDE-EFFECT IMPORTS
from .commands import (
    clans,
    economy,
    infomaker,
    levels,
    logging,
    main,
    moderation,
    moderstats,
    notifications,
    private_channels,
    tickets,
)
from .commands.battlepass import add_level, change_level, delete_level

__all__ = (
    "add_level",
    "change_level",
    "clans",
    "delete_level",
    "economy",
    "infomaker",
    "levels",
    "logging",
    "main",
    "moderation",
    "moderstats",
    "notifications",
    "private_channels",
    "tickets",
)


async def setup(bot: Nightcore):
    """Setup the configuration commands for the Nightcore bot."""
    if not any(
        isinstance(cmd, app_commands.AppCommand) and cmd.name == "config"  # type: ignore
        for cmd in bot.tree.get_commands()
    ):
        bot.tree.add_command(config_group)
