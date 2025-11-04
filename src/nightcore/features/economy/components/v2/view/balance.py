"""
Balance view v2 component.

Used for displaying a user's balance information.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Self

from discord.ui import Container, LayoutView, Separator, TextDisplay

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.utils import discord_ts


class BalanceViewV2(LayoutView):
    def __init__(
        self,
        bot: "Nightcore",
        user_id: int,
        coin_name: str | None,
        balance: float,
    ):
        super().__init__(timeout=60)

        container = Container[Self]()

        container.add_item(
            TextDisplay[Self](
                "## <:10845currency:1432050187492130836> Информация о балансе"
            )
        )
        container.add_item(Separator[Self]())

        description = (
            f"> **Пользователь:** <@{user_id}>\n> **Баланс:** {balance}"
        )
        if coin_name:
            description += f" {coin_name}"

        container.add_item(TextDisplay[Self](description))
        container.add_item(Separator[Self]())

        now = datetime.now(timezone.utc)
        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {bot.user.name} in {discord_ts(now)}"  # type: ignore
            )
        )

        self.add_item(container)
