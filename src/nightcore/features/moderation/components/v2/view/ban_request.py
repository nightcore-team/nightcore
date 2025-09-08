"""View for paginating infractions."""

from datetime import datetime, timezone
from typing import Self

from discord import ButtonStyle, Member, User
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

from src.nightcore.bot import Nightcore
from src.nightcore.utils import discord_ts


class ActionButtons(ActionRow["BanRequestViewV2"]):
    def __init__(self):
        super().__init__()

    async def interaction_check(
        self,
        interaction: Interaction,
    ) -> bool:
        """Ensure that only the author can interact with the view."""
        if interaction.user.id != self.view.author_id:  # type: ignore
            await interaction.response.send_message(
                "You can't manage this pagination.", ephemeral=True
            )
            return False
        return True

    @button(
        style=ButtonStyle.green,
        emoji="<:52104checkmark:1414732973005340672>",
        label="Approve",
        custom_id="ban_request_approve",
    )
    async def approve(
        self, interaction: Interaction, button: Button["BanRequestViewV2"]
    ):
        """Approve the ban request."""

    @button(
        style=ButtonStyle.red,
        emoji="<:9349_nope:1414732960841859182>",
        label="Deny",
        custom_id="ban_request_deny",
    )
    async def deny(
        self, interaction: Interaction, button: Button["BanRequestViewV2"]
    ):
        """Deny the ban request."""


class BanRequestViewV2(LayoutView):
    def __init__(
        self,
        author_id: int,
        reason: str,
        user: User | Member,
        bot: Nightcore,
        duration: int,
        original_duration: str,
        delete_seconds: int,
        original_delete_seconds: str,
        ban_access_roles_ids: list[int],
        timeout: int = 180,
    ):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.reason = reason
        self.user = user
        self.bot = bot
        self.original_duration = original_duration
        self.ban_access_roles_ids = ban_access_roles_ids
        self.duration = duration
        self.delete_seconds = delete_seconds
        self.original_delete_seconds = original_delete_seconds

        self.actions: ActionButtons | None = None
        self.header_text: TextDisplay[Self] | None = None
        self.footer_text: TextDisplay[Self] | None = None

        self.make_component()

    def _disable_buttons(self): ...

    def make_component(self) -> Self:
        """Create the layout view component."""

        # important: clear previous items to avoid duplicate custom_id
        self.clear_items()

        container = Container[Self]()

        # Header
        self.notify_test = TextDisplay[Self]("## Ban Request Form")
        container.add_item(self.notify_test)
        container.add_item(Separator[Self]())

        self.header_text = TextDisplay[Self](
            f"Name | ID: {self.user.global_name} | {self.user.id}\n"
            f"Reason: **`{self.reason}`**\n"
            f"Duration: **`{self.original_duration}`**\n"
            f"Delete message for last: **`{self.original_delete_seconds if self.original_delete_seconds else 'N/A'}`**\n"  # noqa: E501
        )
        header_section = Section[Self](
            self.header_text,
            accessory=Thumbnail(self.user.display_avatar.url),
        )
        container.add_item(header_section)
        container.add_item(Separator[Self]())

        # Main page text
        page_content = "Attachments:\n"
        self.main_text = TextDisplay[Self](page_content)
        container.add_item(Separator[Self]())

        # Action buttons
        self.actions = ActionButtons()

        # Footer
        now = datetime.now(timezone.utc)
        self.footer_text = TextDisplay[Self](
            f"-# Powered by {self.bot.user.name} in {discord_ts(now)}"  # type: ignore
        )
        container.add_item(self.footer_text)

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
