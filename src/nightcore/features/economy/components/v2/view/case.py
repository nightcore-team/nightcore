"""
V2 views components related to cases.

Used for displaying case opening results and help information about cases.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Self, cast

from discord import ButtonStyle, Color, Interaction
from discord.ui import (
    ActionRow,
    Button,
    Container,
    LayoutView,
    Separator,
    TextDisplay,
    button,
)

from src.nightcore.utils import discord_ts

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


class CaseOpenViewV2(LayoutView):
    def __init__(
        self, bot: "Nightcore", case_name: str, reward: str, amount:int, chance: int
    ):
        super().__init__()

        self.bot = bot
        self.case_name = case_name
        self.reward = reward
        self.amount = amount
        self.chance = chance

        container = Container[Self](accent_color=Color.from_str("#1441ac"))

        container.add_item(
            TextDisplay(
                "## <a:68842universebox:1442920870996742275> Открытие кейса"
            )
        )
        container.add_item(Separator())

        container.add_item(
            TextDisplay(
                f"Вы успешно открыли **{self.case_name}**\n"
                f"> **Ваш приз:**{self.amount} {self.reward}\n"
                f"> **Шанс выпадения:** **`{self.chance}%`**"
            )
        )
        container.add_item(Separator())

        now = datetime.now(UTC)
        container.add_item(
            TextDisplay(
                f"-# Powered by {bot.user.name} in {discord_ts(now)}"  # type: ignore
            )
        )

        self.add_item(container)


class CaseHelpPaginationActionRow(ActionRow["CaseHelpViewV2"]):
    def __init__(self):
        super().__init__()

        """Handle case help pagination button callback."""

    @button(
        style=ButtonStyle.secondary,
        emoji="<:41036arrowforwardios1:1442925401696632934>",
        custom_id="case:help:prev",
    )
    async def previous(
        self, interaction: Interaction, button: Button["CaseHelpViewV2"]
    ):
        """Go to the previous page."""
        view = cast(CaseHelpViewV2, self.view)

        if view.current_page > 0:
            view.current_page -= 1
        await interaction.response.edit_message(
            view=view.make_component(),
        )

    @button(
        style=ButtonStyle.secondary,
        emoji="<:41036arrowforwardios:1442924853085864178>",
        custom_id="case:help:next",
    )
    async def next(
        self, interaction: Interaction, button: Button["CaseHelpViewV2"]
    ):
        """Go to the next page."""
        view = cast(CaseHelpViewV2, self.view)
        if view.current_page < len(view.pages) - 1:  # type: ignore
            view.current_page += 1  # type: ignore
        await interaction.response.edit_message(
            view=view.make_component(),  # type: ignore
        )


class CaseHelpViewV2(LayoutView):
    def __init__(self, bot: "Nightcore", pages: list[list[TextDisplay[Any]]]):
        super().__init__(timeout=None)

        self.pages = pages
        self.current_page = 0
        self.bot = bot

        self.pagination: CaseHelpPaginationActionRow | None = None

        self.make_component()

    def _update_buttons(self):
        """Update button states based on current page."""
        if not self.pagination:
            return
        for child in self.pagination.children:
            if isinstance(child, Button):
                if child.custom_id == "case:help:prev":
                    child.disabled = self.current_page == 0  # type: ignore
                elif child.custom_id == "case:help:next":
                    child.disabled = self.current_page == len(self.pages) - 1  # type: ignore

    def make_component(self) -> Self:
        """Create a new component for the current page."""

        self.clear_items()

        container = Container[Self](accent_color=Color.from_str("#1441ac"))

        container.add_item(
            TextDisplay(
                "## <a:68842universebox:1442920870996742275> Информация о кейсах"  # noqa: E501
            )
        )
        container.add_item(Separator())
        container.add_item(
            TextDisplay(
                "**Доступные виды кейсов.**\n"
                "> Чтобы открыть кейс, используйте команду **`/case open`**"
            )
        )
        container.add_item(Separator())

        if len(self.pages) > 1:
            for item in self.pages[self.current_page]:
                container.add_item(item)

            container.add_item(Separator[Self]())

            self.pagination = CaseHelpPaginationActionRow()
            container.add_item(self.pagination)
        else:
            for item in self.pages[0]:
                container.add_item(item)

        container.add_item(Separator())

        now = datetime.now(UTC)

        container.add_item(
            TextDisplay[Self](
                f"-# Page {self.current_page + 1} of {len(self.pages)}\n"
                f"-# Powered by {self.bot.user.name} in {discord_ts(now)}"  # type: ignore
            )
        )

        self._update_buttons()

        self.add_item(container)

        return self
