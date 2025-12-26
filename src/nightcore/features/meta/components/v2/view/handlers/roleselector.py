"""Handle role selector select interactions."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

import discord
from discord import Guild, Member
from discord.interactions import Interaction

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.components.embed import EntityNotFoundEmbed, ErrorEmbed
from src.nightcore.utils import ensure_role_exists

logger = logging.getLogger(__name__)


async def handle_role_selector_select(
    interaction: Interaction[Nightcore],
) -> None:
    """Handle the role selector select interaction."""

    guild = cast(Guild, interaction.guild)
    member = cast(Member, interaction.user)
    selected_role_id = cast(int, interaction.data.get("values", [])[0])  # type: ignore

    role = await ensure_role_exists(guild, selected_role_id)

    if not role:
        return await interaction.response.send_message(
            embed=EntityNotFoundEmbed(
                "выбранная роль",
                interaction.client.user.display_name,  # type: ignore
                interaction.client.user.avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if role in member.roles:
        try:
            await member.remove_roles(
                role, reason="Удаление роли через селектор ролей"
            )
            await interaction.response.send_message(
                f"Роль {role.mention} была успешно удалена.", ephemeral=True
            )
            return
        except discord.Forbidden:
            logger.error(
                "[roleselector] Missing permissions to remove role %s from user %s in guild %s",  # noqa: E501
                role.id,
                member.id,
                guild.id,
            )
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка удаления роли",
                    "У бота нет прав для удаления этой роли.",
                    interaction.client.user.display_name,  # type: ignore
                    interaction.client.user.avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )
        except Exception as e:
            logger.error(
                "[roleselector] Failed to remove role %s from user %s in guild %s: %s",  # noqa: E501
                role.id,
                member.id,
                guild.id,
                e,
                exc_info=True,
            )
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка удаления роли",
                    "Произошла ошибка при удалении роли.",
                    interaction.client.user.display_name,  # type: ignore
                    interaction.client.user.avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

    try:
        await member.add_roles(
            role, reason="Добавление роли через селектор ролей"
        )
        await interaction.response.send_message(
            f"Роль {role.mention} была успешно добавлена.", ephemeral=True
        )
        return
    except discord.Forbidden:
        logger.error(
            "[roleselector] Missing permissions to add role %s to user %s in guild %s",  # noqa: E501
            role.id,
            member.id,
            guild.id,
        )
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка добавления роли",
                "У бота нет прав для добавления этой роли.",
                interaction.client.user.display_name,  # type: ignore
                interaction.client.user.avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )
    except Exception as e:
        logger.error(
            "[roleselector] Failed to add role %s to user %s in guild %s: %s",
            role.id,
            member.id,
            guild.id,
            e,
            exc_info=True,
        )
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка добавления роли",
                "Произошла ошибка при добавлении роли.",
                interaction.client.user.display_name,  # type: ignore
                interaction.client.user.avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )
