"""Get config info view v2 component."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Self, cast

from discord import ButtonStyle, Color
from discord.interactions import Interaction
from discord.ui import (
    ActionRow,
    Button,
    Container,
    LayoutView,
    Separator,
    TextDisplay,
    button,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.utils import discord_ts


class ConfigInfoPaginationButtons(ActionRow["ConfigInfoViewV2"]):
    def __init__(self):
        super().__init__()

    async def interaction_check(self, interaction: Interaction) -> bool:
        """Ensure only the author can interact."""
        if interaction.user.id != self.view.author_id:  # type: ignore
            await interaction.response.send_message(
                "Вы не можете управлять этой пагинацией.", ephemeral=True
            )
            return False
        return True

    @button(
        style=ButtonStyle.secondary,
        emoji="<:41036arrowforwardios1:1442925401696632934>",
        custom_id="config_info:prev",
    )
    async def previous(
        self,
        interaction: Interaction,
        button: Button[ConfigInfoViewV2],
    ):
        """Go to the previous page."""
        view = cast(ConfigInfoViewV2, self.view)
        if view.current_page > 0:
            view.current_page -= 1
        await interaction.response.edit_message(
            view=view.make_component(),
        )

    @button(
        style=ButtonStyle.secondary,
        emoji="<:41036arrowforwardios:1442924853085864178>",
        custom_id="config_info:next",
    )
    async def next(
        self,
        interaction: Interaction,
        button: Button[ConfigInfoViewV2],
    ):
        """Go to the next page."""
        view = cast(ConfigInfoViewV2, self.view)
        if view.current_page < len(view.pages) - 1:
            view.current_page += 1
        await interaction.response.edit_message(
            view=view.make_component(),
        )


class ConfigInfoViewV2(LayoutView):
    def __init__(
        self, bot: Nightcore, config_name: str, pages: list[str]
    ) -> None:
        super().__init__(timeout=None)
        self.bot = bot
        self.config_name = config_name
        self.pages = pages
        self.current_page = 0

        self.pagination: ConfigInfoPaginationButtons | None = None

    def _update_buttons(self):
        """Update button states based on current page."""
        if not self.pagination:
            return

        for child in self.pagination.children:
            if isinstance(child, Button):
                if child.custom_id == "config_info:prev":
                    child.disabled = self.current_page == 0  # type: ignore
                elif child.custom_id == "config_info:next":
                    child.disabled = self.current_page == len(self.pages) - 1  # type: ignore

    def make_component(self) -> Self:
        """Create the layout view component."""

        self.clear_items()

        container = Container[Self](accent_color=Color.from_str("#515cff"))

        container.add_item(
            TextDisplay[Self](f"## Конфигурация: {self.config_name.lower()}\n")
        )
        container.add_item(Separator[Self]())

        container.add_item(TextDisplay[Self](self.pages[self.current_page]))
        container.add_item(Separator[Self]())

        if len(self.pages) > 1:
            self.pagination = ConfigInfoPaginationButtons()
            container.add_item(self.pagination)
            container.add_item(Separator[Self]())
        else:
            self.pagination = None

        now = datetime.now(timezone.utc)

        container.add_item(
            TextDisplay[Self](
                f"-# Page {self.current_page + 1} of {len(self.pages)}\n"
                f"-# Powered by {self.bot.user.name} at {discord_ts(now)}"  # type: ignore
            )
        )

        self.add_item(container)
        self._update_buttons()

        return self
