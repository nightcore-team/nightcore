from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from ._groups import faq as faq_group

# SIDE-EFFECT IMPORTS
from .commands import add_page, change_page, delete_page, send

__all__ = ("add_page", "change_page", "delete_page", "send")


async def setup(bot: "Nightcore"):
    """Setup the faq commands for the Nightcore bot."""

    bot.tree.add_command(faq_group)
