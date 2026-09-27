"""
Level Up View V2 Component.

Used for displaying a notification when a user levels up in the levels system.
"""

from typing import TYPE_CHECKING, Self

from discord import Color
from discord.ui import Container, LayoutView, TextDisplay

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


class LevelUpViewV2(LayoutView):
    def __init__(
        self,
        bot: "Nightcore",
        user_id: int,
        new_level: int,
        exp_to_level: int,
    ) -> None:
        super().__init__(timeout=30)

        container = Container[Self](accent_color=Color.from_str("#5EC9B3"))

        container.add_item(TextDisplay[Self]("### Повышение уровня\n"))

        container.add_item(
            TextDisplay[Self](
                f"<@{user_id}> повысил свой уровень до {new_level}!\n"
                f"> До получения следующего осталось: **`{exp_to_level}`** опыта.\n",  # noqa: E501
            )
        )

        self.add_item(container)
