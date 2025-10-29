"""Autocomplete utils for economy feature."""

import logging
import time
from typing import TYPE_CHECKING, cast

from discord import Guild, app_commands
from discord.interactions import Interaction

from src.infra.db.operations import get_or_create_user

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


async def cases_autocomplete(
    interaction: Interaction["Nightcore"],
    current: str,
) -> list[app_commands.Choice[str]]:
    """Autocomplete function to get cases for user."""
    start_autocomplete = time.perf_counter()
    guild = cast(Guild, interaction.guild)

    async with interaction.client.uow.start() as session:
        user, created = await get_or_create_user(
            session,
            guild_id=guild.id,
            user_id=interaction.user.id,
        )

    result: list[app_commands.Choice[str]] = []
    if created:
        result = []
    else:
        inventory = user.inventory or {}
        cases = inventory.get("cases", {})
        for case_name in cases:
            match case_name.lower():
                case "coins_case":
                    result.append(
                        app_commands.Choice(
                            name=f"Кейс с монетами, количество: {cases[case_name]}",  # noqa: E501, RUF001
                            value=case_name,
                        )
                    )
                case "colors_case":
                    result.append(
                        app_commands.Choice(
                            name=f"Кейс с цветами, количество: {cases[case_name]}",  # noqa: E501, RUF001
                            value=case_name,
                        )
                    )
                case _:
                    ...

    end_autocomplete = time.perf_counter()
    logger.info(
        "[clans/autocomplete] Autocomplete for guild %s took %.4f seconds ",
        guild.id,
        end_autocomplete - start_autocomplete,
    )

    return result
