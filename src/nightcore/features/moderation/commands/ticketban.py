"""Ticket ban command for the Nightcore bot."""

import logging
from datetime import timezone
from typing import cast

import discord
from discord import Guild, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.infra.db.operations import (
    get_moderation_access_roles,
    get_or_create_user,
    is_user_ticketbanned,
    set_user_field_upsert,
)
from src.nightcore.bot import Nightcore
from src.nightcore.components.embed import (
    EntityNotFoundEmbed,
    ErrorEmbed,
    MissingPermissionsEmbed,
    SuccessMoveEmbed,
    ValidationErrorEmbed,
)
from src.nightcore.exceptions import FieldNotConfiguredError
from src.nightcore.features.moderation.events import UserMutedEventData
from src.nightcore.features.moderation.utils import (
    compare_top_roles,
    parse_duration,
)
from src.nightcore.utils import (
    ensure_member_exists,
    has_any_role_from_sequence,
)

logger = logging.getLogger(__name__)


class Ticketban(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @app_commands.command(
        name="ticketban", description="Ban a user from creating tickets"
    )
    @app_commands.describe(
        user="The user to ban", reason="The reason for banning the user"
    )
    async def ticketban(
        self,
        interaction: Interaction,
        user: discord.User,
        duration: str,
        reason: str,
    ):
        """Ban a user from creating tickets."""
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

            try:
                u, _ = await get_or_create_user(
                    session, guild_id=guild.id, user_id=member.id
                )
                if u.ticket_ban or await is_user_ticketbanned(
                    session, guild_id=guild.id, user_id=member.id
                ):
                    return await interaction.response.send_message(
                        embed=ValidationErrorEmbed(
                            "This user is already ticket banned.",
                            self.bot.user.name,  # type: ignore
                            self.bot.user.display_avatar.url,  # type: ignore
                        ),
                        ephemeral=True,
                    )
            except Exception as e:
                logger.error(
                    "Failed to ticketban user %s in guild %s: %s",
                    user.id,
                    guild.id,
                    e,
                )
                return await interaction.response.send_message(
                    embed=ErrorEmbed(
                        "Ticketban Failed",
                        "Failed to ticketban the user. ",
                        self.bot.user.name,  # type: ignore
                        self.bot.user.display_avatar.url,  # type: ignore
                    )
                )

            try:
                await set_user_field_upsert(
                    session,
                    guild_id=guild.id,
                    user_id=member.id,
                    field="ticket_ban",
                    value=True,
                )

            except Exception as e:
                logger.error(
                    "Failed to ticketban user %s in guild %s: %s",
                    user.id,
                    guild.id,
                    e,
                )
                return await interaction.response.send_message(
                    embed=ErrorEmbed(
                        "Ticketban Failed",
                        "Failed to ticketban the user. ",
                        self.bot.user.name,  # type: ignore
                        self.bot.user.display_avatar.url,  # type: ignore
                    )
                )

        await interaction.response.defer()

        try:
            self.bot.dispatch(
                "user_ticketbanned",
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
                ),
            )
        except Exception as e:
            logger.exception(
                "[event] - Failed to dispatch user_muted event: %s", e
            )
            return

        await interaction.followup.send(
            embed=SuccessMoveEmbed(
                "User Ticketbanned",
                f"{member.mention} has been ticketbanned by moderator {interaction.user.mention}",  # noqa: E501
                self.bot.user.name,  # type: ignore
                self.bot.user.display_avatar.url,  # type: ignore
            )
            .add_field(name="Reason", value=reason, inline=True)
            .add_field(name="Duration", value=duration, inline=True)
        )

        logger.info(
            "[command] - invoked user=%s guild=%s target=%s reason=%s duration=%s",  # noqa: E501
            interaction.user.id,
            guild.id,
            user.id,
            reason,
            duration,
        )


async def setup(bot: Nightcore):
    """Setup the Ticketban cog."""
    await bot.add_cog(Ticketban(bot))
