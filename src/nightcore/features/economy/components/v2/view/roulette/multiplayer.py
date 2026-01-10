"""
Roulette view v2 component.

Used for displaying the results of a casino roulette game.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Self

from discord import Color
from discord.ui import Container, LayoutView, Separator, TextDisplay

from src.nightcore.utils import discord_ts

if TYPE_CHECKING:
    from src.infra.db.models._annot import CasinoBetAnnot
    from src.nightcore.bot import Nightcore

from src.nightcore.features.economy.utils.casino import COLORS


class MultiplayerRouletteViewV2(LayoutView):
    def __init__(
        self,
        bot: "Nightcore",
        coin_name: str | None,
        initiator_id: int,
        bet_count: int,
        selected_color: str,
        participants: list["CasinoBetAnnot"] | None = None,
    ) -> None:
        super().__init__(timeout=None)

        container = Container[Self](accent_color=Color.from_str("#ffffff"))

        container.add_item(
            TextDisplay[Self](
                "## <:Casino_Chip:1403530383013842994> Рулетка",
            )
        )
        container.add_item(Separator[Self]())

        coin_name_display = coin_name if coin_name else "коинов"
        container.add_item(
            TextDisplay[Self](
                f"### Пользователь <@{initiator_id}> запустил игру\n"
                f"> **Его ставка:** {bet_count} {coin_name_display} | {COLORS[selected_color]}\n"  # noqa: E501
            )
        )
        container.add_item(Separator[Self]())

        if participants:
            container.add_item(
                TextDisplay[Self](
                    "### Список остальных участников:\n"
                    "-# пользователь - ставка - цвет"
                    + "\n".join(
                        f"> <@{user['user_id']}> - {user['bet']} - {COLORS[user['selected_color']]}"  # noqa: E501
                        for user in participants
                    )
                )
            )

        container.add_item(
            TextDisplay[Self](
                "\nОжидается начало игры... <:sandclock:1442914884147871874>\n"
                "Другие пользователи могут присоединиться в течение 60 секунд"
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
