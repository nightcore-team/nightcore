"""Subcommand to delete a battle pass level."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, app_commands
from discord.interactions import Interaction
from sqlalchemy.orm import attributes

from src.infra.db.models import GuildEconomyConfig
from src.nightcore.components.embed import (
    ErrorEmbed,
    SuccessMoveEmbed,
    ValidationErrorEmbed,
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
    name="delete_level", description="Удалить уровень боевого пропуска"
)  # type: ignore
@app_commands.describe(
    level="Уровень, который нужно удалить",
)
@check_required_permissions(PermissionsFlagEnum.ADMINISTRATOR)
async def delete_level(
    interaction: Interaction["Nightcore"],
    level: int,
):
    """Delete battlepass level and shift others down."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)

    try:
        int_level = int(level)
    except ValueError:
        return await interaction.response.send_message(
            embed=ValidationErrorEmbed(
                "Пожалуйста, введите действительный номер уровня.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    outcome = ""

    async with specified_guild_config(
        bot, guild.id, GuildEconomyConfig, _create=True
    ) as (
        guild_config,
        _,
    ):
        battlepass_rewards = guild_config.battlepass_rewards or []

        # found index of level to delete
        level_index = None
        for i, bp_level in enumerate(battlepass_rewards):
            if bp_level.get("level") == int_level:
                level_index = i
                break

        if level_index is None:
            outcome = "level_not_found"
        else:
            battlepass_rewards.pop(level_index)

            # moving down subsequent levels
            for i in range(level_index, len(battlepass_rewards)):
                battlepass_rewards[i]["level"] = i + 1

            guild_config.battlepass_rewards = battlepass_rewards
            attributes.flag_modified(guild_config, "battlepass_rewards")

            outcome = "success"

    if outcome == "level_not_found":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка удаления уровня",
                f"Уровень {int_level} не найден в боевом пропуске.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "success":
        return await interaction.response.send_message(
            embed=SuccessMoveEmbed(
                "Уровень удален",
                f"Уровень {int_level} успешно удален из боевого пропуска.\n"
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
