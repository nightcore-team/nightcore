"""UnBan command for the Nightcore bot."""

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from discord import Guild, Member, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.infra.db.models import GuildModerationConfig
from src.infra.db.operations import get_or_create_user
from src.nightcore.components.embed import ErrorEmbed
from src.nightcore.features.moderation.components.v2 import PunishViewV2
from src.nightcore.features.moderation.events import UnPunishEventData
from src.nightcore.features.moderation.utils.transformers import (
    StringToRuleTransformer,
)
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


class Unrrban(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

    @app_commands.command(  # type: ignore
        name="unrrban",
        description="Снять блокировку на запрос роли с пользователя",
    )
    @app_commands.guild_only()
    @app_commands.describe(
        user="Пользователь для снятия бана", reason="Причина снятия бана"
    )
    @check_required_permissions(PermissionsFlagEnum.MODERATION_ACCESS)  # type: ignore
    async def unrrban(
        self,
        interaction: Interaction,
        user: Member,
        reason: app_commands.Transform[
            app_commands.Range[str, 1, 1000], StringToRuleTransformer
        ],
    ):
        """Unrrban a user in the server."""
        guild = cast(Guild, interaction.guild)

        if guild.me == user:
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка снятия блокировки",
                    "Вы не можете снять блокировку на запрос роли с меня.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        outcome = ""
        async with specified_guild_config(
            self.bot,
            guild.id,
            GuildModerationConfig,
        ) as (_, session):
            try:
                user_record, _ = await get_or_create_user(
                    session, guild_id=guild.id, user_id=user.id
                )
                if user_record.role_request_ban:
                    user_record.role_request_ban = False
                else:
                    outcome = "not_rrbanned"
            except Exception as e:
                logger.exception(
                    "Failed to unrrban user=%s in guild=%s: %s",
                    user.id,
                    guild.id,
                    e,
                )
                outcome = "error"

        if outcome == "not_rrbanned":
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка снятия блокировки",
                    "Данный пользователь не имеет блокировки на запрос роли.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if outcome == "error":
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка снятия блокировки",
                    "Не удалось снять блокировку на запрос роли с пользователя.",  # noqa: E501
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
                punish_type="unrrban",
                moderator_id=interaction.user.id,  # type: ignore
                reason=reason,
                mode="server",
            )
        )

        try:
            self.bot.dispatch(
                "user_unrole_request_banned",
                data=UnPunishEventData(
                    mode="dm",
                    category="rrban",
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
                "[event] - Failed to dispatch user_unrole_request_banned event: %s",  # noqa: E501
                e,
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
    """Setup the Unrrban cog."""
    await bot.add_cog(Unrrban(bot))
