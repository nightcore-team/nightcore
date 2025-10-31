"""Autocomplete utils for economy feature."""

import logging
import time
from typing import TYPE_CHECKING, cast

from discord import Guild, app_commands
from discord.interactions import Interaction

from src.infra.db.models import GuildEconomyConfig
from src.infra.db.operations import get_or_create_user
from src.nightcore.services.config import specified_guild_config

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
        "[cases/autocomplete] Autocomplete for guild %s took %.4f seconds ",
        guild.id,
        end_autocomplete - start_autocomplete,
    )

    return result


async def own_colors_autocomplete(
    interaction: Interaction["Nightcore"],
    current: str,
) -> list[app_commands.Choice[str]]:
    """Autocomplete function to get colors for user."""
    start_autocomplete = time.perf_counter()
    guild = cast(Guild, interaction.guild)
    result: list[app_commands.Choice[str]] = []

    async with specified_guild_config(
        interaction.client, guild.id, config_type=GuildEconomyConfig
    ) as (guild_config, session):
        user, created = await get_or_create_user(
            session,
            guild_id=guild.id,
            user_id=interaction.user.id,
        )
        drop_from_colors = guild_config.drop_from_colors_case or {}

    if created:
        result = []
    else:
        inventory = user.inventory.get("colors", []) or []
        for color_key in inventory:
            color_data = drop_from_colors.get(color_key, None)
            if color_data is None:
                continue

            role_id = color_data["role_id"]
            role = guild.get_role(role_id)

            if role is not None:
                result.append(
                    app_commands.Choice(
                        name=role.name,
                        value=f"{color_key}",
                    )
                )
        result.append(
            app_commands.Choice(
                name="Сбросить цвет",
                value="reset",
            )
        )

    end_autocomplete = time.perf_counter()
    logger.info(
        "[colors/autocomplete] Autocomplete for guild %s took %.4f seconds ",
        guild.id,
        end_autocomplete - start_autocomplete,
    )

    return result


async def all_colors_autocomplete(
    interaction: Interaction["Nightcore"],
    current: str,
) -> list[app_commands.Choice[str]]:
    """Autocomplete function to get all colors for guild."""
    start_autocomplete = time.perf_counter()
    guild = cast(Guild, interaction.guild)
    result: list[app_commands.Choice[str]] = []

    async with specified_guild_config(
        interaction.client, guild.id, config_type=GuildEconomyConfig
    ) as (guild_config, _):
        drop_from_colors = guild_config.drop_from_colors_case or {}

        for color_key, color_data in drop_from_colors.items():
            role_id = color_data["role_id"]

            role = guild.get_role(role_id)

            if role is not None:
                result.append(
                    app_commands.Choice(
                        name=role.name,
                        value=f"{role.name},{role_id},{color_key}",
                    )
                )

    end_autocomplete = time.perf_counter()
    logger.info(
        "[colors/autocomplete] Autocomplete for guild %s took %.4f seconds",
        guild.id,
        end_autocomplete - start_autocomplete,
    )

    return result
