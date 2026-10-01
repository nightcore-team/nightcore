"""
Level Up View V2 Component.

Used for displaying a notification when a user levels up in the levels system.
"""

from typing import Self

from discord import Color
from discord.ui import Container, LayoutView, TextDisplay


class LevelUpViewV2(LayoutView):
    def __init__(
        self,
        user_id: int,
        new_level: int,
        exp_to_level: int,
        coins_per_level_up: int,
    ) -> None:
        super().__init__(timeout=30)

        container = Container[Self](accent_color=Color.from_str("#5EC9B3"))

        container.add_item(TextDisplay[Self]("### Повышение уровня\n"))

        coins_text = (
            f"\n> Вы получили дополнительных {coins_per_level_up} "
            f"коинов за повышение уровня."
            if coins_per_level_up > 0
            else ""
        )

        container.add_item(
            TextDisplay[Self](
                f"<@{user_id}> повысил свой уровень до {new_level}!\n"
                f"> До получения следующего осталось: **`{exp_to_level}`** опыта."  # noqa: E501
                f"{coins_text}"
            )
        )

        self.add_item(container)
