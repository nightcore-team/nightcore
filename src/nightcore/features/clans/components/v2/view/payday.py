"""Clans Payday View V2 Component."""

from typing import TYPE_CHECKING, Self

from discord import Color
from discord.ui import Container, LayoutView, Separator, TextDisplay

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


class ClansPaydayViewV2(LayoutView):
    def __init__(self, bot: "Nightcore") -> None:
        super().__init__(timeout=None)

        container = Container[Self](accent_color=Color.from_str("#9B7EDE"))

        container.add_item(
            TextDisplay[Self](
                "## <:nightcoreCrownPurple:1540714328209100923> PayDay"
            )
        )
        container.add_item(Separator[Self]())

        container.add_item(
            TextDisplay[Self](
                "Всем кланам были выданы очки репутации в зависимости от количества участников и множителя PayDay."  # noqa: E501
            )
        )
        self.add_item(container)
