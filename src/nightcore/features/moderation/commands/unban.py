"""UnBan command for the Nightcore bot."""

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, cast

import discord
from discord import Guild, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.nightcore.components.embed import (
    ErrorEmbed,
    MissingPermissionsEmbed,
    SuccessMoveEmbed,
    ValidationErrorEmbed,
)
from src.nightcore.features.moderation.events import UnPunishEventData

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.utils.permissions import check_required_permissions, PermissionsFlagEnum

logger = logging.getLogger(__name__)


class UnBan(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

    @app_commands.command( # type: ignore
        name="unban", description="Разбанить пользователя на сервере"
    )
    @app_commands.describe(
        user="Пользователь для разбана", reason="Причина разбана пользователя"
    )
    @check_required_permissions(PermissionsFlagEnum.BAN_ACCESS) # type: ignore
    async def unban(
        self,
        interaction: Interaction,
        user: discord.User,
        reason: str,
    ):
        """Unban a user in the server."""
        guild = cast(Guild, interaction.guild)

        if not guild.me.guild_permissions.ban_members:
            return await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                    "У меня нет прав на разбан участников.",
                ),
                ephemeral=True,
            )

        if guild.me == user:
            return await interaction.response.send_message(
                embed=ValidationErrorEmbed(
                    "Вы не можете разбанить меня.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        try:
            await guild.fetch_ban(user)
        except discord.NotFound:
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Пользователь не забанен",
                    f"<@{user.id}> не забанен на этом сервере.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )
        else:
            try:
                await guild.unban(user, reason=reason)
            except discord.HTTPException as e:
                logger.exception("Failed to unban user: %s", e)
                return await interaction.response.send_message(
                    embed=ErrorEmbed(
                        "Ошибка разбана",
                        f"Не удалось разбанить <@{user.id}>.",
                        self.bot.user.name,  # type: ignore
                        self.bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )

        await interaction.response.defer(thinking=True)

        await interaction.followup.send(
            embed=SuccessMoveEmbed(
                "Пользователь разбанен",
                f"<@{user.id}> был разбанен модератором {interaction.user.mention}",  # noqa: E501
                self.bot.user.name,  # type: ignore
                self.bot.user.display_avatar.url,  # type: ignore
            ).add_field(name="Причина", value=reason, inline=True)
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


async def setup(bot: "Nightcore"):
    """Setup the UnBan cog."""
    await bot.add_cog(UnBan(bot))
