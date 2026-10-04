"""Command to get information about badges."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild
from discord.interactions import Interaction

from src.infra.db.operations import get_badges
from src.nightcore.features.economy._groups import badge as badge_group
from src.nightcore.features.economy.components.v2 import BadgeHelpViewV2
from src.nightcore.features.economy.utils.pages import build_badge_help_pages
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


@badge_group.command(name="help", description="Узнать информацию о бейджах.")  # type: ignore
@check_required_permissions(PermissionsFlagEnum.NONE)
async def badge_help(
    interaction: Interaction["Nightcore"],
):
    """Get information about badges."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)

    async with bot.uow.start() as session:
        global_badges, guild_badges = await get_badges(
            session, guild_id=guild.id
        )

    pages = build_badge_help_pages(global_badges, guild_badges)

    view = BadgeHelpViewV2(bot=bot, pages=pages)

    await interaction.response.send_message(view=view, ephemeral=True)

    logger.info(
        "[command] - invoked user=%s guild=%s",
        interaction.user.id,
        guild.id,
    )
