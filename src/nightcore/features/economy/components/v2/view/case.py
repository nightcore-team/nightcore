"""
V2 views components related to cases.

Used for displaying case opening results and help information about cases.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Self

from discord import Color
from discord.ui import Container, LayoutView, Separator, TextDisplay

from src.infra.db.models.case import Case
from src.nightcore.utils import discord_ts

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


class CaseOpenViewV2(LayoutView):
    def __init__(
        self, bot: "Nightcore", case_name: str, reward: str | int, chance: int
    ):
        super().__init__()

        self.bot = bot
        self.case_name = case_name
        self.reward = reward
        self.chance = chance

        container = Container[Self](accent_color=Color.from_str("#1441ac"))

        container.add_item(
            TextDisplay[Self](
                "## <a:68842universebox:1442920870996742275> Открытие кейса"
            )
        )
        container.add_item(Separator[Self]())

        container.add_item(
            TextDisplay[Self](
                f"Вы успешно открыли **{self.case_name}**\n"
                f"> **Ваш приз:** {self.reward}\n"
                f"> **Шанс выпадения:** **`{self.chance}%`**"
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


class CaseHelpViewV2(LayoutView):
    def __init__(
        self, bot: "Nightcore", coin_name: str | None, cases: list[Case]
    ):
        super().__init__()

        container = Container[Self](accent_color=Color.from_str("#1441ac"))

        container.add_item(
            TextDisplay[Self](
                "## <a:68842universebox:1442920870996742275> Информация о кейсах"  # noqa: E501
            )
        )
        container.add_item(Separator[Self]())
        container.add_item(
            TextDisplay[Self](
                "**Доступные виды кейсов: кейс с коинами, кейс с цветами.**\n"
                "> Чтобы открыть кейс, используйте команду **`/case open`**"
            )
        )
        container.add_item(Separator[Self]())

        container.add_item(
            TextDisplay[Self]("### Кейс с коинами"),
        )
        if not coins_drops:
            container.add_item(
                TextDisplay[Self](
                    "> В данный момент кейс с монетами не настроен."
                )
            )
        else:
            container.add_item(
                TextDisplay[Self](
                    "\n".join(
                        f"> {drop['amount']} {coin_name or 'коинов'} "
                        f"- шанс **`{drop['chance']}%`**"
                        for drop in coins_drops
                    )
                ),
            )

        container.add_item(Separator[Self]())
        container.add_item(TextDisplay[Self]("### Кейс с цветами"))
        if not colors_drops:
            container.add_item(
                TextDisplay[Self](
                    "> В данный момент кейс с цветами не настроен."
                )
            )
        else:
            container.add_item(
                TextDisplay[Self](
                    "\n".join(
                        f"> цвет: **<@&{drop['role_id']}>** "
                        f"- шанс **`{drop['chance']}%`**"
                        for drop in colors_drops.values()
                    )
                ),
            )

        container.add_item(Separator[Self]())

        now = datetime.now(UTC)
        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {bot.user.name} in {discord_ts(now)}"  # type: ignore
            )
        )

        self.add_item(container)
