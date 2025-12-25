"""Command to manage clan improvements."""

from typing import TYPE_CHECKING, cast

from discord import Guild, app_commands
from discord.interactions import Interaction

from src.infra.db.models import Clan, GuildClansConfig, GuildLoggingConfig
from src.infra.db.models._enums import (
    ChannelType,
    ClanManageActionEnum,
    ClanMemberRoleEnum,
)
from src.infra.db.operations import get_clan_member, get_specified_channel
from src.nightcore.components.embed import (
    ErrorEmbed,
    MissingPermissionsEmbed,
    SuccessMoveEmbed,
)
from src.nightcore.features.clans._groups import manage as clan_manage_group
from src.nightcore.features.clans.events.dto.clan_manage_notify import (
    ClanManageAction,
    ClanManageNotifyDTO,
)
from src.nightcore.features.clans.utils import clans_improvements_autocomplete
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


@clan_manage_group.command(  # type: ignore
    name="improvements", description="Управление клановыми улучшениями."
)
@app_commands.describe(improvement="Улучшение, которое нужно применить.")
@app_commands.autocomplete(improvement=clans_improvements_autocomplete)
@check_required_permissions(PermissionsFlagEnum.NONE)
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
            index = 0
            try:
                index = int(improvement)
                icost = guild_config.clan_improvements[index]
            except (IndexError, ValueError, KeyError):
                outcome = "invalid_improvement"

            if not outcome:
                # get clan
                clan = cast(Clan, clan_member.clan)  # type: ignore

                if not (clan.coins > icost):
                    outcome = "insufficient_funds"
                else:
                    match index:
                        case 0:
                            if clan.max_deputies + 1 <= 3:
                                clan.max_deputies += 1
                                clan.coins -= icost
                                await session.flush()
                                outcome = "success"
                            else:
                                outcome = "max_deputies_reached"
                        case 1:
                            if clan.max_members + 10 <= 100:
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

    async with bot.uow.start() as session:
        clans_logging_channel = await get_specified_channel(
            session,
            guild_id=guild.id,
            config_type=GuildLoggingConfig,
            channel_type=ChannelType.LOGGING_CLANS,
        )

    clan_buy_improvement_action = ClanManageAction(
        type=ClanManageActionEnum.BUY_IMPOVEMENT, after=improvement
    )

    dto = ClanManageNotifyDTO(
        guild=guild,
        event_type="clan_manage_notify",
        actor_id=interaction.user.id,
        clan_name=clan_member.clan.name,  # type: ignore The clan will always exist here because of the checks on lines 64 and 125
        actions=[clan_buy_improvement_action],
        logging_channel_id=clans_logging_channel,
    )

    bot.dispatch("clan_manage_notify", dto)

    return await interaction.response.send_message(
        embed=SuccessMoveEmbed(
            "Успешное улучшение клана",
            "Улучшение клана применено успешно.",
            bot.user.display_name,  # type: ignore
            bot.user.display_avatar.url,  # type: ignore
        ),
        ephemeral=True,
    )
