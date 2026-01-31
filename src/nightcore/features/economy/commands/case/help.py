"""Command to get information about cases."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild
from discord.interactions import Interaction

from src.infra.db.models.guild import GuildEconomyConfig
from src.infra.db.operations import get_guild_cases
from src.nightcore.features.economy._groups import case as case_group
from src.nightcore.features.economy.components.v2 import CaseHelpViewV2
from src.nightcore.features.economy.utils.case import format_cases_rewards
from src.nightcore.features.economy.utils.pages import build_cases_help_pages
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


@case_group.command(name="help", description="Узнать информацию о кейсах")  # type: ignore
@check_required_permissions(PermissionsFlagEnum.NONE)
async def open_case(
    interaction: Interaction["Nightcore"],
):
    """Get information about cases."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)

    async with specified_guild_config(
        bot,
        guild_id=guild.id,
        config_type=GuildEconomyConfig,
        _create=False,
    ) as (
        guild_config,
        session,
    ):
        coin_name = (
            guild_config.coin_name if guild_config.coin_name else "коины"
        )
        cases = await get_guild_cases(session, guild_id=guild.id)

        await format_cases_rewards(
            session, cases=cases, coin_name=coin_name, guild=guild
        )

    pages = build_cases_help_pages(cases)

    view = CaseHelpViewV2(
        bot=bot,
        pages=pages,
    )

    await interaction.response.send_message(view=view, ephemeral=True)

    logger.info(
        "[command] - invoked user=%s guild=%s",
        interaction.user.id,
        guild.id,
    )
