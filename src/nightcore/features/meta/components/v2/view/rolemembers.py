"""Role members view v2 component."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Self

from discord import ButtonStyle, Role
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

from src.nightcore.utils import discord_ts

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


class PaginationButtons(ActionRow["RoleMembersViewV2"]):
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
        custom_id="rolemembers:prev",
    )
    async def previous(
        self, interaction: Interaction, button: Button["RoleMembersViewV2"]
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
        custom_id="rolemembers:next",
    )
    async def next(
        self, interaction: Interaction, button: Button["RoleMembersViewV2"]
    ):
        """Go to the next page."""
        view = self.view  # type: ignore
        if view.current_page < len(view.pages) - 1:  # type: ignore
            view.current_page += 1  # type: ignore
        await interaction.response.edit_message(
            view=view.make_component(),  # type: ignore
        )


class RoleMembersViewV2(LayoutView):
    def __init__(
        self,
        bot: "Nightcore",
        author_id: int,
        pages: list[str],
        role: Role,
        members_count: int,
        timeout: int = 180,
    ) -> None:
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.pages = pages
        self.current_page = 0
        self.role = role
        self.members_count = members_count
        self.bot = bot

        self.pagination: PaginationButtons | None = None
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
                if child.custom_id == "rolemembers_prev":
                    child.disabled = self.current_page == 0  # type: ignore
                elif child.custom_id == "rolemembers_next":
                    child.disabled = self.current_page == len(self.pages) - 1  # type: ignore

    def make_component(self) -> Self:
        """Create the layout view component."""

        # Important: clear previous items to avoid duplicate custom_id
        self.clear_items()

        container = Container[Self]()

        header_section: TextDisplay[Self] | Section[Self] = TextDisplay[Self](
            f"### <:10447information:1442922761591849021> Список участников с ролью\n"  # noqa: E501
            f"Роль: {self.role.mention}\n"
            f"ID роли: **`{self.role.id}`**\n"
            f"Количество участников: **{self.members_count}**"
        )
        if self.role.icon:
            header_section = Section[Self](
                header_section,
                accessory=Thumbnail(self.role.icon.url),
            )

        container.add_item(header_section)
        container.add_item(Separator[Self]())

        page_content = self.pages[self.current_page]
        container.add_item(TextDisplay[Self](page_content))
        container.add_item(Separator[Self]())

        # Footer
        now = datetime.now(timezone.utc)
        container.add_item(
            TextDisplay[Self](
                f"-# Page {self.current_page + 1} of {len(self.pages)}\n"
                f"-# Powered by {self.bot.user.name} in {discord_ts(now)}"  # type: ignore
            )
        )

        self.add_item(container)

        # Update buttons after adding items
        self._update_buttons()
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
