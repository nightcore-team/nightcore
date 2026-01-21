"""Command to change color."""

import logging
from typing import TYPE_CHECKING, cast

import discord
from discord import Guild, Member, app_commands
from discord.interactions import Interaction

from src.infra.db.models import GuildLoggingConfig
from src.infra.db.models._enums import ChannelType, ItemChangeActionEnum
from src.infra.db.operations import get_color_by_id, get_specified_channel
from src.nightcore.components.embed import (
    ErrorEmbed,
)
from src.nightcore.components.embed.success import SuccessMoveEmbed
from src.nightcore.features.economy._groups import color as color_group
from src.nightcore.features.economy.events.dto.item_change import (
    ChangedRole,
    ItemChangeNotifyEventDTO,
)
from src.nightcore.features.economy.utils.autocomplete import (
    guild_colors_autocomplete,
)
from src.nightcore.utils.object import compare_top_roles
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)
from src.nightcore.utils.transformers.str_to_int import StrToIntTransformer

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


@color_group.command(name="change", description="Изменить цвет")  # type: ignore
@app_commands.autocomplete(color=guild_colors_autocomplete)
@app_commands.rename(color_id="color")
@check_required_permissions(PermissionsFlagEnum.ECONOMY_ACCESS)
async def change_color(
    interaction: Interaction["Nightcore"],
    color_id: app_commands.Transform[int, StrToIntTransformer],
    new_role: discord.Role,
):
    """Change color."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)
    member = cast(Member, interaction.user)

    logging_channel_id = None
    outcome = None

    if new_role.position >= member.top_role.position:
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка изменения цвета",
                "Вы не можете использовать роль с позицией выше чем ваша высшая роль.",  # noqa: E501
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if new_role.permissions.administrator:
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка изменения цвета",
                "Роль цвета не может иметь права администратора.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if not compare_top_roles(guild, new_role):
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка изменения цвета",
                "Роль цвета должна быть ниже высшей роли бота.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    async with bot.uow.start() as session:
        try:
            color = await get_color_by_id(
                session, guild_id=guild.id, color_id=color_id
            )

            if color is None:
                outcome = "color_not_found"
            else:
                color.role_id = new_role.id

            logging_channel_id = await get_specified_channel(
                session,
                guild_id=guild.id,
                config_type=GuildLoggingConfig,
                channel_type=ChannelType.LOGGING_ECONOMY,
            )

        except Exception as e:
            outcome = "color_change_error"

            logger.exception(
                "[color/change] Error changing color in guild %s: %s",
                guild.id,
                e,
            )

    if outcome == "color_not_found":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка изменения цвета",
                "Выбранный цвет не найден в базе данных.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "color_change_error":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка изменения цвета",
                "Произошла ошибка при создании цвета. Обратитесь к разработчикам.",  # noqa: E501
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    item = ChangedRole(before_id=color.role_id, after_id=new_role.id)  # type: ignore

    dto = ItemChangeNotifyEventDTO(
        guild=guild,
        event_type=ItemChangeActionEnum.COLOR_UPDATE,
        logging_channel_id=logging_channel_id,
        moderator_id=interaction.user.id,
        item_name=f"{new_role.mention} ({new_role.id})",
        item=item,
    )

    bot.dispatch("item_change_notify", dto)

    await interaction.response.send_message(
        embed=SuccessMoveEmbed(
            "Изменение цвета успешно",
            f"Вы успешно изменили цвет {new_role.mention} ",
            bot.user.display_name,  # type: ignore
            bot.user.display_avatar.url,  # type: ignore
        ),
        ephemeral=True,
    )

    logger.info(
        "[command] - invoked guild=%s role_id=%s", guild.id, new_role.id
    )
