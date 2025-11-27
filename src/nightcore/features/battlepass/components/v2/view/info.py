"""
Battlepass info view v2 component.

Used for displaying a general battlepass information with pagination.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Self, cast

from discord import ButtonStyle, Color
from discord.interactions import Interaction
from discord.ui import (
    ActionRow,
    Button,
    Container,
    Item,
    LayoutView,
    Separator,
    TextDisplay,
    button,
)

from src.nightcore.utils import discord_ts

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


class PaginationButtons(ActionRow["BattlepassInfoViewV2"]):
    def __init__(self):
        super().__init__()

    @button(
        style=ButtonStyle.secondary,
        emoji="<:41036arrowforwardios1:1442925401696632934>",
        custom_id="battlepass:info_prev",
    )
    async def previous(
        self, interaction: Interaction, button: Button["BattlepassInfoViewV2"]
    ):
        """Go to the previous page."""
        await interaction.response.defer()

        view = cast(BattlepassInfoViewV2, self.view)

        if view.current_page > 0:  # type: ignore
            view.current_page -= 1  # type: ignore
        await interaction.followup.edit_message(
            interaction.message.id,  # type: ignore
            view=view.make_component(),
        )

    @button(
        style=ButtonStyle.secondary,
        emoji="<:41036arrowforwardios:1442924853085864178>",
        custom_id="battlepass:info_next",
    )
    async def next(
        self, interaction: Interaction, button: Button["BattlepassInfoViewV2"]
    ):
        """Go to the next page."""
        await interaction.response.defer()

        view = cast(BattlepassInfoViewV2, self.view)

        if view.current_page < len(view.pages) - 1:  # type: ignore
            view.current_page += 1  # type: ignore
        await interaction.followup.edit_message(
            interaction.message.id,  # type: ignore
            view=view.make_component(),
        )


class BattlepassInfoViewV2(LayoutView):
    def __init__(
        self,
        bot: "Nightcore",
        user_level: int,
        total_bp_levels: int,
        total_bp_points: int,
        pages: list[str],
    ) -> None:
        super().__init__(timeout=None)

        self.pages = pages
        self.current_page = 0
        self.user_level = user_level
        self.total_bp_levels = total_bp_levels
        self.total_bp_points = total_bp_points
        self.bot = bot

        self.pagination: PaginationButtons | None = None

        self.make_component()

    def _update_buttons(self):
        """Update button states based on current page."""
        if not self.pagination:
            return
        for child in self.pagination.children:
            if isinstance(child, Button):
                if child.custom_id == "battlepass:info_prev":
                    child.disabled = self.current_page == 0  # type: ignore
                elif child.custom_id == "battlepass:info_next":
                    child.disabled = self.current_page == len(self.pages) - 1  # type: ignore

    def make_component(self):
        """Create the view components."""
        self.clear_items()

        container = Container[Self](accent_color=Color.from_str("#b777a6"))

        container.add_item(
            TextDisplay[Self](
                "## <:9057saturn:1442919302587093072> Battlepass Information"
            )
        )
        container.add_item(Separator[Self]())

        container.add_item(
            TextDisplay[Self](
                f"**Общее количество уровней: {self.total_bp_levels}**\n"
                f"**Необходимо BP points для полного прохождения: {self.total_bp_points}**\n"  # noqa: E501
                "> Для повышения уровня активно общайтесь на нашем сервере <:heartt:1442919985004544011>"  # noqa: E501
            )
        )
        container.add_item(Separator[Self]())
        container.add_item(
            TextDisplay[Self]("-# Уровень - Требуемые BP points - Награда\n")
        )

        container.add_item(TextDisplay[Self](self.pages[self.current_page]))
        container.add_item(Separator[Self]())

        if len(self.pages) > 1:
            self.pagination = PaginationButtons()
            container.add_item(self.pagination)
            container.add_item(Separator[Self]())
        else:
            self.pagination = None

        now = datetime.now(timezone.utc)

        container.add_item(
            TextDisplay[Self](
                f"-# Page {self.current_page + 1} of {len(self.pages)}\n"
                f"-# Powered by {self.bot.user.name} in {discord_ts(now)}"  # type: ignore
            )
        )

        # Update buttons after adding items
        self._update_buttons()

        self.add_item(container)

        return self

    async def on_timeout(self):
        """Disable all buttons when the view times out."""

        def walk(item: Item[Self]):  # type: ignore
            if hasattr(item, "children"):
                for c in item.children:  # type: ignore
                    yield from walk(c)  # type: ignore
            yield item

        for comp in walk(self):  # type: ignore
            if isinstance(comp, Button):
                comp.disabled = True
