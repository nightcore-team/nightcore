"""Clan deletion command."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, app_commands
from discord.interactions import Interaction

from src.infra.db.operations import get_clans
from src.nightcore.components.embed import ErrorEmbed
from src.nightcore.features.clans._groups import clan as clan_main_group
from src.nightcore.features.clans.components.v2 import ClanListViewV2

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


@clan_main_group.command(name="list", description="Get a list of all clans.")
@app_commands.describe()
async def list_clans(interaction: Interaction["Nightcore"]):
    """Get a list of all clans."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)

    async with bot.uow.start() as session:
        # get all clans
        dbclans = await get_clans(session, guild_id=guild.id)
        if not dbclans:
            await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка получения списка кланов",
                    "Список кланов пуст.",
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )
            return

    view = ClanListViewV2(bot=bot, clans=dbclans)

    await interaction.response.send_message(view=view, ephemeral=True)
