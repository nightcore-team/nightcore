"""Command to create color."""

import logging
from typing import TYPE_CHECKING, cast

import discord
from discord import Guild, Member
from discord.interactions import Interaction

from src.infra.db.models import GuildLoggingConfig
from src.infra.db.models._enums import ChannelType, ItemChangeActionEnum
from src.infra.db.models.color import Color
from src.infra.db.operations import (
    get_color_by_role_id,
    get_specified_channel,
)
from src.nightcore.components.embed import (
    ErrorEmbed,
)
from src.nightcore.components.embed.success import SuccessMoveEmbed
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

    logging_channel_id = None
    outcome = None

    if role.position >= member.top_role.position:
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка создания цвета",
                "Вы не можете использовать роль с позицией выше чем ваша высшая роль.",  # noqa: E501
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if role.permissions.administrator:
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка создания цвета",
                "Роль цвета не может иметь права администратора.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if not compare_top_roles(guild, role):
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка создания цвета",
                "Роль цвета должна быть ниже высшей роли бота.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    async with bot.uow.start() as session:
        try:
            color = await get_color_by_role_id(
                session, guild_id=guild.id, role_id=role.id
            )

            if color is not None:
                outcome = "color_exists"
            else:
                new_color = Color(
                    guild_id=guild.id,
                    role_id=role.id,
                )

                session.add(new_color)

                logging_channel_id = await get_specified_channel(
                    session,
                    guild_id=guild.id,
                    config_type=GuildLoggingConfig,
                    channel_type=ChannelType.LOGGING_ECONOMY,
                )

        except Exception as e:
            outcome = "color_create_error"

            logger.exception(
                "[color/create] Error creating color in guild %s: %s",
                guild.id,
                e,
            )

    if outcome == "color_exists":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка создания цвета",
                "К данной роли уже привязан цвет.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "color_create_error":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка создания цвета",
                "Произошла ошибка при создании цвета. Обратитесь к разработчикам.",  # noqa: E501
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    item = ChangedRole(after_id=role.id)

    dto = ItemChangeNotifyEventDTO(
        guild=guild,
        event_type=ItemChangeActionEnum.CREATE.value,
        logging_channel_id=logging_channel_id,
        moderator_id=interaction.user.id,
        item_name=f"{role.mention} ({role.id})",
        item=item,
    )

    bot.dispatch("item_change_notify", dto)

    await interaction.response.send_message(
        embed=SuccessMoveEmbed(
            "Создание цвета успешно",
            f"Вы успешно создали цвет {role.mention} ",
            bot.user.display_name,  # type: ignore
            bot.user.display_avatar.url,  # type: ignore
        ),
        ephemeral=True,
    )

    logger.info("[command] - invoked guild=%s role_id=%s", guild.id, role.id)
