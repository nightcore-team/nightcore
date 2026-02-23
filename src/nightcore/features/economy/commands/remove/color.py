"""Command to remove color from a user."""

import asyncio
import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, User, app_commands
from discord.interactions import Interaction

from src.infra.db.models import GuildLoggingConfig
from src.infra.db.models._enums import ChannelType
from src.infra.db.operations import (
    get_color_by_id,
    get_or_create_user,
    get_specified_channel,
)
from src.nightcore.components.embed import (
    ErrorEmbed,
    SuccessMoveEmbed,
)
from src.nightcore.features.economy._groups import remove as remove_group
from src.nightcore.features.economy.events.dto import (
    AwardNotificationEventDTO,
)
from src.nightcore.features.economy.utils.autocomplete import (
    user_colors_autocomplete,
)
from src.nightcore.utils import ensure_member_exists
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)
from src.nightcore.utils.transformers.str_to_int import StrToIntTransformer

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


@remove_group.command(name="color", description="Удалить у пользователя цвет")  # type: ignore
@app_commands.describe(
    user="Пользователь,  у которого удаляется цвет",
    color_id="Цвет для удаления",
    reason="Причина удаления цвета (необязательно)",
)
@app_commands.autocomplete(color_id=user_colors_autocomplete)
@app_commands.rename(color_id="color")
@check_required_permissions(PermissionsFlagEnum.ECONOMY_ACCESS)
async def remove_color(
    interaction: Interaction["Nightcore"],
    user: User,
    color_id: app_commands.Transform[int, StrToIntTransformer],
    reason: str | None = None,
):
    """Give a color to user."""

    guild = cast(Guild, interaction.guild)
    bot = interaction.client

    outcome = ""

    if not guild.me.guild_permissions.manage_roles:
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка удаления цвета",
                "У меня недостаточно прав для управления ролями.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if user == bot.user:
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка удаления цвета",
                "Невозможно удалить цвет у бота.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    async with bot.uow.start() as session:
        logging_channel_id = await get_specified_channel(
            session,
            guild_id=guild.id,
            config_type=GuildLoggingConfig,
            channel_type=ChannelType.LOGGING_ECONOMY,
        )

        if not outcome:
            user_record, _ = await get_or_create_user(
                session,
                guild_id=guild.id,
                user_id=user.id,
            )
            color = await get_color_by_id(
                session, guild_id=guild.id, color_id=color_id
            )

            if color is None:
                outcome = "unknown_color"
            else:
                if color in user_record.colors:
                    user_record.colors.remove(color)

                    outcome = "success"
                else:
                    outcome = "does_not_have_color"

    if outcome == "unknown_color":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка удаления цвета",
                "Цвет не был найден.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "does_not_have_color":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка удаления цвета",
                "У пользователя нет этого цвета.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "success":
        await interaction.response.send_message(
            embed=SuccessMoveEmbed(
                "Удаление цвета успешно",
                f"Вы успешно удалили пользователю <@{user.id}> цвет <@&{color.role_id}>.",  # noqa: E501 # type: ignore
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

        color_role = guild.get_role(color.role_id)  # type: ignore

        if color_role:
            member = await ensure_member_exists(guild, user.id)
            if member:
                asyncio.create_task(
                    member.remove_roles(
                        color_role, reason="Color removed via economy command."
                    )
                )

        color_name = color_role.name if color_role else "unknown"

        bot.dispatch(
            "user_items_changed",
            dto=AwardNotificationEventDTO(
                guild=guild,
                event_type="remove/color",
                logging_channel_id=logging_channel_id,
                user_id=user.id,
                moderator_id=interaction.user.id,
                item_name=f"{color_name} ({color.role_id})",  # type: ignore
                amount=-1,
                reason=reason,
            ),
        )
