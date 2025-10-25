"""Autocomplete utils for clans feature."""

import logging
import time
from typing import TYPE_CHECKING, Final, cast

from discord import Guild, app_commands
from discord.interactions import Interaction

from src.infra.db.models import GuildClansConfig
from src.infra.db.operations import get_clans
from src.nightcore.services.config import specified_guild_config

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


async def clans_autocomplete(
    interaction: Interaction["Nightcore"],
    current: str,
) -> list[app_commands.Choice[str]]:
    """Autocomplete function to get fraction roles for the guild."""
    start_autocomplete = time.perf_counter()
    guild = cast(Guild, interaction.guild)

    async with interaction.client.uow.start() as session:
        clans = await get_clans(session, guild_id=guild.id)

    result: list[app_commands.Choice[str]] = []
    for clan in clans:
        result.append(app_commands.Choice(name=clan.name, value=str(clan.id)))

    end_autocomplete = time.perf_counter()
    logger.info(
        "[clans/autocomplete] Autocomplete for guild %s took %.4f seconds ",
        guild.id,
        end_autocomplete - start_autocomplete,
    )

    return result


CLAN_IMPROVEMENTS: Final[list[str]] = [
    "Увеличение слотов на заместителя (+1)",
    "Увеличение слотов на участника (+10)",
    "х2 репутация за payday",  # noqa: RUF001
]


async def clans_improvements_autocomplete(
    interaction: Interaction["Nightcore"],
    current: str,
) -> list[app_commands.Choice[str]]:
    """Autocomplete function to get clan improvements for the guild."""
    guild = cast(Guild, interaction.guild)

    async with specified_guild_config(
        interaction.client, guild_id=guild.id, config_type=GuildClansConfig
    ) as (guild_config, _):
        costs = guild_config.clan_improvements

    result: list[app_commands.Choice[str]] = [
        app_commands.Choice(
            name=f"{improvement} — цена: {cost}", value=f"{i},{cost}"
        )
        for i, (improvement, cost) in enumerate(
            zip(CLAN_IMPROVEMENTS, costs, strict=False)
        )
    ]

    return result


async def clans_shop_autocomplete(
    interaction: Interaction["Nightcore"],
    current: str,
) -> list[app_commands.Choice[str]]:
    """Autocomplete function to get clan shop items for the guild."""
    guild = cast(Guild, interaction.guild)

    async with specified_guild_config(
        interaction.client, guild_id=guild.id, config_type=GuildClansConfig
    ) as (guild_config, _):
        shop_items: dict[str, float] = guild_config.clan_shop_items

    result: list[app_commands.Choice[str]] = []

    for item, price in shop_items.items():
        result.append(
            app_commands.Choice(
                name=f"{item} — цена: {price}", value=f"{item},{price}"
            )
        )

    return result
