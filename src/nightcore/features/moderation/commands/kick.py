"""Kick command for the Nightcore bot."""

import logging
from datetime import timezone
from typing import cast

import discord
from discord import Guild, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.infra.db.operations import get_moderation_access_roles
from src.nightcore.bot import Nightcore
from src.nightcore.components.embed import (
    EntityNotFoundEmbed,
    ErrorEmbed,
    MissingPermissionsEmbed,
    SuccessMoveEmbed,
    ValidationErrorEmbed,
)
from src.nightcore.exceptions import FieldNotConfiguredError
from src.nightcore.features.moderation.events import UserKickEventData
from src.nightcore.features.moderation.utils import compare_top_roles
from src.nightcore.utils import (
    ensure_member_exists,
    has_any_role_from_sequence,
)

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

        # Ensure we have a guild Member object
        member = await ensure_member_exists(guild, user.id)

        if member is None:
            return await interaction.response.send_message(
                embed=EntityNotFoundEmbed(
                    "user",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        async with self.bot.uow.start() as session:
            if not (
                moderation_access_roles := await get_moderation_access_roles(
                    session, guild_id=guild.id
                )
            ):
                raise FieldNotConfiguredError("moderation access")

        has_moder_role = has_any_role_from_sequence(
            cast(discord.Member, interaction.user), moderation_access_roles
        )
        if not has_moder_role:
            return await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        is_member_moderator = has_any_role_from_sequence(
            member, moderation_access_roles
        )
        if is_member_moderator:
            return await interaction.response.send_message(
                embed=ValidationErrorEmbed(
                    "You cannot kick moderators.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if not guild.me.guild_permissions.kick_members:
            return await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                    "I do not have permission to kick members.",
                ),
                ephemeral=True,
            )

        if guild.me == member:
            return await interaction.response.send_message(
                embed=ValidationErrorEmbed(
                    "You cannot kick me.",
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
                    "I cannot kick this user because he has a higher role than me.",  # noqa: E501
                ),
                ephemeral=True,
            )

        await interaction.response.defer(thinking=True)

        try:
            self.bot.dispatch(
                "user_kicked",
                data=UserKickEventData(
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
                "[event] - Failed to dispatch user_kicked event: %s", e
            )
            return

        try:
            await guild.kick(member, reason=reason)
        except Exception as e:
            logger.exception("[command] - Failed to kick user: %s", e)
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Kick Error",
                    "Failed to kick the user.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                )
            )

        await interaction.followup.send(
            embed=SuccessMoveEmbed(
                "User Kicked",
                f"Successfully kicked {member.mention} from the server.",
                self.bot.user.name,  # type: ignore
                self.bot.user.display_avatar.url,  # type: ignore
            )
        )
        logger.info(
            "[command] - invoked user=%s guild=%s target=%s reason=%s",
            interaction.user.id,
            guild.id,
            user.id,
            reason,
        )


async def setup(bot: Nightcore):
    """Setup the Kick cog."""
    await bot.add_cog(Kick(bot))
