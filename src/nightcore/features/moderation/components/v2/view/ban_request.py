"""View for paginating infractions."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Self, cast

import discord
from discord import ButtonStyle, Guild, Member, Role, User
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
from src.nightcore.components.embed import (
    ErrorEmbed,
    MissingPermissionsEmbed,
    SuccessMoveEmbed,
)
from src.nightcore.features.moderation.events.dto import UserBannedEventData
from src.nightcore.features.moderation.utils import calculate_end_time
from src.nightcore.utils import discord_ts, has_any_role

logger = logging.getLogger(__name__)


class ActionButtons(ActionRow["BanRequestViewV2"]):
    def __init__(self):
        super().__init__()
        self.in_favor: list[int] = []
        self.against: list[int] = []

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
        view = self.view  # type: ignore
        moderator = cast(Member, interaction.user)
        guild = cast(Guild, interaction.guild)

        if moderator.id in self.in_favor:
            return await interaction.response.send_message(
                "You have already voted in favor of this ban request.",
                ephemeral=True,
            )

        # Оновлення голосів
        self.in_favor.append(moderator.id)
        view.in_favor_moderators_text += f"- <@{moderator.id}>\n"  # type: ignore

        approve_ban = len(self.in_favor) >= 4 or has_any_role(
            moderator,
            view.ban_access_roles_ids,  # type: ignore
        )
        if not approve_ban:
            return await interaction.response.edit_message(
                view=view.make_component()  # type: ignore
            )

        target = view.target  # type: ignore
        end_time = calculate_end_time(view.duration)  # type: ignore

        # Миттєво ACK'аємо, щоб клієнт не чекав
        await interaction.response.defer()

        try:
            await guild.ban(
                target,
                reason=view.reason,  # type: ignore
                delete_message_seconds=view.delete_seconds,  # type: ignore
            )
        except discord.Forbidden as e:
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
        except discord.HTTPException as e:
            logger.exception(
                "Failed to ban user=%s guild=%s: %s", target.id, guild.id, e
            )
            view.accent_color = discord.Color.red()  # type: ignore
            await interaction.edit_original_response(
                view=view.make_component(disabled=True)  # type: ignore
            )
            await interaction.followup.send(
                embed=ErrorEmbed(
                    "User Ban Failed",
                    "Failed to ban user.",
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )
            return

        # success: update original message and send followup
        view.accent_color = discord.Color.green()  # type: ignore
        await interaction.edit_original_response(
            view=view.make_component(disabled=True)  # type: ignore
        )

        try:
            view.bot.dispatch(  # type: ignore
                "user_banned",
                data=UserBannedEventData(
                    category="ban",
                    moderator=moderator,
                    user=target,
                    reason=view.reason,  # type: ignore
                    created_at=discord.utils.utcnow().astimezone(
                        tz=timezone.utc
                    ),
                    duration=view.duration,  # type: ignore
                    original_duration=view.original_duration,  # type: ignore
                    end_time=end_time,  # type: ignore
                ),
            )
        except Exception as e:
            logger.exception(
                "[event] - Failed to dispatch user_banned event: %s", e
            )

        # followup можна не блокувати
        await interaction.followup.send(
            embed=SuccessMoveEmbed(
                "User Banned",
                f"<@{target.id}> has been banned.",
                view.bot.user.name,  # type: ignore
                view.bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

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
        view = self.view  # type: ignore
        user = cast(Member, interaction.user)

        if user.id in self.against:
            return await interaction.response.send_message(
                "You have already voted against this ban request.",
                ephemeral=True,
            )

        self.against.append(user.id)

        view.against_moderators_text += (  # type: ignore
            f"- <@{user.id}>\n"
        )

        await interaction.response.defer()

        has_ban_role = has_any_role(user, view.ban_access_roles_ids)  # type: ignore
        if (
            has_ban_role
            or interaction.user.id == view.author_id  # type: ignore
            or len(self.against) >= 4
        ):
            view.accent_color = discord.Color.red()  # type: ignore

            return await interaction.edit_original_response(
                view=view.make_component(disabled=True),  # type: ignore
            )

        await interaction.edit_original_response(
            view=view.make_component(),  # type: ignore
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
        original_delete_seconds: str,
        moderation_access_roles_ids: list[int],
        ban_access_roles_ids: list[int],
        ping_role: Role | None = None,
        attachments: list[str] | None = None,
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
