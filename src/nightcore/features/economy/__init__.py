from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from ._groups import case as case_group
from ._groups import give as give_group

# SIDE-EFFECT IMPORTS
from .commands.case import help, open
from .commands.give import case, clanexp, clanrep, coins, color, exp

__all__ = (
    "case",
    "clanexp",
    "clanrep",
    "coins",
    "color",
    "exp",
    "help",
    "open",
)


async def setup(bot: "Nightcore"):
    """Setup the economy commands for the Nightcore bot."""

    bot.tree.add_command(case_group)
    bot.tree.add_command(give_group)
