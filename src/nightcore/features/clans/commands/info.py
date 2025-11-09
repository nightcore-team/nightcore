"""Clan deletion command."""

import logging
import time
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
    name="info", description="Посмотреть актуальную информацию о клане."
)
@app_commands.describe(clan="Клан, информацию о котором вы хотите посмотреть.")
@app_commands.autocomplete(clan=clans_autocomplete)
async def info(interaction: Interaction["Nightcore"], clan: str):
    """Get information about a clan."""

    start_time = time.perf_counter()

    bot = interaction.client
    guild = cast(Guild, interaction.guild)
    clan_id = int(clan)

    async with bot.uow.start() as session:
        dbclan = await get_clan_by_id(
            session, guild_id=guild.id, clan_id=clan_id
        )

    if not dbclan:
        await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка получения информации о клане",
                "Не удалось найти данный клан в базе данных.",
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

    end_time = time.perf_counter()
    logger.info(
        "[clans/info] Info command for clan %s took %.4f seconds",
        clan_id,
        end_time - start_time,
    )

    start_time = time.perf_counter()
    await interaction.response.send_message(view=view, ephemeral=True)
    end_time = time.perf_counter()
    logger.info(
        "[clans/info] Sending info response message for clan %s took %.4f seconds",  # noqa: E501
        clan_id,
        end_time - start_time,
    )
