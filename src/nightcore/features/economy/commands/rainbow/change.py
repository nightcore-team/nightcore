"""Command to change rainbow role."""

import logging
from typing import TYPE_CHECKING, cast

import discord
from discord import Guild, Member
from discord.interactions import Interaction

from src.infra.db.models import GuildLoggingConfig
from src.infra.db.operations import (
    get_rainbow_role_by_guild,
    get_specified_channel,
)
from src.nightcore.components.embed import (
    ErrorEmbed,
)
from src.nightcore.components.embed.success import SuccessMoveEmbed
from src.nightcore.features.economy._groups import rainbow as rainbow_group
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


@rainbow_group.command(name="change", description="Изменить радужную роль")  # type: ignore
@check_required_permissions(PermissionsFlagEnum.ECONOMY_ACCESS)
async def change_rainbow(
    interaction: Interaction["Nightcore"],
    new_role: discord.Role,
):
    """Change rainbow role."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)
    member = cast(Member, interaction.user)

    logging_channel_id = None
    outcome = ""

    if new_role.position >= member.top_role.position:
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка изменения радужной роли",
                "Вы не можете использовать роль с позицией выше чем ваша высшая роль.",  # noqa: E501
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if new_role.permissions.administrator:
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка изменения радужной роли",
                "Радужная роль не может иметь права администратора.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if not compare_top_roles(guild, new_role):
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка изменения радужной роли",
                "Радужная роль должна быть ниже высшей роли бота.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    try:
        async with bot.uow.start() as session:
            rainbow = await get_rainbow_role_by_guild(
                session, guild_id=guild.id
            )

            if rainbow is None:
                outcome = "rainbow_not_found"
            else:
                before_role_id = rainbow.role_id
                rainbow.role_id = new_role.id

            logging_channel_id = await get_specified_channel(
                session,
                guild_id=guild.id,
                config_type=GuildLoggingConfig,
                channel_type=ChannelType.LOGGING_ECONOMY,
            )

    except Exception as e:
        outcome = "rainbow_change_error"

        logger.exception(
            "[rainbow/change] Error changing rainbow role in guild %s: %s",
            guild.id,
            e,
        )

    if outcome == "rainbow_not_found":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка изменения радужной роли",
                "На этом сервере не настроена радужная роль.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "rainbow_change_error":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка изменения радужной роли",
                "Произошла ошибка при изменении радужной роли. Обратитесь к разработчикам.",  # noqa: E501
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    await interaction.response.send_message(
        embed=SuccessMoveEmbed(
            "Изменение радужной роли успешно",
            f"Вы успешно изменили радужную роль на {new_role.mention} ",
            bot.user.display_name,  # type: ignore
            bot.user.display_avatar.url,  # type: ignore
        ),
        ephemeral=True,
    )

    item = ChangedRole(
        before_id=before_role_id,  # type: ignore
        after_id=new_role.id,
    )

    dto = ItemChangeNotifyEventDTO(
        guild=guild,
        event_type=ItemChangeActionEnum.COLOR_UPDATE,
        logging_channel_id=logging_channel_id,
        moderator_id=interaction.user.id,
        item_name=f"{new_role.mention} ({new_role.id})",
        item=item,
    )

    bot.dispatch("item_change_notify", dto)

    logger.info(
        "[command] - invoked guild=%s role_id=%s", guild.id, new_role.id
    )
