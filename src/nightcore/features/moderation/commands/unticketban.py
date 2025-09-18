"""UnBan command for the Nightcore bot."""

import logging
from datetime import datetime, timezone
from typing import cast

import discord
from discord import Guild, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.infra.db.models import GuildModerationConfig
from src.infra.db.operations import set_user_field_upsert
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


class Unticketban(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @app_commands.command(
        name="unticketban", description="Unticketban a user in the server"
    )
    @app_commands.describe(
        user="The user to unban", reason="The reason for unbanning the user"
    )
    async def unticketban(
        self,
        interaction: Interaction,
        user: discord.User,
        reason: str,
    ):
        """Unban a user in the server."""
        guild = cast(Guild, interaction.guild)

        if guild.me == user:
            return await interaction.response.send_message(
                embed=ValidationErrorEmbed(
                    "You cannot unban me.",
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
        ) as (guild_config, session):
            if not (
                moderation_access_roles
                := guild_config.moderation_access_roles_ids
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

            try:
                await set_user_field_upsert(
                    session,
                    guild_id=guild.id,
                    user_id=user.id,
                    field="ticket_ban",
                    value=False,
                )
            except Exception as e:
                logger.exception(
                    "Failed to unticketban user=%s in guild=%s: %s",
                    user.id,
                    guild.id,
                    e,
                )
                return await interaction.response.send_message(
                    embed=ErrorEmbed(
                        "Unticketban Failed",
                        "Failed to unticketban user. ",
                        self.bot.user.name,  # type: ignore
                        self.bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )
        await interaction.response.defer(thinking=True)

        await interaction.followup.send(
            embed=SuccessMoveEmbed(
                "User Unticketbanned",
                f"<@{user.id}> has been unticketbanned by moderator {interaction.user.mention}",  # noqa: E501
                self.bot.user.name,  # type: ignore
                self.bot.user.display_avatar.url,  # type: ignore
            ).add_field(name="Reason", value=reason, inline=True)
        )

        try:
            self.bot.dispatch(
                "user_unticketbanned",
                data=UnPunishEventData(
                    category="ticketban",
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
                "[event] - Failed to dispatch user_unticketbanned event: %s", e
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
    """Setup the Unticketban cog."""
    await bot.add_cog(Unticketban(bot))
