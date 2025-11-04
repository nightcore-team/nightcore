"""Utilities for role-related operations in moderation features."""

import logging
from typing import cast

from discord import Guild, app_commands
from discord.interactions import Interaction

from src.infra.db.operations import get_fraction_roles
from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


async def fraction_roles_autocomplete(
    interaction: Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    """Autocomplete function to get fraction roles for the guild."""
    guild = cast(Guild, interaction.guild)

    async with cast(Nightcore, interaction.client).uow.start() as session:
        roles = await get_fraction_roles(session, guild_id=guild.id)

    result: list[app_commands.Choice[str]] = []
    for role_id in roles:
        role = guild.get_role(role_id)
        if role is None:
            logger.warning(
                "[event] fraction_roles_autocomplete - %s: role %s not found",
                guild.id,
                role_id,
            )
            continue

        result.append(app_commands.Choice(name=role.name, value=str(role.id)))

    return result
