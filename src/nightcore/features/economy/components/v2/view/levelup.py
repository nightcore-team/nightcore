"""
Level Up View V2 Component.

Used for displaying a notification when a user levels up in the levels system.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Self

from discord import Color
from discord.ui import Container, LayoutView, Separator, TextDisplay

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.utils import discord_ts


class LevelUpViewV2(LayoutView):
    def __init__(
        self,
        bot: "Nightcore",
        user_id: int,
        new_level: int,
        exp_to_level: int,
    ) -> None:
        super().__init__(timeout=30)

        container = Container[Self](accent_color=Color.from_str("#ffffff"))

        container.add_item(TextDisplay[Self](f"### <@{user_id}>"))
        container.add_item(Separator[Self]())

        container.add_item(
            TextDisplay[Self](
                f"### Вы успешно повысили свой уровень до {new_level}!\n"
                f"> До следующего вам осталось: **`{exp_to_level}`** опыта.\n",
            )
        )

        container.add_item(
            TextDisplay[Self](
                "<:snowflakesnightcore:1450559241365491723> **Мы рады, что вы заполняете наш чат своим присутствием!**",  # noqa: E501
            )
        )
        container.add_item(Separator[Self]())

        now = datetime.now(timezone.utc)
        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {bot.user.name} in {discord_ts(now)}"  # type: ignore
            )
        )

        self.add_item(container)
