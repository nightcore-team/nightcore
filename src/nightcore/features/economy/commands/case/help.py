"""Command to get information about cases."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild
from discord.interactions import Interaction

from src.infra.db.models import GuildEconomyConfig
from src.nightcore.components.embed import (
    ErrorEmbed,
)
from src.nightcore.features.economy._groups import case as case_group
from src.nightcore.features.economy.components.v2 import CaseHelpViewV2
from src.nightcore.services.config import specified_guild_config

from src.nightcore.utils.permissions import PermissionsFlagEnum, check_required_permissions

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


@case_group.command(name="help", description="Узнать информацию о кейсах") # type: ignore
@check_required_permissions(PermissionsFlagEnum.NONE)
async def open_case(
    interaction: Interaction["Nightcore"],
):
    """Get information about cases."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)

    outcome = ""
    coin_name = ""
    coin_drop = []
    color_drop = {}

    async with specified_guild_config(
        bot, guild_id=guild.id, config_type=GuildEconomyConfig
    ) as (guild_config, _):
        try:
            coin_drop = guild_config.drop_from_coins_case
            color_drop = guild_config.drop_from_colors_case
            coin_name = guild_config.coin_name
        except Exception as e:
            logger.error(
                "[case/help] Failed to get guild economy config for guild %s: %s",  # noqa: E501
                guild.id,
                e,
            )
            outcome = "error"

        if not outcome:
            outcome = "success"

    if outcome == "error":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка получения информации",
                "не удалось получить информацию о кейсах.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            )
        )

    if outcome == "success":
        view = CaseHelpViewV2(
            bot=bot,
            coin_name=coin_name,
            coins_drops=coin_drop,
            colors_drops=color_drop,
        )

        await interaction.response.send_message(view=view, ephemeral=True)

    logger.info(
        "[command] - invoked user=%s guild=%s",
        interaction.user.id,
        guild.id,
    )
