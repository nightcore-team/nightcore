"""Subcommand to reset battlepass.

Reset all levels and points for a user.
Reset all levels and rewards in config.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild
from discord.interactions import Interaction

from src.infra.db.operations import reset_users_battlepass_levels
from src.nightcore.components.embed import (
    ErrorEmbed,
    SuccessMoveEmbed,
)
from src.nightcore.features.config._groups import (
    battlepass as battlepass_group,
)

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
@check_required_permissions(PermissionsFlagEnum.ECONOMY_CONFIG_ACCESS)
async def reset(
    interaction: Interaction[Nightcore],
):
    """Add new battle pass level."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)

    await interaction.response.defer(ephemeral=True)

    outcome = ""
    users_count = 0

    async with bot.uow.start() as session:
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

    if outcome == "success":
        msg = (
            f"Боевой пропуск успешно сброшен у {users_count} пользователей.\n"
        )

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
        "[command] - invoked user=%s guild=%s",
        interaction.user.id,
        guild.id,
    )
