"""UnBan command for the Nightcore bot."""

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

import discord
from discord import Guild, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.nightcore.components.embed import (
    ErrorEmbed,
    MissingPermissionsEmbed,
)
from src.nightcore.features.moderation.components.v2 import PunishViewV2
from src.nightcore.features.moderation.events import UnPunishEventData
from src.nightcore.features.moderation.utils.transformers import (
    StringToRuleTransformer,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

logger = logging.getLogger(__name__)


class UnBan(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

    @app_commands.command(  # type: ignore
        name="unban", description="Разбанить пользователя на сервере"
    )
    @app_commands.describe(
        user="Пользователь для разбана", reason="Причина разбана пользователя"
    )
    @app_commands.guild_only()
    @check_required_permissions(PermissionsFlagEnum.BAN_ACCESS)  # type: ignore
    async def unban(
        self,
        interaction: Interaction,
        user: discord.User,
        reason: app_commands.Transform[
            app_commands.Range[str, 1, 1000], StringToRuleTransformer
        ],
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
                embed=ErrorEmbed(
                    "Ошибка снятия блокировки",
                    "Вы не можете снять блокировку с меня.",
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
                    "Ошибка снятия блокировки",
                    f"<@{user.id}> не забанен на этом сервере.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )
        else:
            try:
                self.bot.dispatch(
                    "user_unbanned",
                    data=UnPunishEventData(
                        mode="dm",
                        category="ban",
                        guild_id=guild.id,
                        moderator_id=interaction.user.id,
                        user_id=user.id,
                        reason=reason,
                        created_at=datetime.now(UTC),
                    ),
                    by_command=True,
                )
            except Exception as e:
                logger.exception(
                    "[event] - Failed to dispatch user_unbanned event: %s", e
                )
                return

            try:
                await guild.unban(user, reason=reason)
            except discord.HTTPException as e:
                logger.exception("Failed to unban user: %s", e)
                return await interaction.response.send_message(
                    embed=ErrorEmbed(
                        "Ошибка снятия блокировки",
                        f"Не удалось снять блокировку с <@{user.id}>.",
                        self.bot.user.name,  # type: ignore
                        self.bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )

        await interaction.response.defer(thinking=True)

        await interaction.followup.send(
            view=PunishViewV2(
                bot=self.bot,
                user=user,
                punish_type="unban",
                moderator_id=interaction.user.id,  # type: ignore
                reason=reason,
                mode="server",
            )
        )

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
