"""Autocomplete utils for faq feature."""

import logging
import time
from typing import TYPE_CHECKING, cast

from discord import Guild, app_commands
from discord.interactions import Interaction

from src.infra.db.models import MainGuildConfig
from src.nightcore.services.config import specified_guild_config

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


async def faq_autocomplete(
    interaction: Interaction["Nightcore"],
    current: str,
) -> list[app_commands.Choice[str]]:
    """Autocomplete function to get faq pages for the guild."""
    start_autocomplete = time.perf_counter()
    guild = cast(Guild, interaction.guild)
    async with specified_guild_config(
        interaction.client, guild.id, MainGuildConfig
    ) as (guild_config, _):
        faq = guild_config.faq or []

    result: list[app_commands.Choice[str]] = []
    for page in faq:
        result.append(
            app_commands.Choice(name=page["title"], value=page["title"])
        )

    if not result:
        result.append(
            app_commands.Choice(
                name="Нет доступных страниц FAQ", value="no_faq_pages"
            )
        )

    end_autocomplete = time.perf_counter()
    logger.info(
        "[faq/autocomplete] Autocomplete for guild %s took %.4f seconds ",
        guild.id,
        end_autocomplete - start_autocomplete,
    )

    return result
