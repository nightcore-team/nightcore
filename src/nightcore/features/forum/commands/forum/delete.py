"""Command to delete forum configuration for the guild."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, Interaction

from src.infra.db.models import GuildForumConfig
from src.infra.db.operations import get_specified_guild_config
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
    name="delete", description="Удалить конфигурацию для гильдии"
)
@check_required_permissions(PermissionsFlagEnum.BOT_ACCESS)
@time_executing
async def forum_delete(
    interaction: Interaction["Nightcore"],
):
    """Delete the forum configuration for the guild."""

    guild = cast(Guild, interaction.guild)

    outcome = ""

    try:
        async with interaction.client.uow.start() as session:
            config = await get_specified_guild_config(
                session,
                config_type=GuildForumConfig,
                guild_id=guild.id,
            )

            if config is None:
                outcome = "config_not_found"
            else:
                await session.delete(config)

    except Exception as e:
        logger.error(
            "[forum/add] failed to delete config for guild %s: %e",
            guild.id,
            e,
        )
        await interaction.response.send_message(
            content="Произошла неизвестная ошибка при удалении конфига!",
            ephemeral=True,
        )
        return

    if outcome == "config_not_found":
        return await interaction.response.send_message(
            content="Конфиг для данной гильдии не найден!", ephemeral=True
        )

    await interaction.response.send_message(
        content="Конфиг успешно удален!", ephemeral=True
    )
