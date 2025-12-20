from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from ._groups import components as builder_group

# SIDE-EFFECT IMPORTS
from .commands import change, create, delete, preview, send

__all__ = ("change", "create", "delete", "preview", "send")


async def setup(bot: Nightcore) -> None:
    """Setup the clans commands for the Nightcore bot."""
    bot.tree.add_command(builder_group)
