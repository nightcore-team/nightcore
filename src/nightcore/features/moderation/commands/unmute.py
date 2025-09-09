"""Unmute command for the Nightcore bot."""

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
    EntityNotFoundEmbed,
    ErrorEmbed,
    MissingPermissionsEmbed,
    SuccessMoveEmbed,
    ValidationErrorEmbed,
)
from src.nightcore.exceptions import FieldNotConfiguredError
from src.nightcore.features.moderation.events import UserUnmutedEventData
from src.nightcore.features.moderation.utils import (
    compare_top_roles,
)
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils import ensure_member_exists

logger = logging.getLogger(__name__)


class UnMute(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @app_commands.command(
        name="unmute", description="Unmute a user in the server"
    )
    @app_commands.describe(
        user="The user to unmute", reason="The reason for unmuting the user"
    )
    async def mute(
        self,
        interaction: Interaction,
        user: discord.User,
        reason: str,
    ):
        """Unmute a user in the server."""
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

            mute_type = guild_config.mute_type
            mute_role_id = guild_config.mute_role_id

        has_moder_role = any(
            interaction.user.get_role(role_id)  # type: ignore
            for role_id in moderation_access_roles
        )
        if not has_moder_role:
            return await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if (
            not guild.me.guild_permissions.moderate_members
            or not guild.me.guild_permissions.manage_roles
        ):
            return await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                    "I do not have permission to unmute members.",
                ),
                ephemeral=True,
            )

        if guild.me == member:
            return await interaction.response.send_message(
                embed=ValidationErrorEmbed(
                    "You cannot unmute me.",
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
                    "I cannot unmute this user because he has a higher role than me.",  # noqa: E501
                ),
                ephemeral=True,
            )

        await interaction.response.defer(thinking=True)

        match mute_type:
            case "role":
                mrole = None
                if mute_role_id:
                    # Try cache first
                    mrole = guild.get_role(mute_role_id)
                    if mrole is None:
                        try:
                            mrole = await guild.fetch_role(mute_role_id)
                        except discord.NotFound:
                            mrole = None
                        except discord.HTTPException as e:
                            logger.exception(
                                "Failed to fetch mute role %s in guild %s: %s",
                                mute_role_id,
                                guild.id,
                                e,
                            )
                            mrole = None

                if not mute_role_id or mrole is None:
                    return await interaction.followup.send(
                        embed=ErrorEmbed(
                            "Mute role not found",
                            f"The mute role with ID {mute_role_id} was not found in this server.",  # noqa: E501
                            self.bot.user.name,  # type: ignore
                            self.bot.user.display_avatar.url,  # type: ignore
                        )
                    )
                else:
                    member_roles = {r.id for r in member.roles}
                    has_role = mute_role_id in member_roles

                    if not has_role:
                        return await interaction.followup.send(
                            embed=ErrorEmbed(
                                "Mute role not found",
                                "The mute role was not found in this user.",
                                self.bot.user.name,  # type: ignore
                                self.bot.user.display_avatar.url,  # type: ignore
                            )
                        )
                    else:
                        try:
                            await member.remove_roles(mrole)
                        except Exception as e:
                            logger.exception(
                                "Failed to remove mute role %s from user %s: %s",  # noqa: E501
                                mute_role_id,
                                member.id,
                                e,
                            )
                            return await interaction.followup.send(
                                embed=ErrorEmbed(
                                    "Role Removal Failed",
                                    "Failed to remove role.",
                                    self.bot.user.name,  # type: ignore
                                    self.bot.user.display_avatar.url,  # type: ignore
                                ),
                            )

            case "timeout":
                if member.is_timed_out():
                    try:
                        await member.timeout(None, reason=reason)
                    except Exception as e:
                        logger.exception(
                            "Failed to remove timeout from user %s: %s",
                            member.id,
                            e,
                        )
                        return await interaction.followup.send(
                            embed=ErrorEmbed(
                                "Timeout Removal Failed",
                                "Failed to remove timeout.",
                                self.bot.user.name,  # type: ignore
                                self.bot.user.display_avatar.url,  # type: ignore
                            ),
                        )
                else:
                    return await interaction.followup.send(
                        embed=ErrorEmbed(
                            "User Not Timed Out",
                            "The user is not currently timed out.",
                            self.bot.user.name,  # type: ignore
                            self.bot.user.display_avatar.url,  # type: ignore
                        )
                    )
            case _:
                logger.error(
                    "Unknown mute type for user %s",
                    member.id,
                )
                return await interaction.followup.send(
                    embed=ErrorEmbed(
                        "Unknown Mute Type",
                        "The specified mute type is unknown.",
                        self.bot.user.name,  # type: ignore
                        self.bot.user.display_avatar.url,  # type: ignore
                    )
                )

        await interaction.followup.send(
            embed=SuccessMoveEmbed(
                "User Unmuted",
                f"{member.mention} has been unmuted by moderator {interaction.user.mention}",  # noqa: E501
                self.bot.user.name,  # type: ignore
                self.bot.user.display_avatar.url,  # type: ignore
            ).add_field(name="Reason", value=reason, inline=True)
        )

        try:
            self.bot.dispatch(
                "user_unmute",
                data=UserUnmutedEventData(
                    category="mute",
                    mute_type="default",
                    guild_id=guild.id,
                    moderator_id=interaction.user.id,
                    user_id=member.id,
                    reason=reason,
                    created_at=datetime.now(timezone.utc),
                ),
                by_command=True,
            )
        except Exception as e:
            logger.exception(
                "[event] - Failed to dispatch user_unmuted event: %s", e
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
    """Setup the UnMute cog."""
    await bot.add_cog(UnMute(bot))
