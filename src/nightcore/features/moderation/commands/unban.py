"""UnBan command for the Nightcore bot."""

import logging
from datetime import datetime, timezone
from typing import cast

import discord
from discord import Guild, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.infra.db.models import GuildModerationConfig
from src.nightcore.bot import Nightcore
from src.nightcore.components.embed import (
    ErrorEmbed,
    MissingPermissionsEmbed,
    SuccessMoveEmbed,
    ValidationErrorEmbed,
)
from src.nightcore.exceptions import FieldNotConfiguredError
from src.nightcore.features.moderation.events import UnPunishEventData
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils import has_any_role_from_sequence

logger = logging.getLogger(__name__)


class UnBan(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @app_commands.command(
        name="unban", description="Unban a user in the server"
    )
    @app_commands.describe(
        user="The user to unban", reason="The reason for unbanning the user"
    )
    async def unban(
        self,
        interaction: Interaction,
        user: discord.User,
        reason: str,
    ):
        """Unban a user in the server."""
        guild = cast(Guild, interaction.guild)

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

        has_moder_role = has_any_role_from_sequence(
            cast(discord.Member, interaction.user), moderation_access_roles
        )
        has_ban_role = has_any_role_from_sequence(
            cast(discord.Member, interaction.user), ban_access_roles
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

        if not guild.me.guild_permissions.ban_members:
            return await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                    "I do not have permission to unban members.",
                ),
                ephemeral=True,
            )

        if guild.me == user:
            return await interaction.response.send_message(
                embed=ValidationErrorEmbed(
                    "You cannot unban me.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        await interaction.response.defer(thinking=True)

        try:
            await guild.fetch_ban(user)
        except discord.NotFound:
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "User Not Banned",
                    f"<@{user.id}> is not banned in this server.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                )
            )
        else:
            try:
                await guild.unban(user, reason=reason)
            except discord.HTTPException as e:
                logger.exception("Failed to unban user: %s", e)
                return await interaction.followup.send(
                    embed=ErrorEmbed(
                        "Unban Failed",
                        f"Failed to unban <@{user.id}>.",
                        self.bot.user.name,  # type: ignore
                        self.bot.user.display_avatar.url,  # type: ignore
                    )
                )

        await interaction.followup.send(
            embed=SuccessMoveEmbed(
                "User Unbanned",
                f"<@{user.id}> has been unbanned by moderator {interaction.user.mention}",  # noqa: E501
                self.bot.user.name,  # type: ignore
                self.bot.user.display_avatar.url,  # type: ignore
            ).add_field(name="Reason", value=reason, inline=True)
        )

        try:
            self.bot.dispatch(
                "user_unbanned",
                data=UnPunishEventData(
                    category="ban",
                    guild_id=guild.id,
                    moderator_id=interaction.user.id,
                    user_id=user.id,
                    reason=reason,
                    created_at=datetime.now(timezone.utc),
                ),
                by_command=True,
            )
        except Exception as e:
            logger.exception(
                "[event] - Failed to dispatch user_unbanned event: %s", e
            )
            return

        logger.info(
            "[command] - invoked user=%s guild=%s target=%s reason=%s",
            interaction.user.id,
            guild.id,
            user.id,
            reason,
        )


async def setup(bot: Nightcore):
    """Setup the UnBan cog."""
    await bot.add_cog(UnBan(bot))
