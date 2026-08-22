"""
Unexpected error view v2 component.

Used for displaying unexpected error messages.
"""

from typing import Self

from discord import Color
from discord.ui import Container, LayoutView, TextDisplay


class UnexpectedErrorViewV2(LayoutView):
    def __init__(self, title: str, description: str) -> None:
        super().__init__(timeout=None)

        container = Container[Self](
            accent_color=Color.from_str("#E05263"),
        )

        container.add_item(TextDisplay[Self](f"### {title}\n"))
        container.add_item(TextDisplay[Self](description))

        self.add_item(container)
