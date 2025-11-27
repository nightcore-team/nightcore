"""
Roulette view v2 component.

Used for displaying the results of a casino roulette game.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Self

from discord import Color
from discord.ui import Container, LayoutView, Separator, TextDisplay

from src.nightcore.utils import discord_ts

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore
    from src.nightcore.features.economy.utils.casino import RouletteResult


class RouletteViewV2(LayoutView):
    def __init__(
        self,
        bot: "Nightcore",
        coin_name: str | None,
        last_roulette_games: list[str],
        result: "RouletteResult",
        new_balance: int,
    ) -> None:
        super().__init__(timeout=None)

        container = Container[Self](accent_color=Color.from_str("#ffffff"))

        container.add_item(
            TextDisplay[Self](
                "## <:Casino_Chip:1403530383013842994> Рулетка",
            )
        )
        container.add_item(Separator[Self]())

        last_roulette_games_colors: list[str] = []
        for color in last_roulette_games:
            if color == "red":
                last_roulette_games_colors.append("🔴")
            elif color == "black":
                last_roulette_games_colors.append("⚫")
            elif color == "green":
                last_roulette_games_colors.append("🟢")

        container.add_item(
            TextDisplay[Self]("### Последние 10 игр на сервере:")
        )
        container.add_item(
            TextDisplay[Self](" ".join(last_roulette_games_colors[::-1]))
        )
        container.add_item(Separator[Self]())

        coin_name_display = coin_name if coin_name else "коинов"

        container.add_item(
            TextDisplay[Self](
                "### Результаты вашей игры: \n"
                f"> **Ваша ставка:** {result.bet} {coin_name_display} | {result.selected_color_emoji}\n"  # noqa: E501
                f"> **Выпало:** {result.number} {result.color_emoji}\n"
                f"> **Вы {'выиграли' if result.is_win else 'проиграли'}** {result.coins_change} {coin_name_display}\n\n"  # noqa: E501
                f"Ваш новый баланс: **{new_balance} {coin_name_display}**\n"
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
