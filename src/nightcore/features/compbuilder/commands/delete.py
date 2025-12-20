"""Subcommand for deleting an existing component."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, app_commands
from discord.interactions import Interaction

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.infra.db.operations import get_custom_component_by_id
from src.nightcore.components.embed import ErrorEmbed, SuccessMoveEmbed
from src.nightcore.features.compbuilder._groups import (
    components as builder_group,
)
from src.nightcore.features.compbuilder.utils.autocomplete import (
    components_autocomplete,
)
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

logger = logging.getLogger(__name__)


@builder_group.command(
    name="delete",
    description="Удалить существующий компонент",
)  # type: ignore
@app_commands.describe(
    component="Выберите компонент для удаления",
)
@app_commands.autocomplete(component=components_autocomplete)
@check_required_permissions(PermissionsFlagEnum.MODERATION_ACCESS)
async def delete(
    interaction: Interaction[Nightcore],
    component: str,
):
    """Delete an existing custom component."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)

    try:
        component_id = int(component)
    except ValueError:
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка удаления компонента",
                "Указанный компонент не найден.",
                bot.user.display_name,  # type: ignore
                bot.user.avatar.url,  # type: ignore
            )
        )

    outcome = ""
    async with bot.uow.start() as session:
        cmp = await get_custom_component_by_id(
            session,
            guild_id=guild.id,
            id=component_id,
        )
        if not cmp:
            outcome = "not_found"
        else:
            try:
                await session.delete(cmp)
                outcome = "success"
            except Exception:
                logger.error(
                    "Error deleting custom component %s in guild %s",
                    cmp.id,
                    guild.id,
                    exc_info=True,
                )
                outcome = "error"

    if outcome == "not_found":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка удаления компонента",
                "Указанный компонент не найден.",
                bot.user.display_name,  # type: ignore
                bot.user.avatar.url,  # type: ignore
            )
        )

    if outcome == "error":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка удаления компонента",
                "Произошла ошибка при удалении компонента. ",
                bot.user.display_name,  # type: ignore
                bot.user.avatar.url,  # type: ignore
            )
        )

    if outcome == "success":
        return await interaction.response.send_message(
            embed=SuccessMoveEmbed(
                "Компонент удалён",
                f"Компонент **{cmp.name}** был успешно удалён.",  # type: ignore
                bot.user.display_name,  # type: ignore
                bot.user.avatar.url,  # type: ignore
            )
        )
