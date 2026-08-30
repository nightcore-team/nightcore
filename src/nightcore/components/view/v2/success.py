"""
Success move view v2 component.

Used for displaying successful action messages.
"""

from typing import Self

from discord import Color
from discord.ui import Container, LayoutView, Separator, TextDisplay


class SuccessViewV2(LayoutView):
    def __init__(self, title: str, description: str) -> None:
        super().__init__(timeout=None)

        container = Container[Self](
            accent_color=Color.from_str("#7FD9C4"),
        )

        container.add_item(TextDisplay[Self](f"### {title}\n"))
        container.add_item(TextDisplay[Self](description))
        container.add_item(Separator[Self]())
        container.add_item(TextDisplay[Self]("-# fix by aaxnet"))

        self.add_item(container)
