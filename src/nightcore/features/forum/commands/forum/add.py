"""Command to add forum configuration for the guild."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, Interaction
from sqlalchemy.exc import IntegrityError

from src.infra.db.models import GuildForumConfig
from src.nightcore.decorators.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)
from src.nightcore.decorators.time_executing import time_executing
from src.nightcore.features.forum._groups import forum as forum_group

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


@forum_group.command(
    name="add", description="Настроить конфигурацию для гильдии"
)
@check_required_permissions(PermissionsFlagEnum.BOT_ACCESS)
@time_executing
async def forum_add(
    interaction: Interaction["Nightcore"],
    section_id: int,
):
    """Set up the forum configuration for the guild."""

    guild = cast(Guild, interaction.guild)

    try:
        async with interaction.client.uow.start() as session:
            config = GuildForumConfig(
                section_id=section_id,
            )
            session.add(config)
    except IntegrityError:
        return await interaction.response.send_message(
            "Конфиг для данной гильдии уже существует", ephemeral=True
        )
    except Exception as e:
        logger.error(
            "[forum/add] failed to create config for guild %s: %e",
            guild.id,
            e,
        )
        await interaction.response.send_message(
            content="Произошла неизвестная ошибка при создании конфига!",
            ephemeral=True,
        )
        return

    await interaction.response.send_message(
        content="Конфиг успешно создан!", ephemeral=True
    )
