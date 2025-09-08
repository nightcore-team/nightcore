"""Mute command for the Nightcore bot."""

import logging
from datetime import timezone
from typing import cast

import discord
from discord import Guild, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.infra.db.models import GuildModerationConfig
from src.nightcore.bot import Nightcore
from src.nightcore.components import (
    EntityNotFoundEmbed,
    ErrorEmbed,
    MissingPermissionsEmbed,
    SuccessMoveEmbed,
    ValidationErrorEmbed,
)
from src.nightcore.exceptions import FieldNotConfiguredError
from src.nightcore.features.moderation.components import BanFormModal
from src.nightcore.features.moderation.events import UserBannedEventData
from src.nightcore.features.moderation.utils import (
    calculate_end_time,
    compare_top_roles,
    parse_duration,
)
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils import ensure_member_exists

logger = logging.getLogger(__name__)


class Ban(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @app_commands.command(name="ban", description="Ban a user on the server")
    @app_commands.describe(
        user="The user to ban", reason="The reason for banning the user"
    )
    async def ban(
        self,
        interaction: Interaction,
        user: discord.User,
        duration: str,
        reason: str,
    ):
        """Mute a user in the server."""
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

        has_moder_role = any(
            interaction.user.get_role(role_id)  # type: ignore
            for role_id in moderation_access_roles
        )
        has_ban_role = any(
            interaction.user.get_role(role_id)  # type: ignore
            for role_id in ban_access_roles
        )
        if not has_moder_role:
            return await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )
        if not has_ban_role:
            return await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        is_member_moderator = any(
            member.get_role(role_id) for role_id in moderation_access_roles
        )
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

        if not guild.me.guild_permissions.ban_members:
            return await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                    "I do not have permission to ban members.",
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
                    "Invalid duration format.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        end_time = calculate_end_time(parsed_duration)

        await interaction.response.defer(thinking=True)

        try:
            await guild.fetch_ban(member)
        except discord.NotFound:
            # not banned yet, we can ban
            try:
                await guild.ban(member, reason=reason, delete_message_days=0)
            except discord.HTTPException as e:
                logger.exception(
                    "Failed to ban user=%s guild=%s: %s",
                    member.id,
                    guild.id,
                    e,
                )
                return await interaction.followup.send(
                    embed=ErrorEmbed(
                        "User Ban Failed",
                        "Failed to ban user.",
                        self.bot.user.name,  # type: ignore
                        self.bot.user.display_avatar.url,  # type: ignore
                    )
                )
            else:
                await interaction.followup.send(
                    embed=SuccessMoveEmbed(
                        "User Banned",
                        f"{member.mention} has been banned by moderator {interaction.user.mention}",  # noqa: E501
                        self.bot.user.name,  # type: ignore
                        self.bot.user.display_avatar.url,  # type: ignore
                    )
                    .add_field(name="Reason", value=reason, inline=True)
                    .add_field(name="Duration", value=duration, inline=True)
                )
        else:
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "User is already banned.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                )
            )

        try:
            self.bot.dispatch(
                "user_banned",
                data=UserBannedEventData(
                    category=self.__class__.__name__.lower(),
                    moderator=interaction.user,  # type: ignore
                    user=member,
                    reason=reason,
                    created_at=discord.utils.utcnow().astimezone(
                        tz=timezone.utc
                    ),
                    duration=parsed_duration,
                    original_duration=duration,
                    end_time=end_time,  # type: ignore
                ),
            )
        except Exception as e:
            logger.exception(
                "[event] - Failed to dispatch user_banned event: %s", e
            )
            return

        logger.info(
            "[command] - invoked user=%s guild=%s target=%s reason=%s",
            interaction.user.id,
            guild.id,
            user.id,
            reason,
        )


async def _ban_request_callback(
    interaction: Interaction, user: discord.Member
):
    """Callback for the ban request context menu."""
    guild = cast(Guild, interaction.guild)

    # Ensure we have a guild Member object
    member = await ensure_member_exists(guild, user)
    client = cast(Nightcore, interaction.client)

    if member is None:
        return await interaction.response.send_message(
            embed=EntityNotFoundEmbed(
                "user",
                client.user.name,  # type: ignore
                client.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    async with specified_guild_config(
        client,
        guild.id,
        GuildModerationConfig,
        _create=False,
    ) as (guild_config, _):
        if not (
            moderation_access_roles := guild_config.moderation_access_roles_ids
        ):
            raise FieldNotConfiguredError("moderation access")

        if not (
            ban_request_channel_id := guild_config.send_ban_request_channel_id
        ):
            raise FieldNotConfiguredError("ban request channel")

        if not (ban_access_roles := guild_config.ban_access_roles_ids):
            raise FieldNotConfiguredError("ban access")

        ban_request_ping_role_id = guild_config.ban_request_ping_role_id

    has_moder_role = any(
        interaction.user.get_role(role_id)  # type: ignore
        for role_id in moderation_access_roles
    )
    if not has_moder_role:
        return await interaction.response.send_message(
            embed=MissingPermissionsEmbed(
                client.user.name,  # type: ignore
                client.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    is_member_moderator = any(
        member.get_role(role_id) for role_id in moderation_access_roles
    )
    if is_member_moderator:
        return await interaction.response.send_message(
            embed=ValidationErrorEmbed(
                "You cannot ban moderators.",
                client.user.name,  # type: ignore
                client.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if member.guild_permissions.administrator:
        return await interaction.response.send_message(
            embed=ValidationErrorEmbed(
                "You cannot ban administrators.",
                client.user.name,  # type: ignore
                client.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if not guild.me.guild_permissions.ban_members:
        return await interaction.response.send_message(
            embed=MissingPermissionsEmbed(
                client.user.name,  # type: ignore
                client.user.display_avatar.url,  # type: ignore
                "I do not have permission to ban members.",
            ),
            ephemeral=True,
        )

    if guild.me == member:
        return await interaction.response.send_message(
            embed=ValidationErrorEmbed(
                "You cannot ban me.",
                client.user.name,  # type: ignore
                client.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if not compare_top_roles(guild, member):
        return await interaction.response.send_message(
            embed=MissingPermissionsEmbed(
                client.user.name,  # type: ignore
                client.user.display_avatar.url,  # type: ignore
                "I cannot ban this user because he has a higher role than me.",
            ),
            ephemeral=True,
        )

    role = None
    if ban_request_ping_role_id:
        role = guild.get_role(ban_request_ping_role_id)
        if role is None:
            try:
                role = await guild.fetch_role(ban_request_ping_role_id)
            except discord.NotFound:
                role = None

    channel = guild.get_channel(ban_request_channel_id)
    if channel is None:
        try:
            channel = await guild.fetch_channel(ban_request_channel_id)  # type: ignore
            if not isinstance(channel, discord.TextChannel | discord.Thread):
                logger.warning(
                    "[ban_request_callback] channel %s not messageable (%s)",
                    channel.id,  # type: ignore
                    type(channel).__name__,
                )
                return await interaction.response.send_message(
                    embed=ValidationErrorEmbed(
                        "Channel's type must be a TextChannel or Thread",
                        client.user.name,  # type: ignore
                        client.user.display_avatar.url,  # type: ignore
                    )
                )
        except discord.NotFound:
            return await interaction.response.send_message(
                embed=EntityNotFoundEmbed(
                    "channel",
                    client.user.name,  # type: ignore
                    client.user.display_avatar.url,  # type: ignore
                )
            )

    modal = BanFormModal(
        target=user,
        moderator=interaction.user,  # type: ignore
        bot=client,
        ping_role=role,
        channel=channel,  # type: ignore
        ban_access_roles_ids=ban_access_roles,
    )

    await interaction.response.send_modal(modal)

    logger.info(
        "[command] - invoked user=%s guild=%s target=%s",
        interaction.user.id,
        guild.id,
        user.id,
    )


async def setup(bot: Nightcore):
    """Setup the Ban cog."""
    bot.tree.add_command(
        app_commands.ContextMenu(
            name="Send Ban Request",
            callback=_ban_request_callback,
        )
    )
    await bot.add_cog(Ban(bot))
