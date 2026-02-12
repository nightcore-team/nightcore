"""Autocomplete utils for custom components feature."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, cast

from discord import Guild, app_commands
from discord.interactions import Interaction

from src.infra.db.operations import get_custom_components

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


async def components_autocomplete(
    interaction: Interaction[Nightcore],
    current: str,
) -> list[app_commands.Choice[str]]:
    """Autocomplete function to get custom components for the guild."""

    start_autocomplete = time.perf_counter()
    guild = cast(Guild, interaction.guild)

    async with interaction.client.uow.start() as session:
        components = await get_custom_components(session, guild_id=guild.id)

    result: list[app_commands.Choice[str]] = []
    for cmp in components[:25]:
        logger.info(
            "[components/autocomplete] Found component with name %s (len: %d) and id %s for guild %s",  # noqa: E501
            cmp.name,
            len(cmp.name),
            cmp.id,
            guild.id,
        )
        result.append(app_commands.Choice(name=cmp.name, value=str(cmp.id)))

    end_autocomplete = time.perf_counter()
    logger.info(
        "[components/autocomplete] Autocomplete for guild %s took %.4f seconds ",  # noqa: E501
        guild.id,
        end_autocomplete - start_autocomplete,
    )

    return result
