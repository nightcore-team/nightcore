"""View for paginating infractions."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Self, cast

import discord
from discord import (
    ButtonStyle,
    File,
    Guild,
    MediaGalleryItem,
    Member,
    Role,
    User,
)
from discord.interactions import Interaction
from discord.ui import (
    ActionRow,
    Button,
    Container,
    Item,
    LayoutView,
    MediaGallery,
    Section,
    Separator,
    TextDisplay,
    Thumbnail,
    button,
)

from src.nightcore.bot import Nightcore
from src.nightcore.components.embed import (
    MissingPermissionsEmbed,
)
from src.nightcore.features.moderation.events.dto import UserBannedEventData
from src.nightcore.utils import discord_ts, has_any_role

logger = logging.getLogger(__name__)


class ActionButtons(ActionRow["BanRequestViewV2"]):
    def __init__(self):
        super().__init__()

    async def interaction_check(
        self,
        interaction: Interaction,
    ) -> bool:
        """Ensure that only users with ban access roles can interact with the view."""  # noqa: E501
        view = self.view  # type: ignore
        user = cast(Member, interaction.user)
        has_moder_role = has_any_role(user, view.moderation_access_roles_ids)  # type: ignore
        if not has_moder_role:
            await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
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
        view = cast(BanRequestViewV2, self.view)
        moderator = cast(Member, interaction.user)
        guild = cast(Guild, interaction.guild)

        async with view.approve_lock:
            if view.is_closed:
                return await interaction.response.send_message(
                    "This ban request has already been closed.",
                    ephemeral=True,
                )

            if moderator.id in view.in_favor:
                return await interaction.response.send_message(
                    "You have already voted in favor of this ban request.",
                    ephemeral=True,
                )

            view.in_favor.append(moderator.id)
            view.in_favor_moderators_text += f"- <@{moderator.id}>\n"

            if not (
                len(view.in_favor) >= 4
                or has_any_role(
                    moderator,
                    view.ban_access_roles_ids,
                )
            ):
                return await interaction.response.edit_message(
                    view=view.make_component()
                )

            view.is_closed = True
            view.accent_color = discord.Color.green()

            await interaction.response.defer()

            await interaction.edit_original_response(
                view=view.make_component(disabled=True)
            )

        target = view.target

        try:
            view.bot.dispatch(
                "user_banned",
                data=UserBannedEventData(
                    category="ban",
                    moderator=moderator,
                    user=target,
                    reason=view.reason,
                    created_at=discord.utils.utcnow().astimezone(
                        tz=timezone.utc
                    ),
                    duration=view.duration,
                    original_duration=view.original_duration,
                    delete_messages_per=view.original_delete_seconds,
                ),
            )
        except Exception as e:
            logger.exception(
                "[event] - Failed to dispatch user_banned event: %s", e
            )

        try:
            await guild.ban(
                target,
                reason=view.reason,  # type: ignore
                delete_message_seconds=view.delete_seconds,  # type: ignore
            )
        except (discord.Forbidden, discord.HTTPException) as e:
            logger.exception(
                "Failed to ban user=%s guild=%s: %s", target.id, guild.id, e
            )

            view.accent_color = discord.Color.red()  # type: ignore
            await interaction.edit_original_response(
                view=view.make_component(disabled=True)  # type: ignore
            )
            await interaction.followup.send(
                embed=MissingPermissionsEmbed(
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

            return

        return

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
        view = cast("BanRequestViewV2", self.view)
        user = cast(Member, interaction.user)

        if view.is_closed:
            return await interaction.response.send_message(
                "This ban request has already been closed.",
                ephemeral=True,
            )

        if user.id in view.against:
            return await interaction.response.send_message(
                "You have already voted against this ban request.",
                ephemeral=True,
            )

        view.against.append(user.id)

        view.against_moderators_text += f"- <@{user.id}>\n"

        has_ban_role = has_any_role(user, view.ban_access_roles_ids)
        if (
            has_ban_role
            or interaction.user.id == view.author_id
            or len(view.against) >= 4
        ):
            view.accent_color = discord.Color.red()

            view.is_closed = True

            await interaction.response.defer()

            return await interaction.edit_original_response(
                view=view.make_component(disabled=True),
            )

        await interaction.response.defer()

        await interaction.edit_original_response(
            view=view.make_component(),
        )


class BanRequestViewV2(LayoutView):
    def __init__(
        self,
        author_id: int,
        reason: str,
        target: User | Member,
        bot: Nightcore,
        duration: int,
        original_duration: str,
        delete_seconds: int,
        moderation_access_roles_ids: list[int],
        ban_access_roles_ids: list[int],
        original_delete_seconds: str | None = None,
        ping_role: Role | None = None,
        attachments: list[File] | None = None,
        timeout: int = 180,
    ):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.reason = reason
        self.target = target
        self.bot = bot
        self.duration = duration
        self.original_duration = original_duration
        self.delete_seconds = delete_seconds
        self.original_delete_seconds = original_delete_seconds
        self.moderation_access_roles_ids = moderation_access_roles_ids
        self.ban_access_roles_ids = ban_access_roles_ids
        self.ping_role = ping_role
        self.attachments = attachments

        self.actions: ActionButtons | None = None
        self.header_text: TextDisplay[Self] | None = None
        self.footer_text: TextDisplay[Self] | None = None
        self.in_favor_moderators_text = ""
        self.against_moderators_text = ""
        self.accent_color = discord.Color.yellow()

        self.approve_lock = asyncio.Lock()
        self.in_favor: list[int] = []
        self.against: list[int] = []
        self.is_closed: bool = False

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

        container = Container[Self](accent_color=self.accent_color)

        if self.ping_role:
            container.add_item(
                TextDisplay[Self](f"### {self.ping_role.mention}")
            )
            container.add_item(Separator[Self]())

        self.header_text = TextDisplay[Self](
            f"Name | ID: {self.target.mention} | `{self.target.id}`\n"
            f"Moderator: <@{self.author_id}>\n"
            f"Reason: **`{self.reason}`**\n"
            f"Duration: **`{self.original_duration}`**\n"
            f"Delete messages for last: **`{self.original_delete_seconds if self.original_delete_seconds else 'N/A'}`**\n"  # noqa: E501
        )
        header_section = Section[Self](
            self.header_text,
            accessory=Thumbnail(self.target.display_avatar.url),
        )
        container.add_item(header_section)
        container.add_item(Separator[Self]())

        container.add_item(TextDisplay[Self]("### In Favor:"))
        if self.in_favor_moderators_text:
            container.add_item(
                TextDisplay[Self](self.in_favor_moderators_text)
            )
        container.add_item(TextDisplay[Self]("### Against:"))
        if self.against_moderators_text:
            container.add_item(TextDisplay[Self](self.against_moderators_text))

        container.add_item(Separator[Self]())

        # Main page text
        if self.attachments:
            attachments_text = TextDisplay[Self]("### Attachments:")
            container.add_item(attachments_text)
            attachments: list[MediaGalleryItem] = []
            for att in self.attachments:
                attachments.append(MediaGalleryItem(att))  # type: ignore

            container.add_item(MediaGallery[Self](*attachments))
            container.add_item(Separator[Self]())

        # Action buttons
        self.actions = ActionButtons()
        container.add_item(self.actions)
        container.add_item(Separator[Self]())

        # Footer
        now = datetime.now(timezone.utc)
        self.footer_text = TextDisplay[Self](
            f"-# Powered by {self.bot.user.name} in {discord_ts(now)}"  # type: ignore
        )
        container.add_item(self.footer_text)

        if disabled:
            self.disable_buttons()

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
