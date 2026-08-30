"""Command to manage clan improvements."""

from typing import TYPE_CHECKING, cast

from discord import Guild, app_commands
from discord.interactions import Interaction

from src.infra.db.models import GuildClansConfig, GuildLoggingConfig
from src.infra.db.operations import (
    get_clan_by_id,
    get_clan_member,
    get_specified_webhook,
)
from src.nightcore.components.view.v2 import (
    ErrorViewV2,
    MissingPermissionsViewV2,
    SuccessViewV2,
)
from src.nightcore.features.clans._groups import manage as clan_manage_group
from src.nightcore.features.clans.events.dto.clan_manage_notify import (
    ClanManageAction,
    ClanManageNotifyDTO,
)
from src.nightcore.features.clans.utils import (
    CLAN_IMPROVEMENTS,
    clans_improvements_autocomplete,
)
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)
from src.utils._enums import (
    ChannelType,
    ClanManageActionEnum,
    ClanMemberRoleEnum,
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
            for_update=True,
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
                # get clan with FOR UPDATE to prevent lost update on coins
                clan = await get_clan_by_id(
                    session,
                    guild_id=guild.id,
                    clan_id=clan_member.clan.id,  # type: ignore
                    for_update=True,
                )
                if clan is None:
                    outcome = "clan_not_found"
                elif not (clan.coins > icost):
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
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка улучшения клана",
                "Недопустимое улучшение.",
            ),
            ephemeral=True,
        )
        return

    if outcome == "missing_permissions":
        await interaction.response.send_message(
            view=MissingPermissionsViewV2(),
            ephemeral=True,
        )
        return

    if outcome == "insufficient_funds":
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка улучшения клана",
                "Недостаточно репутации для данного улучшения.",
            ),
            ephemeral=True,
        )
        return

    if outcome == "max_deputies_reached":
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка улучшения клана",
                "Достигнут максимальный лимит заместителей.",
            ),
            ephemeral=True,
        )
        return

    if outcome == "max_members_reached":
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка улучшения клана",
                "Достигнут максимальный лимит участников.",
            ),
            ephemeral=True,
        )
        return

    if outcome == "x2_payday_already_active":
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка улучшения клана",
                "Улучшение x2 Payday уже активно.",
            ),
            ephemeral=True,
        )
        return

    if outcome == "clan_not_found":
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка улучшения клана",
                "Клан не найден.",
            ),
            ephemeral=True,
        )
        return

    async with bot.uow.start() as session:
        clans_logging_channel = await get_specified_webhook(
            session,
            guild_id=guild.id,
            config_type=GuildLoggingConfig,
            channel_type=ChannelType.LOGGING_CLANS,
        )

    clan_buy_improvement_action = ClanManageAction(
        type=ClanManageActionEnum.BUY_IMPOVEMENT,
        after=CLAN_IMPROVEMENTS[iindex],  # type: ignore
    )

    dto = ClanManageNotifyDTO(
        guild=guild,
        event_type="clan_manage_notify",
        actor_id=interaction.user.id,
        clan_name=clan_member.clan.name,  # type: ignore The clan will always exist here because of the checks on lines 64 and 125
        actions=[clan_buy_improvement_action],
        logging_webhook=clans_logging_channel,
    )

    bot.dispatch("clan_manage_notify", dto)

    await interaction.response.send_message(
        view=SuccessViewV2(
            "Успешное улучшение клана",
            "Улучшение клана применено успешно.",
        ),
        ephemeral=True,
    )
    return
