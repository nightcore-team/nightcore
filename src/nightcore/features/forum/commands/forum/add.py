import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, Interaction, Role, TextChannel
from sqlalchemy.exc import IntegrityError

from src.infra.db.models.guild import GuildForumConfig
from src.nightcore.features.forum._groups import forum as forum_group
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


@forum_group.command(
    name="add", description="Создать конфигурацию для гильдии"
)  # type: ignore
@check_required_permissions(PermissionsFlagEnum.BOT_ACCESS)
async def forum_add(
    interaction: Interaction["Nightcore"],
    section_id: int,
    channel: TextChannel,
    role: Role,
):
    guild = cast(Guild, interaction.guild)

    try:
        async with interaction.client.uow.start() as session:
            config = GuildForumConfig(
                section_id=section_id, role_id=role.id, channel_id=channel.id
            )
            session.add(config)
    except IntegrityError:
        await interaction.response.send_message(
            "Конфиг для данной гильдии уже существует", ephemeral=True
        )
    except Exception as e:
        logger.error(
            "[forum/add] failed to create config for guild %s: %e",
            guild.id,
            e,
        )

    await interaction.response.send_message(
        content="Конфиг успешно создан!", ephemeral=True
    )
