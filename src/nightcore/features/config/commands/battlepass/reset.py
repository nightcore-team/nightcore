"""Subcommand to reset battlepass.

Reset all levels and points for a user.
Reset all levels and rewards in config.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, app_commands
from discord.interactions import Interaction
from sqlalchemy.orm import attributes

from src.infra.db.models import GuildEconomyConfig
from src.infra.db.operations import reset_users_battlepass_levels
from src.nightcore.components.embed import (
    ErrorEmbed,
    SuccessMoveEmbed,
)
from src.nightcore.features.config._groups import (
    battlepass as battlepass_group,
)
from src.nightcore.services.config import specified_guild_config

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

logger = logging.getLogger(__name__)


@battlepass_group.command(
    name="reset", description="Сбросить боевой пропуск у пользователей"
)  # type: ignore
@app_commands.describe(
    reset_config="Сбросить дополнительно уровни и награды боевого пропуска в конфиге сервера",  # noqa: E501
)
@check_required_permissions(PermissionsFlagEnum.ADMINISTRATOR)
async def reset(
    interaction: Interaction[Nightcore], reset_config: bool | None = False
):
    """Add new battle pass level."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)

    await interaction.response.defer(ephemeral=True)

    outcome = ""
    users_count = 0

    async with specified_guild_config(
        bot, guild.id, config_type=GuildEconomyConfig
    ) as (
        guild_config,
        session,
    ):
        # reset users' battlepass data
        try:
            users_count = await reset_users_battlepass_levels(
                session, guild_id=guild.id
            )
            if not users_count:
                users_count = 0
        except Exception as e:
            logger.error(
                "Error resetting battlepass for users in guild %s: %s",
                guild.id,
                e,
                exc_info=True,
            )
            outcome = "error_resetting_users"

        if not outcome:
            try:
                if reset_config:
                    guild_config.battlepass_rewards = []
                    attributes.flag_modified(
                        guild_config, "battlepass_rewards"
                    )
            except Exception as e:
                logger.error(
                    "Error resetting battlepass config in guild %s: %s",
                    guild.id,
                    e,
                    exc_info=True,
                )
                outcome = "error_resetting_config"

        if not outcome:
            outcome = "success"

    if outcome == "error_resetting_users":
        return await interaction.followup.send(
            embed=ErrorEmbed(
                "Ошибка сброса боевого пропуска",
                "Произошла ошибка при сбросе боевого пропуска у пользователей.",  # noqa: E501
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "error_resetting_config":
        return await interaction.followup.send(
            embed=ErrorEmbed(
                "Ошибка сброса конфигурации боевого пропуска",
                "Произошла ошибка при сбросе конфигурации боевого пропуска на сервере.",  # noqa: E501
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "success":
        msg = (
            f"Боевой пропуск успешно сброшен у {users_count} пользователей.\n"
        )
        if reset_config:
            msg += "> Конфигурация также была сброшена."

        return await interaction.followup.send(
            embed=SuccessMoveEmbed(
                "Сброс боевого пропуска",
                msg,
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    logger.info(
        "[command] - invoked user=%s guild=%s reset_config=%s",
        interaction.user.id,
        guild.id,
        reset_config,
    )
