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
from src.nightcore.features.moderation.events import UserMutedEventData
from src.nightcore.features.moderation.utils import (
    calculate_end_time,
    compare_top_roles,
    parse_duration,
)
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils import ensure_member_exists

logger = logging.getLogger(__name__)


class Mute(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @app_commands.command(name="mute", description="Mute a user in the server")
    @app_commands.describe(
        user="The user to mute", reason="The reason for muting the user"
    )
    async def mute(
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
            moderation_access_roles = cast(
                list[int], guild_config.moderation_access_roles_ids
            )

        mute_type = guild_config.mute_type

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

        is_member_moderator = any(
            member.get_role(role_id) for role_id in moderation_access_roles
        )
        if is_member_moderator:
            return await interaction.response.send_message(
                embed=ValidationErrorEmbed(
                    "You cannot mute moderators.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if not guild.me.guild_permissions.moderate_members:
            return await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                    "I do not have permission to mute members.",
                ),
                ephemeral=True,
            )

        if guild.me == member:
            return await interaction.response.send_message(
                embed=ValidationErrorEmbed(
                    "You cannot mute me.",
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
                    "I cannot mute this user because he has a higher role than me.",  # noqa: E501
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

        match mute_type:
            case "role":
                mute_role = guild_config.mute_role_id
                if not mute_role or not (mrole := guild.get_role(mute_role)):
                    return await interaction.followup.send(
                        embed=ValidationErrorEmbed(
                            "Mute role is not set.",
                            self.bot.user.name,  # type: ignore
                            self.bot.user.display_avatar.url,  # type: ignore
                        )
                    )

                member_roles = {r.id for r in member.roles}
                has_role = mute_role in member_roles

                if not has_role:
                    try:
                        await member.add_roles(mrole, reason=reason)
                    except Exception as e:
                        logger.exception("Failed to add role: %s", e)
                        return await interaction.followup.send(
                            embed=ErrorEmbed(
                                "Role Assignment Failed",
                                "Failed to add role.",
                                self.bot.user.name,  # type: ignore
                                self.bot.user.display_avatar.url,  # type: ignore
                            ),
                        )
                else:
                    return await interaction.followup.send(
                        embed=ErrorEmbed(
                            "User Mute Failed",
                            f"{member.mention} already has mute.",
                            self.bot.user.name,  # type: ignore
                            self.bot.user.display_avatar.url,  # type: ignore
                        ),
                        ephemeral=True,
                    )

            case "timeout":
                try:
                    if not member.timed_out_until:
                        await member.timeout(end_time, reason=reason)
                    else:
                        return await interaction.followup.send(
                            embed=ErrorEmbed(
                                "User Mute Failed",
                                f"{member.mention} is already timed out.",
                                self.bot.user.name,  # type: ignore
                                self.bot.user.display_avatar.url,  # type: ignore
                            ),
                        )

                except Exception as e:
                    logger.exception("Failed to timeout member: %s", e)
                    return await interaction.followup.send(
                        embed=ErrorEmbed(
                            "User Timeout Failed",
                            "Failed to timeout user.",
                            self.bot.user.name,  # type: ignore
                            self.bot.user.display_avatar.url,  # type: ignore
                        )
                    )
            case _:
                return await interaction.followup.send(
                    embed=ErrorEmbed(
                        "Invalid Mute Type",
                        "Mute type must be 'role' or 'timeout'.",
                        self.bot.user.name,  # type: ignore
                        self.bot.user.display_avatar.url,  # type: ignore
                    ),
                )

        await interaction.followup.send(
            embed=SuccessMoveEmbed(
                "User Muted",
                f"{member.mention} has been muted by moderation {interaction.user.mention}",  # noqa: E501
                self.bot.user.name,  # type: ignore
                self.bot.user.display_avatar.url,  # type: ignore
            )
            .add_field(name="Reason", value=reason, inline=True)
            .add_field(name="Duration", value=duration, inline=True)
        )

        try:
            self.bot.dispatch(
                "user_muted",
                data=UserMutedEventData(
                    category=self.__class__.__name__.lower(),
                    moderator=interaction.user,  # type: ignore
                    user=member,
                    reason=reason,
                    created_at=discord.utils.utcnow().astimezone(
                        tz=timezone.utc
                    ),
                    duration=parsed_duration,
                    original_duration=duration,
                    mute_type=mute_type,
                    end_time=end_time,  # type: ignore
                ),
            )
        except Exception as e:
            logger.exception(
                "[event] - Failed to dispatch user_muted event: %s", e
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
    """Setup the Mute cog."""
    await bot.add_cog(Mute(bot))
