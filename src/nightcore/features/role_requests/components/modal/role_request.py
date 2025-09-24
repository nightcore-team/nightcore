"""Modal for submitting ban requests."""

import logging
from typing import TYPE_CHECKING, Self, cast

import discord
from discord.ui import Modal, TextInput

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.components.embed import (
    ErrorEmbed,
    MissingPermissionsEmbed,
    SuccessMoveEmbed,
    ValidationErrorEmbed,
)
from src.nightcore.features.role_requests.components.v2.view.check_role_request import (  # noqa: E501
    CheckRoleRequestView,
)
from src.nightcore.features.role_requests.utils import validate_user_nickname

logger = logging.getLogger(__name__)


class RoleRequestModal(Modal, title="Send Role Request"):
    nickname = TextInput[Self](
        label="Enter your nickname in format: Name_Surname",
        style=discord.TextStyle.short,
        placeholder="Example: Raymond_Walker",
        required=True,
        max_length=35,
    )

    rank = TextInput[Self](
        label="Enter your rank",
        style=discord.TextStyle.short,
        placeholder="Example: 1",
        required=True,
        max_length=2,
    )

    def __init__(
        self,
        user: discord.Member,
        channel: discord.abc.GuildChannel | discord.Thread,
        role: discord.Role,
        selected_role_tag: str,
        bot: "Nightcore",
    ):
        super().__init__()
        self.user = user
        self.bot = bot
        self.channel = channel
        self.requested_role = role
        self.selected_role_tag = selected_role_tag

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Handles the submission of the ban form modal."""
        guild = cast(discord.Guild, interaction.guild)

        nickname = validate_user_nickname(self.nickname.value)
        if not nickname:
            return await interaction.response.send_message(
                embed=ValidationErrorEmbed(
                    "Invalid nickname format. Please use Name_Surname.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        try:
            rank = int(self.rank.value)
        except ValueError:
            return await interaction.response.send_message(
                embed=ValidationErrorEmbed(
                    "Invalid rank format. Please enter a valid number.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if not guild.me.guild_permissions.manage_nicknames:
            return await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                    "I do not have permission to manage messages.",
                ),
                ephemeral=True,
            )

        try:
            await self.user.edit(
                nick=f"[{self.selected_role_tag}][{rank}] {nickname}",
            )
        except Exception:
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Nickname Change Failed",
                    "I was unable to change your nickname.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        await interaction.response.defer()

        view = CheckRoleRequestView(
            bot=self.bot,
            interaction_user_id=self.user.id,
            role_requested_id=self.requested_role.id,
        )

        try:
            await self.channel.send(view=view)  # type: ignore

            await interaction.followup.send(
                embed=SuccessMoveEmbed(
                    "Role Request Submitted",
                    "Your role request has sent successfully.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
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
            "[role_request_submit] - invoked user=%s guild=%s role=%s",
            self.user.id,
            guild.id,
            self.requested_role.id,
        )
