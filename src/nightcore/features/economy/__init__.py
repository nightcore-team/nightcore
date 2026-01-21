from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from ._groups import case as case_group
from ._groups import casino as casino_group
from ._groups import color as color_group
from ._groups import give as give_group
from ._groups import remove as remove_group
from ._groups import temp as temp_group

# SIDE-EFFECT IMPORTS
from .commands.case import help, open
from .commands.casino import roulette
from .commands.give import bp_exp, case, clanexp, clanrep, coins, color, exp
from .commands.remove import color as remove_color
from .commands.temp import multiplier, role

__all__ = (
    "bp_exp",
    "case",
    "clanexp",
    "clanrep",
    "coins",
    "color",
    "exp",
    "help",
    "multiplier",
    "open",
    "remove_color",
    "role",
    "roulette",
)


async def setup(bot: "Nightcore"):
    """Setup the economy commands for the Nightcore bot."""

    bot.tree.add_command(case_group)
    bot.tree.add_command(color_group)
    bot.tree.add_command(give_group)
    bot.tree.add_command(casino_group)
    bot.tree.add_command(temp_group)
    bot.tree.add_command(remove_group)
