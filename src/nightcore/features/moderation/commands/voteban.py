"""Mute command for the Nightcore bot."""

import asyncio
import logging
from typing import cast

import discord
from discord import (
    File,
    Guild,
    Member,
    User,
    app_commands,
)
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.config.config import config
from src.infra.db.models import GuildModerationConfig
from src.nightcore.bot import Nightcore
from src.nightcore.components.embed import (
    EntityNotFoundEmbed,
    ErrorEmbed,
    MissingPermissionsEmbed,
    SuccessMoveEmbed,
    ValidationErrorEmbed,
)
from src.nightcore.exceptions import FieldNotConfiguredError
from src.nightcore.features.moderation.components.v2 import BanRequestViewV2
from src.nightcore.features.moderation.components.view import (
    AttachmentsCollectorView,
)
from src.nightcore.features.moderation.utils import (
    compare_top_roles,
    parse_duration,
)
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils import ensure_member_exists, has_any_role

logger = logging.getLogger(__name__)


class Voteban(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @app_commands.command(
        name="voteban", description="Vote to ban a user on the server"
    )
    @app_commands.describe(
        user="The user to ban", reason="The reason for banning the user"
    )
    async def voteban(
        self,
        interaction: Interaction,
        user: User,
        duration: str,
        reason: str,
        delete_messages_per: str | None = None,
    ):
        """Vote to ban a user on the server."""
        guild = cast(Guild, interaction.guild)

        # Ensure we have a guild Member object
        member = await ensure_member_exists(guild, user)

        if member is None:
            return await interaction.response.send_message(
                embed=EntityNotFoundEmbed(
                    "user",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        ping_role = None

        async with specified_guild_config(
            self.bot,
            guild.id,
            GuildModerationConfig,
            _create=False,
        ) as (guild_config, _):
            if not (
                moderation_access_roles
                := guild_config.moderation_access_roles_ids
            ):
                raise FieldNotConfiguredError("moderation access")

            if not (ban_access_roles := guild_config.ban_access_roles_ids):
                raise FieldNotConfiguredError("ban access")

            if not (
                ban_request_channel_id
                := guild_config.send_ban_request_channel_id
            ):
                raise FieldNotConfiguredError("ban request channel")

            ping_role_id = guild_config.ban_request_ping_role_id

        if ping_role_id:
            ping_role = guild.get_role(ping_role_id)

        has_moder_role = has_any_role(
            cast(Member, interaction.user), moderation_access_roles
        )

        if not has_moder_role:
            return await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        is_member_moderator = has_any_role(member, moderation_access_roles)
        if is_member_moderator:
            return await interaction.response.send_message(
                embed=ValidationErrorEmbed(
                    "You cannot ban moderators.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if member.guild_permissions.administrator:
            return await interaction.response.send_message(
                embed=ValidationErrorEmbed(
                    "You cannot ban administrators.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if guild.me == member:
            return await interaction.response.send_message(
                embed=ValidationErrorEmbed(
                    "You cannot ban me.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if not compare_top_roles(guild, member):
            return await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                    "I cannot ban this user because he has a higher role than me.",  # noqa: E501
                ),
                ephemeral=True,
            )

        parsed_duration = parse_duration(duration)

        if not parsed_duration:
            return await interaction.response.send_message(
                embed=ValidationErrorEmbed(
                    "Invalid duration. Use s/m/h/d up to 7d (e.g., 1h, 1d, 7d).",  # noqa: E501
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        parsed_delete_messages_per_seconds = 0

        if delete_messages_per:
            tmp_delete_messages_per = parse_duration(delete_messages_per)

            if tmp_delete_messages_per is None:
                return await interaction.response.send_message(
                    embed=ValidationErrorEmbed(
                        "Invalid message deletion duration. Use s/m/h/d up to 7d (e.g., 1h, 1d, 7d).",  # noqa: E501
                        self.bot.user.name,  # type: ignore
                        self.bot.user.display_avatar.url,  # type: ignore
                    ),
                )

            if tmp_delete_messages_per > config.bot.DELETE_MESSAGES_SECONDS:
                return await interaction.response.send_message(
                    embed=ValidationErrorEmbed(
                        f"Message deletion duration cannot exceed {config.bot.DELETE_MESSAGES_SECONDS // 86400} days.",  # noqa: E501
                        self.bot.user.name,  # type: ignore
                        self.bot.user.display_avatar.url,  # type: ignore
                    ),
                )

            parsed_delete_messages_per_seconds = tmp_delete_messages_per

        channel = guild.get_channel(ban_request_channel_id)
        if channel is None:
            try:
                channel = await guild.fetch_channel(ban_request_channel_id)  # type: ignore
                if not isinstance(
                    channel, discord.TextChannel | discord.Thread
                ):
                    logger.warning(
                        "[ban_request_callback] channel %s not messageable (%s)",  # noqa: E501
                        channel.id,  # type: ignore
                        type(channel).__name__,
                    )
                    return await interaction.response.send_message(
                        embed=ValidationErrorEmbed(
                            "Channel's type must be a TextChannel or Thread",
                            self.bot.user.name,  # type: ignore
                            self.bot.user.display_avatar.url,  # type: ignore
                        )
                    )

            except discord.NotFound:
                return await interaction.response.send_message(
                    embed=EntityNotFoundEmbed(
                        "channel",
                        self.bot.user.name,  # type: ignore
                        self.bot.user.display_avatar.url,  # type: ignore
                    )
                )

        acview = AttachmentsCollectorView(author_id=interaction.user.id)

        # TODO: write more readeble message
        await interaction.response.send_message(
            f"Collecting attachments for the ban request of {user.mention}. You can upload up to 7 images. Click 'Done' when finished or 'Cancel' to abort.",  # noqa: E501
            view=acview,
            ephemeral=True,
        )

        collected_attachments: list[File] = []

        def check(message: discord.Message):
            if message.author.id != interaction.user.id:
                return False
            if message.channel.id != interaction.channel_id:
                return False
            if not message.attachments:  # noqa: SIM103
                return False
            return True

        async def listener():
            while not acview.done.is_set():
                try:
                    msg = await self.bot.wait_for(
                        "message", timeout=1.0, check=check
                    )
                except asyncio.TimeoutError:
                    continue
                for att in msg.attachments:
                    if len(collected_attachments) >= 7:
                        break
                    att_file = await att.to_file()
                    collected_attachments.append(att_file)  # type: ignore
                if len(collected_attachments) >= 7:
                    acview.done.set()

        listener_task = asyncio.create_task(listener())

        try:
            await acview.done.wait()
        finally:
            listener_task.cancel()

        if acview.cancelled:
            await interaction.followup.send(
                "Collection cancelled. Request not created.", ephemeral=True
            )
            return

        view = BanRequestViewV2(
            author_id=interaction.user.id,
            reason=reason,
            target=user,
            bot=self.bot,
            ping_role=ping_role,
            original_duration=duration,
            duration=parsed_duration,
            original_delete_seconds=delete_messages_per,
            delete_seconds=parsed_delete_messages_per_seconds,
            ban_access_roles_ids=ban_access_roles,
            moderation_access_roles_ids=moderation_access_roles,
            attachments=collected_attachments,
        )

        try:
            message = await channel.send(  # type: ignore
                view=view, files=collected_attachments
            )

            await interaction.followup.send(
                embed=SuccessMoveEmbed(
                    "Ban Request Submitted",
                    f"Your {message.jump_url} for {user.mention} has sent successfully.",  # noqa: E501 # type: ignore
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        except Exception as e:
            logger.exception(
                "Failed to send message in guild %s to channel %s: %s",
                channel.guild.id,
                channel.id,
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
            interaction.user.id,
            channel.guild.id,
            user.id,
            duration,
            reason,
            delete_messages_per,
        )


async def setup(bot: Nightcore) -> None:
    """Setup the Voteban cog."""
    await bot.add_cog(Voteban(bot))
