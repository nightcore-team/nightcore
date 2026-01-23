"""Command to change moderator's stats."""

import logging
from typing import TYPE_CHECKING, cast

import discord
from discord import Guild, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.infra.db.models import (
    ChangeStat as ChangeStatGM,
)
from src.infra.db.models import (
    GuildModerationConfig,
)
from src.infra.db.models._enums import ChangeStatTypeEnum
from src.nightcore.components.embed import (
    ErrorEmbed,
    SuccessMoveEmbed,
    ValidationErrorEmbed,
)
from src.nightcore.exceptions import FieldNotConfiguredError
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils import (
    has_any_role,
)
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


class ChangeStat(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

    @app_commands.command(  # type: ignore
        name="changestat", description="Изменить статистику модератора"
    )
    @app_commands.describe(
        moderator="Модератор, чью статистику нужно изменить.",
        type="Тип статистики для изменения.",
        amount="Количество для изменения (положительное или отрицательное число).",  # noqa: E501
        reason="Причина изменения статистики.",
    )
    @app_commands.choices(
        type=[
            app_commands.Choice(name="Ban", value="ban"),
            app_commands.Choice(name="Kick", value="kick"),
            app_commands.Choice(name="Mute", value="mute"),
            app_commands.Choice(name="MPmute", value="mpmute"),
            app_commands.Choice(name="Vmute", value="vmute"),
            app_commands.Choice(name="Ticket", value="ticket"),
            app_commands.Choice(name="Ticketban", value="ticketban"),
            app_commands.Choice(name="Role Remove", value="role_remove"),
            app_commands.Choice(name="Role Accept", value="role_accept"),
            app_commands.Choice(name="Notify", value="notify"),
        ]
    )
    @app_commands.guild_only()
    @check_required_permissions(PermissionsFlagEnum.HEAD_MODERATION_ACCESS)  # type: ignore
    async def changestat(
        self,
        interaction: Interaction,
        moderator: discord.Member,
        type: app_commands.Choice[str],
        amount: float,
        reason: str,
    ):
        """Change moderator's stat."""
        guild = cast(Guild, interaction.guild)

        try:
            amount = float(amount)
        except ValueError as e:
            logger.error("[command] - Invalid amount: %s", e)
            return await interaction.response.send_message(
                embed=ValidationErrorEmbed(
                    "Пожалуйста, укажите корректное число.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        async with specified_guild_config(
            self.bot, guild.id, GuildModerationConfig
        ) as (guild_config, _):
            moderation_access_roles_ids = (
                guild_config.moderation_access_roles_ids
            )
            if not moderation_access_roles_ids:
                raise FieldNotConfiguredError("доступ к модерации")

            trackable_moderation_role = (
                guild_config.trackable_moderation_role_id
            )
            if not trackable_moderation_role:
                raise FieldNotConfiguredError("отслеживаемая роль модерации")

        is_member_moderator = has_any_role(
            moderator, trackable_moderation_role
        )
        if not is_member_moderator:
            return await interaction.response.send_message(
                embed=ValidationErrorEmbed(
                    "Этот пользователь не является модератором для получения статистики.",  # noqa: E501
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        outcome = ""
        async with self.bot.uow.start() as session:
            try:
                cs = ChangeStatGM(
                    guild_id=guild.id,
                    moderator_id=moderator.id,
                    type=ChangeStatTypeEnum(type.value),
                    amount=amount,
                    reason=reason,
                    time_now=discord.utils.utcnow(),
                )
                session.add(cs)

                outcome = "success"
            except Exception as e:
                logger.error(
                    "[changestat] - Failed to change stat for moderator %s in guild %s: %s",  # noqa: E501
                    moderator.id,
                    guild.id,
                    e,
                )
                outcome = "changestat_failed"

        if outcome == "changestat_failed":
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка изменения статистики",
                    "Не удалось изменить статистику модератора.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if outcome == "success":
            return await interaction.response.send_message(
                embed=SuccessMoveEmbed(
                    "Статистика модератора успешно изменена",
                    f"Статистика модератора {moderator.mention} была изменена: {type.name}, {amount}.",  # noqa: E501
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        logger.info(
            "[command] - invoked user=%s guild=%s moderator=%s type=%s reason=%s amount=%s",  # noqa: E501
            interaction.user.id,
            guild.id,
            moderator.id,
            type.value,
            reason,
            amount,
        )


async def setup(bot: "Nightcore"):
    """Setup the ChangeStat cog."""
    await bot.add_cog(ChangeStat(bot))
