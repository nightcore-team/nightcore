from typing import TYPE_CHECKING

from discord import app_commands

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from ._groups import clan as clan_main_group

# SIDE-EFFECT IMPORTS
from .commands import info, leave, seq, top
from .commands.manage import (
    change_deputy,
    create,
    delete,
    improvements,
    invite,
    kick,
    settings,
    shop,
)

__all__ = (
    "change_deputy",
    "create",
    "delete",
    "improvements",
    "info",
    "invite",
    "kick",
    "leave",
    "seq",
    "settings",
    "shop",
    "top",
)


async def setup(bot: "Nightcore") -> None:
    """Setup the clans commands for the Nightcore bot."""
    bot.tree.add_command(clan_main_group)
