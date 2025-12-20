"""
Award notification view v2 component.

Used for displaying a notification when an item is awarded to a user.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Self

from discord import Color
from discord.ui import Container, LayoutView, Separator, TextDisplay

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.utils import discord_ts


class AwardNotificationViewV2(LayoutView):
    def __init__(
        self,
        bot: "Nightcore",
        user_id: int,
        item_name: str,
        amount: int,
        reason: str | None = None,
    ):
        super().__init__(timeout=None)

        container = Container[Self](accent_color=Color.from_str("#ffffff"))

        container.add_item(
            TextDisplay[Self](
                "## <:snowflakesnightcore:1450559241365491723> Уведомление о выдаче предмета"  # noqa: E501
            )
        )
        container.add_item(Separator[Self]())

        container.add_item(
            TextDisplay[Self](
                f"<@{user_id}> вам выдал(а) предмет.\n> Причина: {reason or 'Не указана'}"  # noqa: E501
            )
        )
        container.add_item(Separator[Self]())

        container.add_item(TextDisplay[Self]("### Информация о предмете: "))
        container.add_item(
            TextDisplay[Self](
                f"> Название: **{item_name}**\n> Количество: **{amount}**"
            )
        )
        container.add_item(Separator[Self]())

        now = datetime.now(UTC)
        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {bot.user.name} in {discord_ts(now)}"  # type: ignore
            )
        )

        self.add_item(container)
