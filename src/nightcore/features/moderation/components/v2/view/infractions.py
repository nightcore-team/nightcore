"""View for paginating infractions."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Self, cast

from discord import ButtonStyle, Color, User
from discord.interactions import Interaction
from discord.ui import (
    ActionRow,
    Button,
    Container,
    Item,
    LayoutView,
    Section,
    Separator,
    TextDisplay,
    Thumbnail,
    button,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.utils import discord_ts


class PaginationButtons(ActionRow["InfractionsViewV2"]):
    def __init__(self):
        super().__init__()

    async def interaction_check(
        self,
        interaction: Interaction,
    ) -> bool:
        """Ensure that only the author can interact with the view."""
        if interaction.user.id != self.view.author_id:  # type: ignore
            await interaction.response.send_message(
                "Вы не можете управлять этой пагинацией.", ephemeral=True
            )
            return False
        return True

    @button(
        style=ButtonStyle.secondary,
        emoji="<:41036arrowforwardios1:1442925401696632934>",
        custom_id="infractions_prev",
    )
    async def previous(
        self, interaction: Interaction, button: Button[InfractionsViewV2]
    ):
        """Go to the previous page."""
        view = self.view  # type: ignore
        if view.current_page > 0:  # type: ignore
            view.current_page -= 1  # type: ignore
        await interaction.response.edit_message(
            view=view.make_component(),  # type: ignore
        )

    @button(
        style=ButtonStyle.secondary,
        emoji="<:41036arrowforwardios:1442924853085864178>",
        custom_id="infractions_next",
    )
    async def next(
        self, interaction: Interaction, button: Button[InfractionsViewV2]
    ):
        """Go to the next page."""
        view = self.view  # type: ignore
        if view.current_page < len(view.pages) - 1:  # type: ignore
            view.current_page += 1  # type: ignore
        await interaction.response.edit_message(
            view=view.make_component(),  # type: ignore
        )


class InfractionsViewV2(LayoutView):
    def __init__(
        self,
        author_id: int,
        pages: list[str],
        user: User,
        bot: Nightcore,
        total_punishments: int,
        count_last_7_days_infractions: int,
    ):
        super().__init__(timeout=None)
        self.author_id = author_id
        self.pages = pages
        self.current_page = 0
        self.user = user
        self.bot = bot
        self.total_punishments = total_punishments
        self.count_last_7_days_infractions = count_last_7_days_infractions

        self.pagination: PaginationButtons | None = None
        self.header_text: TextDisplay[Self] | None = None
        self.main_text: TextDisplay[Self] | None = None
        self.footer_text: TextDisplay[Self] | None = None

        self.make_component()

    def _update_buttons(self):
        if not self.pagination:
            return
        for child in self.pagination.children:
            if isinstance(child, Button):
                if child.custom_id == "infractions_prev":
                    child.disabled = self.current_page == 0  # type: ignore
                elif child.custom_id == "infractions_next":
                    child.disabled = self.current_page == len(self.pages) - 1  # type: ignore

    def make_component(self) -> Self:
        """Create the layout view component."""

        # important: clear previous items to avoid duplicate custom_id
        self.clear_items()

        container = Container[Self](accent_color=Color.from_str("#ffffff"))

        # Header

        container.add_item(
            Section[Self](
                TextDisplay[Self](
                    f"## <:winternightcoreinfractions:1450531448384917614> Список нарушений\n"  # noqa: E501
                    f"**Пользователь:** {self.user.mention} `({self.user.id})`\n"  # noqa: E501
                    f"**Общее количество нарушений:** `{self.total_punishments}`\n"  # noqa: E501
                    f"> **Количество нарушений за последние 7 дней:** `{self.count_last_7_days_infractions}`"  # noqa: E501
                ),
                accessory=Thumbnail(self.user.display_avatar.url),
            )
        )
        container.add_item(Separator[Self]())

        container.add_item(TextDisplay[Self](self.pages[self.current_page]))
        container.add_item(Separator[Self]())

        if len(self.pages) > 1:
            self.pagination = PaginationButtons()
            container.add_item(self.pagination)
            container.add_item(Separator[Self]())
        else:
            self.pagination = None

        now = datetime.now(UTC)

        container.add_item(
            TextDisplay[Self](
                f"-# Page {self.current_page + 1} of {len(self.pages)}\n"
                f"-# Powered by {self.bot.user.name} in {discord_ts(now)}"  # type: ignore
            )
        )

        self.add_item(container)

        # update buttons after adding items
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
