"""
Roulette view v2 component.

Used for displaying the results of a casino roulette game.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Self

from discord import ButtonStyle, Color
from discord.ui import (
    ActionRow,
    Button,
    Container,
    LayoutView,
    Separator,
    TextDisplay,
)

from src.nightcore.utils import discord_ts

if TYPE_CHECKING:
    from src.infra.db.models._annot import CasinoBetAnnot
    from src.nightcore.bot import Nightcore

from src.infra.db.models._enums import (
    CasinoBetResultTypeEnum,
    CasinoGameStateEnum,
)
from src.nightcore.features.economy.utils.casino import COLORS


class MultiplayerRouletteViewV2(LayoutView):
    def __init__(
        self,
        bot: "Nightcore",
        coin_name: str | None,
        initiator_id: int,
        initiator_bet: int,
        initiator_selected_color: str,
        state: CasinoGameStateEnum,
        initiator_result: CasinoBetResultTypeEnum | None = None,
        bets: list["CasinoBetAnnot"] | None = None,
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
                f"> **Его ставка:** {initiator_bet} {coin_name_display} | {COLORS[initiator_selected_color]}\n"  # noqa: E501
                f"> **Результат:** {initiator_result.value if initiator_result else 'Ожидание...'}\n"  # noqa: E501
            )
        )
        container.add_item(Separator[Self]())

        if bets:
            container.add_item(
                TextDisplay[Self](
                    "### Список остальных участников:\n"
                    "-# пользователь - ставка - цвет - результат\n"
                    + "\n".join(
                        f"> <@{bet['user_id']}> - {bet['bet']} - {COLORS[bet['selected_color']]} - {bet['result_type'].value if bet['result_type'] else 'Ожидание...'}"  # noqa: E501
                        for bet in bets
                    )
                )
            )

        if state == CasinoGameStateEnum.PENDING:
            container.add_item(
                TextDisplay[Self](
                    "\nОжидается начало игры... <:sandclock:1442914884147871874>\n"  # noqa: E501
                    "Другие пользователи могут присоединиться в течение 60 секунд"  # noqa: E501
                )
            )
        else:
            container.add_item(TextDisplay[Self]("\nИгра завершена.\n"))

        container.add_item(Separator[Self]())

        container.add_item(
            ActionRow[Self](
                Button[Self](
                    style=ButtonStyle.grey,
                    label="Присоединиться к игре",
                    custom_id="casino:roulette:multiplayer",
                    emoji=None,
                )
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
