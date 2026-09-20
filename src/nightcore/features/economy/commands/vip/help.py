"""Command to get information about VIP-statuses."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild
from discord.interactions import Interaction

from src.infra.db.operations import get_guild_vip_statuses
from src.nightcore.features.economy._groups import vip as vip_group
from src.nightcore.features.economy.components.v2 import VipStatusHelpViewV2
from src.nightcore.features.economy.utils.pages import (
    build_vip_statuses_help_pages,
)
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


@vip_group.command(
    name="help", description="Узнать информацию о VIP-статусах."
)  # type: ignore
@check_required_permissions(PermissionsFlagEnum.NONE)
async def case_help(
    interaction: Interaction["Nightcore"],
):
    """Get information about VIP-statuses."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)

    async with bot.uow.start() as session:
        vip_statuses = await get_guild_vip_statuses(session, guild_id=guild.id)

    pages = build_vip_statuses_help_pages(vip_statuses)

    view = VipStatusHelpViewV2(bot=bot, pages=pages)

    await interaction.response.send_message(view=view, ephemeral=True)

    logger.info(
        "[command] - invoked user=%s guild=%s",
        interaction.user.id,
        guild.id,
    )
