"""Subcommand for previewing an existing component."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

from discord import Color, Guild, app_commands
from discord.interactions import Interaction

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.infra.db.operations import get_custom_component_by_id
from src.nightcore.components.view.v2 import ErrorViewV2
from src.nightcore.features.compbuilder._groups import (
    components as builder_group,
)
from src.nightcore.features.compbuilder.components.modal import (
    ChooseImageModal,
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
    name="preview",
    description="Предпросмотр существующего компонента",
)  # type: ignore
@app_commands.describe(
    component="Выберите компонент для предпросмотра",
    color="Цвет компонента в HEX формате (опционально): Пример: #FF5733",
)
@app_commands.autocomplete(component=components_autocomplete)
@check_required_permissions(PermissionsFlagEnum.MODERATION_ACCESS)
async def preview(
    interaction: Interaction[Nightcore],
    component: str,
    color: str | None = None,
):
    """Preview an existing custom component."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)

    try:
        component_id = int(component)
    except ValueError:
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка предпросмотра компонента",
                "Указанный компонент не найден.",
            )
        )
        return

    c = Color.default()
    try:
        if color:
            c = Color.from_str(color)
    except Exception as e:
        logger.error("[compbuilder/preview] Invalid color provided: %s", e)
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка предпросмотра компонента",
                "Указанный цвет недействителен. "
                "Пожалуйста, используйте правильный HEX формат.",
            )
        )
        return

    async with bot.uow.start() as session:
        cmp = await get_custom_component_by_id(
            session,
            guild_id=guild.id,
            id=component_id,
        )

    if cmp is None:
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка предпросмотра компонента",
                "Указанный компонент не найден.",
            )
        )
        return

    await interaction.response.send_modal(
        ChooseImageModal(
            bot=bot,
            type=cmp.type,
            name=cmp.name,
            text=cmp.text,
            author_text=cmp.author_text,
            color=c,
        )
    )
    return
