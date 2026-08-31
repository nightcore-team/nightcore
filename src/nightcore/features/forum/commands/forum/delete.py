"""Command to delete the forum configuration for a guild."""

import logging
from typing import TYPE_CHECKING

from discord import Interaction

from src.infra.db.models import GuildForumConfig
from src.infra.db.operations import get_specified_guild_config
from src.nightcore.features.forum._groups import forum as forum_group
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


@forum_group.command(
    name="delete", description="Удалить конфигурацию для гильдии"
)  # type: ignore
@check_required_permissions(PermissionsFlagEnum.BOT_ACCESS)
async def forum_delete(
    interaction: Interaction["Nightcore"],
):
    """Delete the guild forum configuration."""
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message(
            content="Команда доступна только на сервере.",
            ephemeral=True,
        )
        return

    try:
        async with interaction.client.uow.start() as session:
            config = await get_specified_guild_config(
                session,
                config_type=GuildForumConfig,
                guild_id=guild.id,
            )

            if config is None:
                await interaction.response.send_message(
                    content="Конфиг не найден!",
                    ephemeral=True,
                )
                return

            await session.delete(config)

    except Exception as e:
        logger.error(
            "[forum/delete] failed to delete config for guild %s: %s",
            guild.id,
            e,
        )
        await interaction.response.send_message(
            content="Произошла неизвестная ошибка при удалении конфига!",
            ephemeral=True,
        )
        return

    await interaction.response.send_message(
        content="Конфиг успешно удален!", ephemeral=True
    )
