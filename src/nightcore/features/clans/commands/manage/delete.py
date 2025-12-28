"""Clan deletion command."""

import asyncio
import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, app_commands
from discord.interactions import Interaction

from src.infra.db.models._enums import ChannelType, ClanManageActionEnum
from src.infra.db.models.guild import GuildLoggingConfig
from src.infra.db.operations import get_clan_by_id, get_specified_channel
from src.nightcore.features.clans.events.dto.clan_manage_notify import (
    ClanManageAction,
    ClanManageNotifyDTO,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.components.embed import (
    ErrorEmbed,
    SuccessMoveEmbed,
)
from src.nightcore.features.clans._groups import manage as manage_clan_group
from src.nightcore.features.clans.utils import clans_autocomplete
from src.nightcore.utils import (
    ensure_role_exists,
    safe_delete_role,
)
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

logger = logging.getLogger(__name__)


@manage_clan_group.command(  # type: ignore
    name="delete", description="Удалить существующий клан."
)
@app_commands.describe(
    clan="Клан, который вы хотите удалить.",
)
@app_commands.autocomplete(clan=clans_autocomplete)
@check_required_permissions(PermissionsFlagEnum.CLANS_ACCESS)
async def delete(interaction: Interaction["Nightcore"], clan: str):
    """Delete an existing clan."""
    bot = interaction.client
    guild = cast(Guild, interaction.guild)
    try:
        clan_id = int(clan)
    except ValueError:
        await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка получения информации о клане",
                "Не удалось найти данный клан в базе данных.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )
        return

    await interaction.response.defer(ephemeral=True, thinking=True)

    outcome = ""
    clan_name = ""
    clan_role_id = 0

    async with bot.uow.start() as session:
        try:
            dbclan = await get_clan_by_id(
                session, guild_id=guild.id, clan_id=clan_id
            )

            if not dbclan:
                outcome = "clan_not_found"
            else:
                clan_name = dbclan.name
                clan_role_id = dbclan.role_id

                await session.delete(dbclan)
                await session.flush()

                outcome = "success"

        except Exception as e:
            logger.exception(
                "[clans] Failed to delete clan %s in guild %s: %s",
                clan,
                guild.id,
                e,
            )
            outcome = "database_error"

    if outcome == "clan_not_found":
        return await interaction.followup.send(
            embed=ErrorEmbed(
                "Ошибка удаления клана",
                "Не удалось найти данный клан в базе данных.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            )
        )

    if outcome == "database_error":
        return await interaction.followup.send(
            embed=ErrorEmbed(
                "Ошибка удаления клана",
                "Не удалось удалить клан из-за внутренней ошибки.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            )
        )

    if outcome == "success":
        role = await ensure_role_exists(guild, clan_role_id)
        if role:
            asyncio.create_task(safe_delete_role(role, "Удаление роли клана"))

        await interaction.followup.send(
            embed=SuccessMoveEmbed(
                "Удаление клана",
                f"Клан **{clan_name}** был успешно удален вместе с его участниками.",  # noqa: E501
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            )
        )

    async with bot.uow.start() as session:
        clans_logging_channel = await get_specified_channel(
            session,
            guild_id=guild.id,
            config_type=GuildLoggingConfig,
            channel_type=ChannelType.LOGGING_CLANS,
        )

    clan_delete_action = ClanManageAction(
        type=ClanManageActionEnum.DELETE,
    )

    dto = ClanManageNotifyDTO(
        guild=guild,
        event_type="clan_manage_notify",
        actor_id=interaction.user.id,
        clan_name=clan_name,  # type: ignore The clan_name will always exist here because of the checks on lines 64 and 84
        actions=[clan_delete_action],
        logging_channel_id=clans_logging_channel,
    )

    bot.dispatch("clan_manage_notify", dto)

    logger.info(
        "[command] - invoked user=%s guild=%s clan_name=%s deleted_clan=%s",
        interaction.user.id,
        guild.id,
        clan_name,
        clan,
        True,
    )
