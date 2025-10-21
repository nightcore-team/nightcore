"""Clan deletion command."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, app_commands
from discord.interactions import Interaction

from src.infra.db.operations import get_clan_by_id
from src.nightcore.components.embed import ErrorEmbed
from src.nightcore.features.clans._groups import clan as clan_main_group
from src.nightcore.features.clans.components.v2 import ClanInfoViewV2
from src.nightcore.features.clans.utils import clans_autocomplete

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


@clan_main_group.command(
    name="info", description="Get information about a clan."
)
@app_commands.describe()
@app_commands.autocomplete(clan=clans_autocomplete)
async def info(interaction: Interaction["Nightcore"], clan: str):
    """Get information about a clan."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)
    clan_id = int(clan)

    async with bot.uow.start() as session:
        # get clan
        dbclan = await get_clan_by_id(
            session, guild_id=guild.id, clan_id=clan_id
        )
        if not dbclan:
            await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка получения информации о клане",  # noqa: RUF001
                    "Не удалось найти данный клан в базе данных.",  # noqa: RUF001
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )
            return

    view = ClanInfoViewV2(
        bot=bot,
        name=dbclan.name,
        leader_id=dbclan.leader.user_id,
        created_at=dbclan.created_at,
        deputies=[deputy.user_id for deputy in dbclan.deputies],
        lvl=dbclan.level,
        current_exp=dbclan.current_exp,
        reputation=dbclan.coins,
        members=dbclan.members,
        max_members=dbclan.max_members,
        max_deputies=dbclan.max_deputies,
        reputation_multiplier=dbclan.payday_multipler,
    )

    await interaction.response.send_message(view=view, ephemeral=True)
