"""V2 help view for badges.

Used for displaying paginated information about badges.
"""

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

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


class BadgeHelpPaginationActionRow(ActionRow["BadgeHelpViewV2"]):
    def __init__(self):
        super().__init__()

    @button(
        style=ButtonStyle.secondary,
        emoji="<:nightcoreArrowLeftCyan:1540434220436951172>",
        custom_id="badge:help:prev",
    )
    async def previous(
        self, interaction: Interaction, button: Button["BadgeHelpViewV2"]
    ):
        """Go to the previous page."""
        view = cast(BadgeHelpViewV2, self.view)

        if view.current_page > 0:
            view.current_page -= 1
        await interaction.response.edit_message(
            view=view.make_component(),
        )

    @button(
        style=ButtonStyle.secondary,
        emoji="<:nightcoreArrowRightCyan:1540434390780477551>",
        custom_id="badge:help:next",
    )
    async def next(
        self, interaction: Interaction, button: Button["BadgeHelpViewV2"]
    ):
        """Go to the next page."""
        view = cast(BadgeHelpViewV2, self.view)
        if view.current_page < len(view.pages) - 1:
            view.current_page += 1
        await interaction.response.edit_message(
            view=view.make_component(),
        )


class BadgeHelpViewV2(LayoutView):
    def __init__(self, bot: "Nightcore", pages: list[list[TextDisplay[Any]]]):
        super().__init__(timeout=None)

        self.pages = pages
        self.current_page = 0
        self.bot = bot

        self.pagination: BadgeHelpPaginationActionRow | None = None

        self.make_component()

    def _update_buttons(self):
        """Update button states based on current page."""
        if not self.pagination:
            return
        for child in self.pagination.children:
            if isinstance(child, Button):
                if child.custom_id == "badge:help:prev":
                    child.disabled = self.current_page == 0
                elif child.custom_id == "badge:help:next":
                    child.disabled = self.current_page == len(self.pages) - 1

    def make_component(self) -> Self:
        """Create a new component for the current page."""

        self.clear_items()

        container = Container[Self](accent_color=Color.from_str("#5EC9B3"))

        container.add_item(
            TextDisplay(
                "## <:nightcoreBadge:1556219069537984542> Информация о значках"
            )
        )
        container.add_item(Separator())

        if len(self.pages) > 1:
            for item in self.pages[self.current_page]:
                container.add_item(item)

            container.add_item(Separator[Self]())

            self.pagination = BadgeHelpPaginationActionRow()
            container.add_item(self.pagination)
        else:
            for item in self.pages[0]:
                container.add_item(item)

        if len(self.pages) > 1:
            container.add_item(Separator())
            container.add_item(
                TextDisplay[Self](
                    f"-# Page {self.current_page + 1} of {len(self.pages)}"
                )
            )

        self._update_buttons()

        self.add_item(container)

        return self
