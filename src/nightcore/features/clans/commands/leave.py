"""Clan deletion command."""

import asyncio
import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, Member, app_commands
from discord.interactions import Interaction

from src.infra.db.models._enums import ClanMemberRoleEnum
from src.infra.db.operations import get_clan_member
from src.nightcore.components.embed import ErrorEmbed, SuccessMoveEmbed
from src.nightcore.features.clans._groups import clan as clan_main_group
from src.nightcore.utils import ensure_role_exists

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


@clan_main_group.command(name="leave", description="Leave from a clan.")
@app_commands.describe()
async def leave(interaction: Interaction["Nightcore"]):
    """Leave from clan."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)
    user = cast(Member, interaction.user)

    async with bot.uow.start() as session:
        db_clan_member = await get_clan_member(
            session,
            guild_id=guild.id,
            user_id=user.id,
            with_relations=True,
        )
        if not db_clan_member:
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка выхода из клана",
                    "Вы не состоите в клане на этом сервере.",
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if db_clan_member.role == ClanMemberRoleEnum.LEADER:
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка выхода из клана",
                    "Лидер клана не может покинуть его. Передайте лидерство другому участнику или удалите клан.",  # noqa: E501, RUF001
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )
        try:
            await session.delete(db_clan_member)
        except Exception as e:
            logger.error(
                "[clans] Failed to remove clan member %s from clan %s in guild %s: %s",  # noqa: E501
                user.id,
                db_clan_member.clan.id,
                guild.id,
                e,
            )
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка выхода из клана",
                    "Не удалось покинуть клан из-за внутренней ошибки.",  # noqa: RUF001
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )
        await session.flush()

    role = await ensure_role_exists(guild, db_clan_member.clan.role_id)
    if not role:
        logger.error(
            "[clans] Clan role %s not found in guild %s",
            db_clan_member.clan.role_id,
            guild.id,
        )
        await interaction.response.send_message(
            embed=SuccessMoveEmbed(
                "Выход из клана",
                f"Вы успешно покинули клан **{db_clan_member.clan.name}**.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )
        return

    await asyncio.gather(
        interaction.response.send_message(
            embed=SuccessMoveEmbed(
                "Выход из клана",
                f"Вы успешно покинули клан **{db_clan_member.clan.name}**.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        ),
        user.remove_roles(role, reason="Покинул клан"),
    )
