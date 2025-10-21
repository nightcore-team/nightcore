"""Autocomplete utils for clans feature."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, app_commands
from discord.interactions import Interaction

from src.infra.db.operations import get_clans

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


async def clans_autocomplete(
    interaction: Interaction["Nightcore"],
    current: str,
) -> list[app_commands.Choice[str]]:
    """Autocomplete function to get fraction roles for the guild."""
    guild = cast(Guild, interaction.guild)

    async with interaction.client.uow.start() as session:
        clans = await get_clans(session, guild_id=guild.id)

    result: list[app_commands.Choice[str]] = []
    for clan in clans:
        result.append(app_commands.Choice(name=clan.name, value=str(clan.id)))

    return result
