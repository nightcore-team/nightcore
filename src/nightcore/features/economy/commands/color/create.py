"""Command to create color."""

import logging
from typing import TYPE_CHECKING, cast

import discord
from discord import Guild, Member
from discord.interactions import Interaction
from sqlalchemy.exc import IntegrityError

from src.infra.db.models import GuildLoggingConfig
from src.infra.db.models.color import Color
from src.infra.db.operations import (
    get_specified_webhook,
)
from src.nightcore.components.view.v2 import ErrorViewV2, SuccessViewV2
from src.nightcore.features.economy._groups import color as color_group
from src.nightcore.features.economy.events.dto.item_change import (
    ChangedRole,
    ItemChangeNotifyEventDTO,
)
from src.nightcore.utils.object import compare_top_roles
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)
from src.utils._enums import ChannelType, ItemChangeActionEnum

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


@color_group.command(name="create", description="Создать цвет")  # type: ignore
@check_required_permissions(PermissionsFlagEnum.ECONOMY_ACCESS)
async def create_color(
    interaction: Interaction["Nightcore"],
    role: discord.Role,
):
    """Create color."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)
    member = cast(Member, interaction.user)

    logging_webhook = None
    outcome = ""

    if role.position >= member.top_role.position:
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка создания цвета",
                "Вы не можете использовать роль с позицией выше чем ваша высшая роль.",  # noqa: E501
            ),
            ephemeral=True,
        )
        return

    if role.permissions.administrator:
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка создания цвета",
                "Роль цвета не может иметь права администратора.",
            ),
            ephemeral=True,
        )
        return

    if not compare_top_roles(guild, role):
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка создания цвета",
                "Роль цвета должна быть ниже высшей роли бота.",
            ),
            ephemeral=True,
        )
        return

    try:
        async with bot.uow.start() as session:
            new_color = Color(
                guild_id=guild.id,
                role_id=role.id,
            )

            session.add(new_color)

            logging_webhook = await get_specified_webhook(
                session,
                guild_id=guild.id,
                config_type=GuildLoggingConfig,
                channel_type=ChannelType.LOGGING_ECONOMY,
            )

    except IntegrityError:
        outcome = "color_exists"

        logger.warning(
            "[color/create] Error creating color in guild %s with existing role %s",  # noqa: E501
            guild.id,
            role.id,
        )

    except Exception as e:
        outcome = "color_create_error"

        logger.exception(
            "[color/create] Error creating color in guild %s: %s",
            guild.id,
            e,
        )

    if outcome == "color_exists":
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка создания цвета",
                "К данной роли уже привязан цвет.",
            ),
            ephemeral=True,
        )
        return

    if outcome == "color_create_error":
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка создания цвета",
                "Произошла ошибка при создании цвета. Обратитесь к разработчикам.",  # noqa: E501
            ),
            ephemeral=True,
        )
        return

    item = ChangedRole(after_id=role.id)

    dto = ItemChangeNotifyEventDTO(
        guild=guild,
        event_type=ItemChangeActionEnum.CREATE.value,
        logging_webhook=logging_webhook,
        moderator_id=interaction.user.id,
        item_name=f"{role.mention} ({role.id})",
        item=item,
    )

    bot.dispatch("item_change_notify", dto)

    await interaction.response.send_message(
        view=SuccessViewV2(
            "Создание цвета успешно",
            f"Вы успешно создали цвет {role.mention} ",
        ),
        ephemeral=True,
    )

    logger.info("[command] - invoked guild=%s role_id=%s", guild.id, role.id)
