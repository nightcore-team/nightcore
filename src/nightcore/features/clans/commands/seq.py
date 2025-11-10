"""Command to list clans."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild
from discord.interactions import Interaction

from src.infra.db.operations import get_clans
from src.nightcore.components.embed import ErrorEmbed
from src.nightcore.features.clans._groups import clan as clan_main_group
from src.nightcore.features.clans.components.v2 import ClanListViewV2

from src.nightcore.utils.permissions import PermissionsFlagEnum, check_required_permissions

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


@clan_main_group.command( # type: ignore
    name="list", description="Посмотреть список всех кланов"
)
@check_required_permissions(PermissionsFlagEnum.NONE)
async def list_clans(interaction: Interaction["Nightcore"]):
    """Get a list of all clans."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)

    async with bot.uow.start() as session:
        # get all clans
        dbclans = await get_clans(session, guild_id=guild.id)

    if not dbclans:
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка получения списка кланов",
                "Список кланов пуст.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    view = ClanListViewV2(bot=bot, clans=dbclans)

    await interaction.response.send_message(view=view, ephemeral=True)

    logger.info(
        "[command] - invoked user=%s guild=%s total_clans=%s",
        interaction.user.id,
        guild.id,
        len(dbclans),
    )
