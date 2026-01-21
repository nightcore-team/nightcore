"""
Autocomplete utilities.

Used for providing autocomplete options for cases and colors.
"""

import logging
import time
from typing import TYPE_CHECKING, Final, cast

from discord import Guild, app_commands
from discord.interactions import Interaction

from src.infra.db.models._enums import CaseDropTypeEnum
from src.infra.db.operations import (
    get_guild_cases,
    get_guild_colors,
    get_or_create_user,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)

CLEAR_COLOR_ID: Final[int] = -1

_commands: Final[dict[str, int]] = {"add_reward": 1}


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
            result = await guild_cases_autocomplete(interaction, current)
        case CaseDropTypeEnum.COLOR.value:
            result = await guild_colors_autocomplete(interaction, current)
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


async def user_cases_autocomplete(
    interaction: Interaction["Nightcore"],
    current: str,
) -> list[app_commands.Choice[str]]:
    """Autocomplete function to get cases for user."""
    start_autocomplete = time.perf_counter()
    guild = cast(Guild, interaction.guild)

    async with interaction.client.uow.start() as session:
        user, _ = await get_or_create_user(
            session,
            guild_id=guild.id,
            user_id=interaction.user.id,
        )

    result: list[app_commands.Choice[str]] = []

    for case in user.cases:
        result.append(
            app_commands.Choice(
                name=f"{case.item.name}, количество: {case.amount}",
                value=case.item.name,
            )
        )

    end_autocomplete = time.perf_counter()
    logger.info(
        "[cases/autocomplete] Autocomplete for guild %s took %.4f seconds ",
        guild.id,
        end_autocomplete - start_autocomplete,
    )

    return result


async def user_colors_autocomplete(
    interaction: Interaction["Nightcore"],
    current: str,
) -> list[app_commands.Choice[str]]:
    """Autocomplete function to get colors for user."""
    start_autocomplete = time.perf_counter()
    guild = cast(Guild, interaction.guild)
    result: list[app_commands.Choice[str]] = []

    async with interaction.client.uow.start() as session:
        user, _ = await get_or_create_user(
            session,
            guild_id=guild.id,
            user_id=interaction.user.id,
        )

    for color in user.colors:
        role = guild.get_role(color.role_id)

        if role is None:
            value = f"Цвет не найден. id: {color.id}"
        else:
            value = role.name
        result.append(
            app_commands.Choice(
                name=value,
                value=str(color.id),
            )
        )
    result.append(
        app_commands.Choice(
            name="Сбросить цвет",
            value=str(CLEAR_COLOR_ID),
        )
    )

    end_autocomplete = time.perf_counter()
    logger.info(
        "[colors/autocomplete] Autocomplete for guild %s took %.4f seconds ",
        guild.id,
        end_autocomplete - start_autocomplete,
    )

    return result


async def guild_colors_autocomplete(
    interaction: Interaction["Nightcore"],
    current: str,
) -> list[app_commands.Choice[str]]:
    """Autocomplete function to get all colors for guild."""
    start_autocomplete = time.perf_counter()
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

    end_autocomplete = time.perf_counter()
    logger.info(
        "[colors/autocomplete] Autocomplete for guild %s took %.4f seconds",
        guild.id,
        end_autocomplete - start_autocomplete,
    )

    return result


async def guild_cases_autocomplete(
    interaction: Interaction["Nightcore"],
    current: str,
) -> list[app_commands.Choice[str]]:
    """Autocomplete function to get all cases for guild."""
    start_autocomplete = time.perf_counter()
    guild = cast(Guild, interaction.guild)
    result: list[app_commands.Choice[str]] = []

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

    end_autocomplete = time.perf_counter()
    logger.info(
        "[cases/autocomplete] Autocomplete for guild %s took %.4f seconds",
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
