"""Command to get information about cases."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild
from discord.interactions import Interaction

from src.infra.db.operations import get_guild_cases
from src.nightcore.components.embed import (
    ErrorEmbed,
)
from src.nightcore.features.economy._groups import case as case_group
from src.nightcore.features.economy.components.v2 import CaseHelpViewV2
from src.nightcore.features.economy.utils.pages import build_cases_help_pages
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

    outcome = ""
    coin_name = ""

    async with bot.uow.start() as session:
        try:
            cases = await get_guild_cases(session, guild_id=guild.id)
        except Exception as e:
            logger.error(
                "[case/help] Failed to get cases for guild %s: %s",
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
        pages = build_cases_help_pages(cases, coin_name)  # type: ignore

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
