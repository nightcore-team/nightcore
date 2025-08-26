"""Kick command for the Nightcore bot."""

import logging
from datetime import timezone
from typing import cast

import discord
from discord import Guild, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.db.operations import get_moderation_access_roles
from src.nightcore.bot import Nightcore
from src.nightcore.components import (
    EntityNotFoundEmbed,
    MissingPermissionsEmbed,
    SuccessMoveEmbed,
    ValidationErrorEmbed,
)
from src.nightcore.features.moderation.events import UserPunishmentEventData
from src.nightcore.features.moderation.utils import compare_top_roles
from src.nightcore.utils import ensure_member_exists

logger = logging.getLogger(__name__)


class Kick(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @app_commands.command(
        name="kick", description="Kick a user from the server"
    )
    @app_commands.describe(
        user="The user to kick", reason="The reason for kicking the user"
    )
    async def kick(
        self,
        interaction: Interaction,
        user: discord.User,
        reason: str,
    ):
        """Kick a user from the server."""
        guild = cast(Guild, interaction.guild)

        async with self.bot.uow.start() as uow:
            moderation_access_roles = await get_moderation_access_roles(
                cast(AsyncSession, uow.session), guild_id=guild.id
            )
        has_moder_role = any(
            interaction.user.get_role(role_id)  # type: ignore
            for role_id in moderation_access_roles
        )
        if not has_moder_role:
            await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )
            return

        # Ensure we have a guild Member object
        member = await ensure_member_exists(guild, user)

        if member is None:
            await interaction.response.send_message(
                embed=EntityNotFoundEmbed(
                    "user",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )
            return

        if interaction.user == member:
            await interaction.response.send_message(
                embed=ValidationErrorEmbed(
                    "You cannot kick yourself.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )
            return

        is_member_moderator = any(
            member.get_role(role_id) for role_id in moderation_access_roles
        )
        if is_member_moderator:
            await interaction.response.send_message(
                embed=ValidationErrorEmbed(
                    "You cannot kick moderators.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )
            return

        if not guild.me.guild_permissions.kick_members:
            await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                    "I do not have permission to kick members.",
                ),
                ephemeral=True,
            )
            return

        if guild.me == member:
            await interaction.response.send_message(
                embed=ValidationErrorEmbed(
                    "You cannot kick me.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )
            return

        if not compare_top_roles(guild, member):
            await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                    "I cannot kick this user because he has a higher role than me.",  # noqa: E501
                ),
                ephemeral=True,
            )
            return

        await interaction.response.defer(thinking=True)

        try:
            await guild.kick(member, reason=reason)
        except Exception as e:
            logger.exception("[command] - Failed to kick user: %s", e)

        try:
            self.bot.dispatch(
                "user_punish",
                data=UserPunishmentEventData(
                    moderator=interaction.user,  # type: ignore
                    user=member,
                    category=self.__class__.__name__.lower(),
                    reason=reason,
                    created_at=discord.utils.utcnow().astimezone(
                        tz=timezone.utc
                    ),
                ),
            )
        except Exception as e:
            logger.exception(
                "[event] - Failed to dispatch user_punish event: %s", e
            )

        await interaction.followup.send(
            embed=SuccessMoveEmbed(
                "User Kicked",
                f"Successfully kicked {member.mention} from the server.",
                self.bot.user.name,  # type: ignore
                self.bot.user.display_avatar.url,  # type: ignore
            )
        )


async def setup(bot: Nightcore):
    """Setup the Kick cog."""
    await bot.add_cog(Kick(bot))
