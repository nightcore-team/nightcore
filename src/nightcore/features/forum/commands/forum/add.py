import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, Interaction
from sqlalchemy.exc import IntegrityError

from src.infra.db.models import GuildForumConfig
from src.infra.db.operations import get_guild_forum_config
from src.nightcore.features.forum._groups import forum as forum_group
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


@forum_group.command(
    name="add", description="Настроить конфигурацию для гильдии"
)  # type: ignore
@check_required_permissions(PermissionsFlagEnum.BOT_ACCESS)
async def forum_add(
    interaction: Interaction["Nightcore"], section_id: int, prefix_id: int
):
    guild = cast(Guild, interaction.guild)

    try:
        async with interaction.client.uow.start() as session:
            config = await get_guild_forum_config(session, guild_id=guild.id)
            if config is None:
                config = GuildForumConfig(
                    guild_id=guild.id,
                    prefix_id=prefix_id,
                    section_id=section_id,
                )
                session.add(config)
            else:
                config.section_id = section_id
                config.prefix_id = prefix_id

    except IntegrityError:
        logger.warning(
            "[forum/add] section %s is already bound to another guild"
            " (guild %s)",
            section_id,
            guild.id,
        )
        await interaction.response.send_message(
            content="Данный раздел уже занят другой гильдией!",
            ephemeral=True,
        )
        return
    except Exception as e:
        logger.error(
            "[forum/add] failed to create config for guild %s: %s",
            guild.id,
            e,
        )
        await interaction.response.send_message(
            content="Произошла неизвестная ошибка при создании конфига!",
            ephemeral=True,
        )
        return

    await interaction.response.send_message(
        content="Конфиг успешно создан или обновлён", ephemeral=True
    )
