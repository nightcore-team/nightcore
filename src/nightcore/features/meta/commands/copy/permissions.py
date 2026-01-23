"""Command to copy permissions from one channel to another."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

import discord
from discord import (
    Member,
    Role,
    app_commands,
)
from discord.abc import GuildChannel
from discord.interactions import Interaction

from src.nightcore.features.meta.commands.copy._groups import (
    copy as copy_group,
)
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.components.embed import ErrorEmbed, SuccessMoveEmbed

logger = logging.getLogger(__name__)


@copy_group.command(
    name="permissions",
    description="Перенести права из одного канала в другой",
)  # type: ignore
@app_commands.describe(
    from_channel="Канал из которого нужно перенести права",
    role_or_user="Роль или юзер, чьи права нужно перенести",
    to_channel="Канал в который нужно перенести права",
)
@app_commands.guild_only()
@check_required_permissions(PermissionsFlagEnum.ADMINISTRATOR)  # type: ignore
async def copy_permissions(
    interaction: Interaction[Nightcore],
    from_channel: GuildChannel,
    role_or_user: Member | Role,
    to_channel: GuildChannel,
):
    """Copy permissions from one channel to another for a specific user or role."""  # noqa: E501

    member = cast(Member, interaction.user)
    bot = interaction.client

    # Get permission overwrite for the target user/role in the source channel  # noqa: E501
    permission_overwrite = from_channel.overwrites_for(role_or_user)

    # Check if there are any permissions set
    if permission_overwrite.is_empty():
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка копирования прав",
                "Для выбранного пользователя или роли не заданы права в канале!",  # noqa: E501
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    # Apply permissions to the target channel
    try:
        await to_channel.set_permissions(
            role_or_user,
            overwrite=permission_overwrite,
            reason=f"Copied permissions from #{from_channel.name} by {member}",
        )
    except discord.Forbidden:
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка копирования прав",
                "У бота нет прав для управления правами в целевом канале.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    except discord.HTTPException as e:
        logger.exception(
            "[copy_permissions] Error copying permissions from %s to %s: %s",
            from_channel.id,
            to_channel.id,
            e,
        )
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка копирования прав",
                "Произошла ошибка при копировании прав!",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    target_mention = role_or_user.mention
    await interaction.response.send_message(
        embed=SuccessMoveEmbed(
            "Права скопированы",
            f"Права для {target_mention} успешно скопированы из {from_channel.mention} в {to_channel.mention}.",  # noqa: E501
            bot.user.display_name,  # type: ignore
            bot.user.display_avatar.url,  # type: ignore
        ),
        ephemeral=True,
    )

    logger.info(
        "[copy_permissions] - user=%s guild=%s from_channel=%s to_channel=%s target=%s",  # noqa: E501
        member.id,
        interaction.guild_id,
        from_channel.id,
        to_channel.id,
        role_or_user.id,
    )
