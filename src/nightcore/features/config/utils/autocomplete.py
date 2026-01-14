"""Autocomplete utilities."""

import logging
import time
from typing import TYPE_CHECKING, cast

from discord import Guild, app_commands
from discord.interactions import Interaction

from src.infra.db.models import GuildEconomyConfig
from src.infra.db.models._enums import CaseDropTypeEnum
from src.infra.db.operations import (
    get_guild_cases,
    get_guild_colors,
)
from src.nightcore.services.config import specified_guild_config

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


async def reward_depends_on_type_autocomplete(
    interaction: Interaction["Nightcore"],
    current: str,
) -> list[app_commands.Choice[str]]:
    """Autocomplete function to get all colors for guild."""
    start_autocomplete = time.perf_counter()
    guild = cast(Guild, interaction.guild)
    result: list[app_commands.Choice[str]] = []

    match interaction.namespace.reward:
        case CaseDropTypeEnum.CASE.value:
            result = await _cases_autocomplete(interaction, current)
        case CaseDropTypeEnum.COLOR.value:
            result = await _colors_autocomplete(interaction, current)
        case _:  # type: ignore
            result.append(
                app_commands.Choice(
                    name="Данный параметр используется только для типов кейс/цвет!",  # noqa: E501
                    value="Данный параметр используется только для типов кейс/цвет!",  # noqa: E501
                )
            )

    end_autocomplete = time.perf_counter()
    logger.info(
        "[config_reward/autocomplete] Autocomplete for guild %s took %.4f seconds",  # noqa: E501
        guild.id,
        end_autocomplete - start_autocomplete,
    )

    return result


async def _cases_autocomplete(
    interaction: Interaction["Nightcore"],
    current: str,
) -> list[app_commands.Choice[str]]:
    result: list[app_commands.Choice[str]] = []

    guild = cast(Guild, interaction.guild)

    async with specified_guild_config(
        interaction.client, guild.id, config_type=GuildEconomyConfig
    ) as (_, session):
        guild_cases = await get_guild_cases(
            session,
            guild_id=guild.id,
        )

        for case in guild_cases:
            result.append(
                app_commands.Choice(
                    name=case.name,
                    value=str(case.id),
                )
            )

    return result


async def _colors_autocomplete(
    interaction: Interaction["Nightcore"],
    current: str,
) -> list[app_commands.Choice[str]]:
    guild = cast(Guild, interaction.guild)
    result: list[app_commands.Choice[str]] = []

    async with specified_guild_config(
        interaction.client, guild.id, config_type=GuildEconomyConfig
    ) as (_, session):
        guild_colors = await get_guild_colors(
            session,
            guild_id=guild.id,
        )

        for color in guild_colors:
            role = guild.get_role(color.role_id)

            if role is not None:
                result.append(
                    app_commands.Choice(
                        name=role.name,
                        value=str(color.id),
                    )
                )

    return result
