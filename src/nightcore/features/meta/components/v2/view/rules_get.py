"""Rules get view v2 component."""

from typing import TYPE_CHECKING, Self

from discord import Color
from discord.ui import (
    Container,
    LayoutView,
    Separator,
    TextDisplay,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


class RulesGetViewV2(LayoutView):
    def __init__(self, *, bot: "Nightcore", clause: str) -> None:
        super().__init__(timeout=None)

        container = Container[Self](accent_color=Color.from_str("#C0577A"))

        container.add_item(TextDisplay[Self]("## Полученный пункт"))
        container.add_item(Separator[Self]())

        container.add_item(TextDisplay[Self](f"```{clause}```"))

        container.add_item(
            TextDisplay[Self](
                "-# Eсли введенный пункт отсутствует, вы увидите свой ввод"
            )
        )

        self.add_item(container)
