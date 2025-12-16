"""Get single moderator stats view v2 component."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Self, cast

from discord import ButtonStyle, Color, Interaction
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

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore
    from src.nightcore.features.moderation.utils.getmoderstats import (
        ModerationScores,
    )
    from src.nightcore.features.moderation.utils.getmoderstats._types import (
        ModeratorStats,
    )
from src.nightcore.features.moderation.utils.getmoderstats.pages import (
    format_moderstats_page_components,
)
from src.nightcore.utils import discord_ts


class GetModerStatsPaginationButtons(ActionRow["MultiplyGetModerStatsViewV2"]):
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
        custom_id="getmoderstats:prev",
    )
    async def previous(
        self,
        interaction: Interaction,
        button: Button[MultiplyGetModerStatsViewV2],
    ):
        """Go to the previous page."""
        view = cast(MultiplyGetModerStatsViewV2, self.view)
        if view.current_page > 0:
            view.current_page -= 1
        await interaction.response.edit_message(
            view=view.make_component(),
        )

    @button(
        style=ButtonStyle.secondary,
        emoji="<:41036arrowforwardios:1442924853085864178>",
        custom_id="getmoderstats:next",
    )
    async def next(
        self,
        interaction: Interaction,
        button: Button[MultiplyGetModerStatsViewV2],
    ):
        """Go to the next page."""
        view = cast(MultiplyGetModerStatsViewV2, self.view)
        if view.current_page < len(view.pages) - 1:
            view.current_page += 1
        await interaction.response.edit_message(
            view=view.make_component(),
        )


class MultiplyGetModerStatsViewV2(LayoutView):
    def __init__(
        self,
        bot: Nightcore,
        author_id: int,
        pages: list[list[tuple[int, ModeratorStats, float]]],
        scores: ModerationScores,
        from_dt: datetime,
        to_dt: datetime,
    ):
        super().__init__(timeout=None)
        self.author_id = author_id
        self.bot = bot
        self.pages = pages
        self.scores = scores
        self.from_dt = from_dt
        self.to_dt = to_dt
        self.current_page = 0

        self.pagination: GetModerStatsPaginationButtons | None = None
        self.header_text: TextDisplay[Self] | None = None
        self.main_text: TextDisplay[Self] | None = None
        self.footer_text: TextDisplay[Self] | None = None

        self.make_component()

    def _update_buttons(self):
        """Update button states based on current page."""
        if not self.pagination:
            return

        for child in self.pagination.children:
            if isinstance(child, Button):
                if child.custom_id == "getmoderstats:prev":
                    child.disabled = self.current_page == 0  # type: ignore
                elif child.custom_id == "getmoderstats:next":
                    child.disabled = self.current_page == len(self.pages) - 1  # type: ignore

    def make_component(self) -> Self:
        """Create the layout view component."""

        self.clear_items()

        container = Container[Self](accent_color=Color.from_str("#d5d5f9"))

        container.add_item(
            TextDisplay[Self](
                f"## <:nightcoremoderation:1450443148009406557> Статистика модерации\n\n"  # noqa: E501
                f"**Период:** {discord_ts(self.from_dt)} - {discord_ts(self.to_dt)}\n"  # noqa: E501
                f"> **Всего модераторов:** {sum(len(page) for page in self.pages)}"  # noqa: E501
            )
        )
        container.add_item(Separator[Self]())

        moderator_components = format_moderstats_page_components(
            self.pages[self.current_page],
            self.current_page + 1,
        )

        for component in moderator_components:
            container.add_item(component)

        if len(self.pages) > 1:
            container.add_item(Separator[Self]())

        if len(self.pages) > 1:
            self.pagination = GetModerStatsPaginationButtons()
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

    async def on_timeout(self):
        """Disable all buttons when the view times out."""

        def walk(item: Item[Self]):  # type: ignore
            if hasattr(item, "children"):
                for c in item.children:  # type: ignore
                    yield from walk(cast(Item[Self], c))
            yield item

        for comp in walk(self):  # type: ignore
            if isinstance(comp, Button):
                comp.disabled = True
