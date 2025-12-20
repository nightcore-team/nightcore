"""Subcommand for changing a new component."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from discord import Guild, app_commands
from discord.interactions import Interaction

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.infra.db.operations import get_custom_component_by_id
from src.nightcore.components.embed import ErrorEmbed
from src.nightcore.features.compbuilder._groups import (
    components as builder_group,
)
from src.nightcore.features.compbuilder.components.modal import (
    ChangeComponentModal,
)
from src.nightcore.features.compbuilder.utils.autocomplete import (
    components_autocomplete,
)
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)


@builder_group.command(
    name="change",
    description="Изменить существующий компонент",
)  # type: ignore
@app_commands.autocomplete(component=components_autocomplete)
@check_required_permissions(PermissionsFlagEnum.MODERATION_ACCESS)
async def change(
    interaction: Interaction[Nightcore],
    component: str,
):
    """Change an existing custom component."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)

    try:
        component_id = int(component)
    except ValueError:
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка изменения компонента",
                "Указанный компонент не найден.",
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

    if not cmp:
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка изменения компонента",
                "Указанный компонент не найден.",
                bot.user.display_name,  # type: ignore
                bot.user.avatar.url,  # type: ignore
            )
        )

    return await interaction.response.send_modal(
        ChangeComponentModal(bot, cmp)
    )
