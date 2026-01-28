"""Subcommand to delete a battle pass level."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, app_commands
from discord.interactions import Interaction

from src.infra.db.operations import get_battlepass_level
from src.nightcore.components.embed import ErrorEmbed, SuccessMoveEmbed
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
    name="delete_level", description="Удалить уровень боевого пропуска"
)  # type: ignore
@app_commands.describe(
    level="Уровень, который нужно удалить",
)
@check_required_permissions(PermissionsFlagEnum.ECONOMY_CONFIG_ACCESS)
async def delete_level(
    interaction: Interaction["Nightcore"],
    level: app_commands.Range[int, 1, 1000000],
):
    """Delete battlepass level and shift others down."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)

    outcome = ""

    async with bot.uow.start() as session:
        battlepass_level = await get_battlepass_level(
            session, guild_id=guild.id, level=level
        )

        if battlepass_level is None:
            outcome = "level_not_found"
        else:
            await session.delete(battlepass_level)

            outcome = "success"

    if outcome == "level_not_found":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка удаления уровня",
                f"Уровень {level} не найден в боевом пропуске.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "success":
        return await interaction.response.send_message(
            embed=SuccessMoveEmbed(
                "Уровень удален",
                f"Уровень {level} успешно удален из боевого пропуска.\n"
                f"Последующие уровни автоматически сдвинуты вниз.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    logger.info(
        "[command] - invoked user=%s guild=%s delete_level=%s required_exp=%s reward_type=%s reward_amount=%s",  # noqa: E501
        interaction.user.id,
        guild.id,
        level,
    )
