"""Autocomplete utilities."""

import logging
import time
from typing import TYPE_CHECKING, Final, cast

from discord import Guild, app_commands
from discord.interactions import Interaction

from src.infra.db.models._enums import CaseDropTypeEnum
from src.infra.db.operations import (
    get_guild_cases,
    get_guild_colors,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)

_commands: Final[dict[str, int]] = {"add_level": 1, "change_level": 2}


async def reward_depends_on_type_autocomplete(
    interaction: Interaction["Nightcore"],
    current: str,
) -> list[app_commands.Choice[str]]:
    """Autocomplete function to get colors or cases depends on reward type for guild."""  # noqa: E501
    start_autocomplete = time.perf_counter()
    guild = cast(Guild, interaction.guild)
    result: list[app_commands.Choice[str]] = []

    index = _commands[interaction.command.name]  # type: ignore

    match interaction.data["options"][index]["value"]:  # type: ignore
        case CaseDropTypeEnum.CASE.value:
            result = await _cases_autocomplete(interaction, current)
        case CaseDropTypeEnum.COLOR.value:
            result = await _colors_autocomplete(interaction, current)
        case CaseDropTypeEnum.CUSTOM.value:
            result = await _custom_reward_autocomplete()
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


async def _custom_reward_autocomplete() -> list[app_commands.Choice[str]]:
    return [
        app_commands.Choice(
            name="Введите название вашей кастомной награды",
            value="Введите название вашей кастомной награды",
        )
    ]


async def _cases_autocomplete(
    interaction: Interaction["Nightcore"],
    current: str,
) -> list[app_commands.Choice[str]]:
    result: list[app_commands.Choice[str]] = []

    guild = cast(Guild, interaction.guild)

    async with interaction.client.uow.start() as session:
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

    async with interaction.client.uow.start() as session:
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
