from discord import app_commands

from src.nightcore.bot import Nightcore

# SIDE-EFFECT IMPORTS
from . import (
    logging,  # noqa: F401
    moderation,  # noqa: F401
    moderstats,  # noqa: F401
    private_channels,  # noqa: F401
)
from ._groups import config as config_group


async def setup(bot: Nightcore):
    """Setup the configuration commands for the Nightcore bot."""
    if not any(
        isinstance(cmd, app_commands.AppCommand) and cmd.name == "config"  # type: ignore
        for cmd in bot.tree.get_commands()
    ):
        bot.tree.add_command(config_group)
