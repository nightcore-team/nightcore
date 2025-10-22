"""Clan invitation command."""

import asyncio
import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, Member, app_commands
from discord.interactions import Interaction

from src.infra.db.models._enums import ClanMemberRoleEnum
from src.infra.db.operations import get_clan_member
from src.nightcore.components.embed import (
    ErrorEmbed,
    MissingPermissionsEmbed,
    SuccessMoveEmbed,
)
from src.nightcore.features.clans._groups import manage as clan_manage_group
from src.nightcore.utils import ensure_role_exists

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


@clan_manage_group.command(
    name="kick", description="Kick member from your clan."
)
@app_commands.describe(user="The user to kick from your clan.")
async def kick(
    interaction: Interaction["Nightcore"],
    user: Member,
):
    """Kick member from your clan."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)

    async with bot.uow.start() as session:
        # get clanmember
        interaction_clan_member = await get_clan_member(
            session,
            guild_id=guild.id,
            user_id=interaction.user.id,
            with_relations=True,
        )

        kicked_user_clan_member = await get_clan_member(
            session, guild_id=guild.id, user_id=user.id
        )

    if not interaction_clan_member:
        await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка кика пользователя",
                "Вы не состоите в клане.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )
        return

    if not kicked_user_clan_member:
        await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка кика пользователя",
                f"{user.mention} не состоит ни в одном из кланов.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )
        return

    if (
        interaction_clan_member.role != ClanMemberRoleEnum.LEADER
        and interaction_clan_member.role != ClanMemberRoleEnum.DEPUTY
    ):
        await interaction.response.send_message(
            embed=MissingPermissionsEmbed(
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )
        return

    if interaction_clan_member.clan_id != kicked_user_clan_member.clan_id:
        await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка кика пользователя",
                f"{user.mention} не состоит в вашем клане.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )
        return

    async with bot.uow.start() as session:
        try:
            await session.delete(kicked_user_clan_member)
        except Exception as e:
            logger.exception(
                "[clans] Failed to delete clanmember in guild %s: %s",
                guild.id,
                e,
            )
            await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка кика пользователя",
                    "Ошибка удаления пользователя в базе данных.",
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                )
            )

    embed = SuccessMoveEmbed(
        "Кик пользователя из клана",
        "Пользователь был успешно кикнут из клана.",
        bot.user.display_name,  # type: ignore
        bot.user.display_avatar.url,  # type: ignore
    )

    role = await ensure_role_exists(
        guild=guild, role_id=interaction_clan_member.clan.role_id
    )
    if not role:
        await interaction.response.send_message(embed=embed, ephemeral=True)
        logger.error(
            "[clans] Clan role %s not found in guild %s",
            interaction_clan_member.clan.role_id,
            guild.id,
        )
        return

    await asyncio.gather(
        interaction.response.send_message(embed=embed, ephemeral=True),
        user.remove_roles(role, reason="Кик из клана."),
    )
