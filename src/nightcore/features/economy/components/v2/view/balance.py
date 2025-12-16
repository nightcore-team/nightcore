"""
Balance view v2 component.

Used for displaying a user's balance information.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Self

from discord import Color
from discord.ui import (
    Container,
    LayoutView,
    Separator,
    TextDisplay,
)

from .transfer import TransferHistoryActionRow

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.utils import discord_ts


class BalanceViewV2(LayoutView):
    def __init__(
        self,
        bot: "Nightcore",
        guild_id: int,
        user_id: int,
        coin_name: str | None,
        balance: float,
    ):
        super().__init__(timeout=None)

        container = Container[Self](accent_color=Color.from_str("#ffffff"))

        container.add_item(
            TextDisplay[Self](
                "## <:icedwalletnightcore:1450561560660410630> Информация о балансе\n\n"  # noqa: E501
            )
        )

        container.add_item(
            TextDisplay[Self](
                f"\n**Пользователь:** <@{user_id}>\n"
                f"**Баланс:** {balance} {coin_name or 'коинов'}"
            ),
        )
        container.add_item(Separator[Self]())

        container.add_item(TransferHistoryActionRow(guild_id, user_id))
        container.add_item(Separator[Self]())

        now = datetime.now(timezone.utc)
        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {bot.user.name} in {discord_ts(now)}"  # type: ignore
            )
        )

        self.add_item(container)
