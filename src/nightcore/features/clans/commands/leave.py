"""Command to leave from clan."""

import asyncio
import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, Member
from discord.interactions import Interaction

from src.infra.db.models._enums import ClanMemberRoleEnum
from src.infra.db.operations import get_clan_member
from src.nightcore.components.embed import ErrorEmbed, SuccessMoveEmbed
from src.nightcore.features.clans._groups import clan as clan_main_group
from src.nightcore.utils import ensure_role_exists

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


@clan_main_group.command(name="leave", description="Покинуть клан")
async def leave(interaction: Interaction["Nightcore"]):
    """Leave from clan."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)
    user = cast(Member, interaction.user)

    outcome = ""
    clan_name = ""
    clan_role_id = 0

    async with bot.uow.start() as session:
        db_clan_member = await get_clan_member(
            session,
            guild_id=guild.id,
            user_id=user.id,
            with_relations=True,
        )

        if not db_clan_member:
            outcome = "not_in_clan"
        elif db_clan_member.role == ClanMemberRoleEnum.LEADER:
            outcome = "is_leader"
        else:
            clan_name = db_clan_member.clan.name
            clan_role_id = db_clan_member.clan.role_id

            try:
                await session.delete(db_clan_member)
                await session.flush()
                outcome = "success"
            except Exception as e:
                logger.error(
                    "[clans] Failed to remove clan member %s from clan %s in guild %s: %s",  # noqa: E501
                    user.id,
                    db_clan_member.clan.id,
                    guild.id,
                    e,
                )
                outcome = "database_error"

    if outcome == "not_in_clan":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка выхода из клана",
                "Вы не состоите в клане на этом сервере.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "is_leader":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка выхода из клана",
                "Лидер клана не может покинуть его. Передайте лидерство другому участнику или удалите клан.",  # noqa: E501
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "database_error":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка выхода из клана",
                "Не удалось покинуть клан из-за внутренней ошибки.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "success":
        role = await ensure_role_exists(guild, clan_role_id)

        if not role:
            logger.error(
                "[clans] Clan role %s not found in guild %s",
                clan_role_id,
                guild.id,
            )
            return await interaction.response.send_message(
                embed=SuccessMoveEmbed(
                    "Выход из клана",
                    f"Вы успешно покинули клан **{clan_name}**.",
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        await asyncio.gather(
            interaction.response.send_message(
                embed=SuccessMoveEmbed(
                    "Выход из клана",
                    f"Вы успешно покинули клан **{clan_name}**.",
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            ),
            user.remove_roles(role, reason="Покинул клан"),
        )

        logger.info(
            "[command] - invoked user=%s guild=%s clan=%s",
            user.id,
            guild.id,
            clan_name,
        )
