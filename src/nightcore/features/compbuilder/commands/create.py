"""Subcommand for creating a new component."""

from __future__ import annotations

from typing import TYPE_CHECKING

from discord.interactions import Interaction

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.features.compbuilder._groups import (
    components as builder_group,
)
from src.nightcore.features.compbuilder.components.modal import (
    CreateComponentModal,
)
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)


@builder_group.command(
    name="create",
    description="Создать новый компонент",
)  # type: ignore
@check_required_permissions(PermissionsFlagEnum.MODERATION_ACCESS)
async def create(interaction: Interaction[Nightcore]):
    """Create a new custom component."""

    return await interaction.response.send_modal(
        CreateComponentModal(interaction.client)
    )
