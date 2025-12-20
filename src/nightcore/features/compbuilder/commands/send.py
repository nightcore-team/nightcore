"""Subcommand for sending an existing component."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Color, Guild, Role, app_commands
from discord.interactions import Interaction

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.infra.db.operations import get_custom_component_by_id
from src.nightcore.components.embed import ErrorEmbed
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
    name="send",
    description="Отправить существующий компонент",
)  # type: ignore
@app_commands.describe(
    component="Выберите компонент для отправки",
    color="Цвет компонента в HEX формате (опционально): Пример: #FF5733",
    role="Роль, которую нужно упомянуть при отправке компонента (опционально)",
)
@app_commands.autocomplete(component=components_autocomplete)
@check_required_permissions(PermissionsFlagEnum.MODERATION_ACCESS)
async def send(
    interaction: Interaction["Nightcore"],
    component: str,
    color: str | None = None,
    role: Role | None = None,
):
    """Preview an existing custom component."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)

    try:
        component_id = int(component)
    except ValueError:
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка отправки компонента",
                "Указанный компонент не найден.",
                bot.user.display_name,  # type: ignore
                bot.user.avatar.url,  # type: ignore
            )
        )

    c = Color.default()
    try:
        if color:
            c = Color.from_str(color)
    except Exception as e:
        logger.error("[compbuilder/preview] Invalid color provided: %s", e)
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка отправки компонента",
                "Указанный цвет недействителен. Пожалуйста, используйте правильный HEX формат.",  # noqa: E501
                bot.user.display_name,  # type: ignore
                bot.user.avatar.url,  # type: ignore
            )
        )

    async with bot.uow.start() as session:
        cmp = await get_custom_component_by_id(
            session,
            guild_id=guild.id,
            id=component_id,
        )

    if cmp is None:
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка отправки компонента",
                "Указанный компонент не найден.",
                bot.user.display_name,  # type: ignore
                bot.user.avatar.url,  # type: ignore
            )
        )

    return await interaction.response.send_modal(
        ChooseImageModal(
            bot=bot,
            type=cmp.type,
            name=cmp.name,
            text=cmp.text,
            author_text=cmp.author_text,
            color=c,
            role=role,
            ephemeral=False,
        )
    )
