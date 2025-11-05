"""Modal for submitting ban requests."""

import logging
from typing import TYPE_CHECKING

import discord
from discord.ui import Modal, TextInput

from src.config.config import config
from src.nightcore.components.embed import (
    ErrorEmbed,
    SuccessMoveEmbed,
    ValidationErrorEmbed,
)
from src.nightcore.features.moderation.components.v2 import BanRequestViewV2
from src.nightcore.utils.time_utils import parse_duration

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


class BanFormModal(Modal, title="Send Ban Request"):
    duration = TextInput["BanFormModal"](
        label="Duration s/m/d/w",
        placeholder="Example: 30m, 2h, 3d",
        required=True,
        max_length=50,
    )

    reason = TextInput["BanFormModal"](
        label="Reason for punishment",
        style=discord.TextStyle.paragraph,
        placeholder="Describe the reason...",
        required=True,
        max_length=1000,
    )

    delete_messages_for_last = TextInput["BanFormModal"](
        label="Delete messages for the last",
        style=discord.TextStyle.short,
        placeholder="Example: 1m, 1h, 1d, 7d",
        required=False,
        max_length=20,
    )

    def __init__(
        self,
        target: discord.Member | discord.User,
        moderator: discord.Member,
        bot: "Nightcore",
        channel: discord.TextChannel | discord.Thread,
        ban_access_roles_ids: list[int],
        moderation_access_roles_ids: list[int],
        ping_role: discord.Role | None = None,
    ):
        super().__init__()
        self.target = target
        self.moderator = moderator
        self.bot = bot
        self.ping_role = ping_role
        self.channel = channel
        self.ban_access_roles_ids = ban_access_roles_ids
        self.moderation_access_roles_ids: list[int] = (
            moderation_access_roles_ids
        )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Handles the submission of the ban form modal."""
        reason = self.reason.value

        await interaction.response.defer(ephemeral=True, thinking=True)

        duration_seconds = parse_duration(self.duration.value)
        if duration_seconds is None:
            return await interaction.followup.send(
                embed=ValidationErrorEmbed(
                    "Invalid duration format. Use s/m/h/d (e.g., 30m, 2h, 3d).",  # noqa: E501
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        delete_seconds = 0
        original_delete_seconds = ""
        if self.delete_messages_for_last.value:
            delete_seconds = parse_duration(
                self.delete_messages_for_last.value
            )
            if delete_seconds is None:
                return await interaction.followup.send(
                    embed=ValidationErrorEmbed(
                        "Invalid message deletion duration. Use s/m/h/d up to 7d (e.g., 1h, 1d, 7d).",  # noqa: E501
                        self.bot.user.name,  # type: ignore
                        self.bot.user.display_avatar.url,  # type: ignore
                    ),
                )

            if delete_seconds > config.bot.DELETE_MESSAGES_SECONDS:
                return await interaction.followup.send(
                    embed=ValidationErrorEmbed(
                        f"Message deletion duration cannot exceed {config.bot.DELETE_MESSAGES_SECONDS // 86400} days.",  # noqa: E501
                        self.bot.user.name,  # type: ignore
                        self.bot.user.display_avatar.url,  # type: ignore
                    ),
                )

            original_delete_seconds = self.delete_messages_for_last.value

        view = BanRequestViewV2(
            author_id=self.moderator.id,
            reason=reason,
            target=self.target,
            bot=self.bot,
            ping_role=self.ping_role,
            original_duration=self.duration.value,
            duration=duration_seconds,
            original_delete_seconds=original_delete_seconds,
            delete_seconds=delete_seconds,
            ban_access_roles_ids=self.ban_access_roles_ids,
            moderation_access_roles_ids=self.moderation_access_roles_ids,
        )

        try:
            message = await self.channel.send(view=view)

            await interaction.followup.send(
                embed=SuccessMoveEmbed(
                    "Ban Request Submitted",
                    f"Your {message.jump_url} for {self.target.mention} has sent successfully.",  # noqa: E501
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                )
            )

        except Exception as e:
            logger.exception(
                "Failed to send message in guild %s to channel %s: %s",
                self.channel.guild.id,
                self.channel.id,
                e,
            )
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Ban Request Failed",
                    "Failed to send ban request message.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                )
            )

        logger.info(
            "[ban_request_submit] - invoked user=%s guild=%s target=%s duration=%s reason=%s delete_messages_for_last=%s",  # noqa: E501
            self.moderator.id,
            self.channel.guild.id,
            self.target.id,
            self.duration.value,
            reason,
            self.delete_messages_for_last.value,
        )
