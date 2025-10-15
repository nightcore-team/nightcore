"""View for paginating infractions."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Self, cast

import discord
from discord import ButtonStyle, Member, User
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

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.utils import discord_ts

logger = logging.getLogger(__name__)


class ActionButtons(ActionRow["AttachmentsCollectorV2"]):
    def __init__(self):
        super().__init__()

    async def interaction_check(
        self,
        interaction: Interaction,
    ) -> bool:
        """Ensure that only the author can interact with the view."""
        if interaction.user.id != self.view.author_id:  # type: ignore
            await interaction.response.send_message(
                "You can't manage this buttons.", ephemeral=True
            )
            return False
        return True

    @button(
        style=ButtonStyle.green,
        emoji="<:52104checkmark:1414732973005340672>",
        label="Done",
        custom_id="done_attachments_collector",
    )
    async def done_button(
        self,
        interaction: Interaction,
        button: Button["AttachmentsCollectorV2"],
    ):
        """Mark the collection as done."""
        view = cast(AttachmentsCollectorV2, self.view)
        if not view.done.is_set():
            view.done.set()

            view.color = discord.Color.green()
            view.text = "Attachment collection completed."
            view.make_component()

        await interaction.response.defer()

        await interaction.edit_original_response(
            view=view.make_component(disabled=True)
        )

    @button(
        style=ButtonStyle.red,
        emoji="<:9349_nope:1414732960841859182>",
        label="Cancel",
        custom_id="cancel_attachments_collector",
    )
    async def cancel_button(
        self,
        interaction: Interaction,
        button: Button["AttachmentsCollectorV2"],
    ):
        """Cancel the collection."""

        view = cast(AttachmentsCollectorV2, self.view)

        if not view.done.is_set():
            view.cancelled = True
            view.done.set()

            view.color = discord.Color.red()
            view.make_component()
            view.text = "Attachment collection cancelled."

        await interaction.response.defer()

        await interaction.edit_original_response(
            view=view.make_component(disabled=True)
        )


class AttachmentsCollectorV2(LayoutView):
    def __init__(
        self,
        author_id: int,
        user: User | Member,
        bot: "Nightcore",
        timeout: int = 3600,
    ):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.done = asyncio.Event()
        self.cancelled = False
        self.user: User | Member = user
        self.bot = bot

        self.actions: ActionButtons | None = None
        self.color: discord.Color | None = None
        self.text: str | None = None

        self.make_component()

    def disable_buttons(self):
        """Disable all buttons in the view."""
        if self.actions:
            for item in self.actions.children:
                if isinstance(item, Button):
                    item.disabled = True

    def make_component(self, *, disabled: bool = False) -> Self:
        """Create the layout view component."""

        # important: clear previous items to avoid duplicate custom_id
        self.clear_items()

        container = Container[Self](accent_color=self.color)
        container.add_item(TextDisplay[Self]("## Review Attachments"))
        container.add_item(Separator())
        if self.text:
            container.add_item(TextDisplay[Self](self.text))
        else:
            container.add_item(
                TextDisplay[Self](
                    f"Collecting attachments for the ban request of {self.user.mention}.\n"  # noqa: E501
                    "You can upload up to 7 images.\n\n"
                    "Click 'Done' when finished or 'Cancel' to abort."
                )
            )
        container.add_item(Separator())
        self.actions = ActionButtons()
        container.add_item(self.actions)

        if disabled:
            self.disable_buttons()

        now = datetime.now(timezone.utc)

        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {self.bot.user.name} in {discord_ts(now)}"  # type: ignore
            )
        )

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
