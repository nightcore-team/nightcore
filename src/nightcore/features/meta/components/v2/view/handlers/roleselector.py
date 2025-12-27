"""Handle role selector select interactions."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

import discord
from discord import Container, Guild, Member, Message, Role
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

    selected_value = cast(int | str, interaction.data.get("values", [])[0])  # type: ignore

    if selected_value == "remove_all_roles":
        await _handle_remove_all_roles(interaction, guild, member)
    else:
        await _handle_role_toggle(
            interaction, guild, member, int(selected_value)
        )


def _get_available_role_ids(interaction: Interaction[Nightcore]) -> set[str]:
    """Extract all role IDs from the selector options."""
    container = cast(
        Container, cast(Message, interaction.message).components[0]
    )
    role_ids: set[str] = set()

    for component in container.children:
        if isinstance(
            component, discord.ui.ActionRow | discord.components.ActionRow
        ):
            select = cast(discord.ui.Select, component.children[0])  # type: ignore
            role_ids.update(option.value for option in select.options)  # type: ignore

    return role_ids


async def _handle_remove_all_roles(
    interaction: Interaction[Nightcore],
    guild: Guild,
    member: Member,
) -> None:
    """Remove all roles from the selector."""
    available_role_ids = _get_available_role_ids(interaction)
    roles_to_remove = [
        role for role in member.roles if str(role.id) in available_role_ids
    ]

    if not roles_to_remove:
        await interaction.response.send_message(
            "У вас нет ролей для удаления из селектора ролей.",
            ephemeral=True,
        )
        return

    await _remove_roles(interaction, guild, member, roles_to_remove)


async def _handle_role_toggle(
    interaction: Interaction[Nightcore],
    guild: Guild,
    member: Member,
    role_id: int,
) -> None:
    """Add or remove a specific role."""
    role = await ensure_role_exists(guild, role_id)

    if not role:
        await interaction.response.send_message(
            embed=EntityNotFoundEmbed(
                "выбранная роль",
                interaction.client.user.display_name,  # type: ignore
                interaction.client.user.avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )
        return

    if role in member.roles:
        await _remove_roles(interaction, guild, member, [role])
    else:
        await _add_role(interaction, guild, member, role)


async def _remove_roles(
    interaction: Interaction[Nightcore],
    guild: Guild,
    member: Member,
    roles: list[Role],
) -> None:
    """Remove roles from a member."""
    try:
        reason = (
            "Удаление ролей через селектор ролей"
            if len(roles) > 1
            else "Удаление роли через селектор ролей"
        )
        await member.remove_roles(*roles, reason=reason, atomic=False)

        message = (
            "Все роли из селектора ролей были успешно удалены."
            if len(roles) > 1
            else f"Роль {roles[0].mention} была успешно удалена."
        )
        await interaction.response.send_message(message, ephemeral=True)

    except discord.Forbidden:
        logger.error(
            "[roleselector] Missing permissions to remove roles from user %s in guild %s",  # noqa: E501
            member.id,
            guild.id,
        )
        await interaction.response.send_message(
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
            "[roleselector] Failed to remove roles from user %s in guild %s: %s",  # noqa: E501
            member.id,
            guild.id,
            e,
            exc_info=True,
        )
        await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка удаления роли",
                "Произошла ошибка при удалении роли.",
                interaction.client.user.display_name,  # type: ignore
                interaction.client.user.avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )


async def _add_role(
    interaction: Interaction[Nightcore],
    guild: Guild,
    member: Member,
    role: Role,
) -> None:
    """Add a role to a member."""
    try:
        await member.add_roles(
            role, reason="Добавление роли через селектор ролей"
        )
        await interaction.response.send_message(
            f"Роль {role.mention} была успешно добавлена.",
            ephemeral=True,
        )
    except discord.Forbidden:
        logger.error(
            "[roleselector] Missing permissions to add role %s to user %s in guild %s",  # noqa: E501
            role.id,
            member.id,
            guild.id,
        )
        await interaction.response.send_message(
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
        await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка добавления роли",
                "Произошла ошибка при добавлении роли.",
                interaction.client.user.display_name,  # type: ignore
                interaction.client.user.avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )
