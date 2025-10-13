from discord import app_commands

from src.nightcore.bot import Nightcore

from . import create, delete, edit, send

# SIDE-EFFECT IMPORTS
from ._groups import rules as rules_group

__all__ = ("create", "delete", "edit", "send")


async def setup(bot: Nightcore):
    """Setup the rules commands for the Nightcore bot."""
    if not any(
        isinstance(cmd, app_commands.AppCommand) and cmd.name == "rules"  # type: ignore
        for cmd in bot.tree.get_commands()
    ):
        bot.tree.add_command(rules_group)
