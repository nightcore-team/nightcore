"""Command to manage clan improvements."""

from typing import TYPE_CHECKING, cast

from discord import Guild, app_commands
from discord.interactions import Interaction

from src.infra.db.models import Clan, GuildClansConfig
from src.infra.db.models._enums import ClanMemberRoleEnum
from src.infra.db.operations import get_clan_member
from src.nightcore.components.embed import (
    ErrorEmbed,
    MissingPermissionsEmbed,
    SuccessMoveEmbed,
)
from src.nightcore.features.clans._groups import manage as clan_manage_group
from src.nightcore.features.clans.utils import clans_improvements_autocomplete
from src.nightcore.services.config import specified_guild_config

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


@clan_manage_group.command(
    name="improvements", description="Управление клановыми улучшениями."
)
@app_commands.describe(improvement="Улучшение, которое нужно применить.")
@app_commands.autocomplete(improvement=clans_improvements_autocomplete)
async def improvements(
    interaction: Interaction["Nightcore"],
    improvement: str,
):
    """Manage clan improvements."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)

    outcome = ""

    async with specified_guild_config(bot, guild.id, GuildClansConfig) as (
        guild_config,
        session,
    ):
        # get clanmember
        clan_member = await get_clan_member(
            session,
            guild_id=guild.id,
            user_id=interaction.user.id,
            with_relations=True,
        )
        if not clan_member or clan_member.role not in [
            ClanMemberRoleEnum.LEADER,
            ClanMemberRoleEnum.DEPUTY,
        ]:
            outcome = "missing_permissions"

        else:
            icost = 0
            iindex = 0
            try:
                iindex = int(improvement)
                icost = guild_config.clan_improvements[iindex]
            except (IndexError, ValueError, KeyError):
                outcome = "invalid_improvement"

            if not outcome:
                # get clan
                clan = cast(Clan, clan_member.clan)  # type: ignore

                if not (clan.coins > icost):
                    outcome = "insufficient_funds"
                else:
                    match iindex:
                        case 0:
                            if clan.max_deputies + 1 <= 3:
                                clan.max_deputies += 1
                                clan.coins -= icost
                                await session.flush()
                                outcome = "success"
                            else:
                                outcome = "max_deputies_reached"
                        case 1:
                            if clan.max_members + 10 <= 30:
                                clan.max_members += 10
                                clan.coins -= icost
                                await session.flush()
                                outcome = "success"
                            else:
                                outcome = "max_members_reached"
                        case 2:
                            if clan.payday_multipler != 2:
                                clan.payday_multipler = 2
                                clan.coins -= icost
                                await session.flush()
                                outcome = "success"
                            else:
                                outcome = "x2_payday_already_active"
                        case _:
                            outcome = "invalid_improvement"

    if outcome == "invalid_improvement":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка улучшения клана",
                "Недопустимое улучшение.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "missing_permissions":
        return await interaction.response.send_message(
            embed=MissingPermissionsEmbed(
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "insufficient_funds":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка улучшения клана",
                "Недостаточно репутации для данного улучшения.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "max_deputies_reached":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка улучшения клана",
                "Достигнут максимальный лимит заместителей.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "max_members_reached":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка улучшения клана",
                "Достигнут максимальный лимит участников.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "x2_payday_already_active":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка улучшения клана",
                "Улучшение x2 Payday уже активно.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "success":
        return await interaction.response.send_message(
            embed=SuccessMoveEmbed(
                "Успешное улучшение клана",
                "Улучшение клана применено успешно.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )
