"""
Roulette view v2 component.

Used for displaying the results of a casino roulette game.
"""

from typing import TYPE_CHECKING, Self

from discord import Color
from discord.ui import Container, LayoutView, Separator, TextDisplay

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore
    from src.nightcore.features.economy.utils.casino import RouletteResult


class SingleRouletteViewV2(LayoutView):
    def __init__(
        self,
        bot: "Nightcore",
        coin_name: str | None,
        result: "RouletteResult",
        new_balance: int,
    ) -> None:
        super().__init__(timeout=None)

        container = Container[Self](accent_color=Color.from_str("#5EC9B3"))

        container.add_item(
            TextDisplay[Self](
                "## <:nightcoreChip:1540462329878028349> Игра в рулетку",
            )
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
        container.add_item(TextDisplay[Self]("-# fix by aaxnet"))

        self.add_item(container)
