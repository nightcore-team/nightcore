"""Command to remove a VIP-status from a user."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Forbidden, Guild, HTTPException, User, app_commands
from discord.interactions import Interaction

from src.infra.db.loads import vip_status_load_vip
from src.infra.db.models import GuildEconomyConfig, GuildLoggingConfig
from src.infra.db.operations import (
    accrue_deposit_interest_if_due,
    get_or_create_bank_account,
    get_or_create_user,
    get_specified_webhook,
    get_user_vip_statuses_for_update,
)
from src.nightcore.components.view.v2 import ErrorViewV2, SuccessViewV2
from src.nightcore.features.economy._groups import remove as remove_group
from src.nightcore.features.economy.events.dto import AwardNotificationEventDTO
from src.nightcore.features.economy.utils.autocomplete import (
    get_user_vip_statuses_autocomplete,
)
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils import ensure_member_exists, ensure_role_exists
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)
from src.nightcore.utils.transformers.str_to_int import StrToIntTransformer
from src.utils._enums import ChannelType

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


@remove_group.command(
    name="vip", description="Удалить VIP-status у пользователя"
)  # type: ignore
@app_commands.describe(
    user="Пользователь, у которого удаляется VIP-status.",
    vip_id="VIP-status для удаления.",
    reason="Причина удаления VIP-status (необязательно).",
)
@app_commands.autocomplete(vip_id=get_user_vip_statuses_autocomplete)
@app_commands.rename(vip_id="vip")
@check_required_permissions(PermissionsFlagEnum.ECONOMY_ACCESS)
async def remove_vip(
    interaction: Interaction["Nightcore"],
    user: User,
    vip_id: app_commands.Transform[int, StrToIntTransformer],
    reason: str | None = None,
):
    """Remove a VIP-status from a user."""

    guild = cast(Guild, interaction.guild)
    bot = interaction.client
    outcome = ""
    vip_name = ""
    role_id: int | None = None

    if user == bot.user:
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка удаления VIP-status",
                "Невозможно удалить VIP-status у бота.",
            ),
            ephemeral=True,
        )
        return

    await interaction.response.defer(ephemeral=True, thinking=True)

    logging_webhook = None

    try:
        async with specified_guild_config(
            bot,
            guild_id=guild.id,
            config_type=GuildEconomyConfig,
        ) as (guild_config, session):
            logging_webhook = await get_specified_webhook(
                session,
                guild_id=guild.id,
                config_type=GuildLoggingConfig,
                channel_type=ChannelType.LOGGING_ECONOMY,
            )
            user_record, _ = await get_or_create_user(
                session, guild_id=guild.id, user_id=user.id
            )

            # lock order: bankaccount -> deposit -> vip status rows.
            # The deposit is accrued before the VIP rows are locked so
            # this path doesn't invert the order used by every other
            # one, and the accrual still sees the VIP that is about to
            # be removed. user is a discord.User here, so the row id has
            # to be resolved before it can be used against bankaccount
            # and uservipstatus.
            bank_account, _ = await get_or_create_bank_account(
                session,
                guild_id=guild.id,
                user_id=user_record.id,
                for_update=True,
            )

            assert bank_account.deposit is not None

            await accrue_deposit_interest_if_due(
                session,
                deposit=bank_account.deposit,
                guild_id=guild.id,
                user_id=user_record.id,
                config=guild_config,
            )

            user_vip_statuses = await get_user_vip_statuses_for_update(
                session,
                guild_id=guild.id,
                user_id=user_record.id,
                options=[vip_status_load_vip],
                for_update=True,
            )
            target = next(
                (
                    status
                    for status in user_vip_statuses
                    if status.vip_id == vip_id
                ),
                None,
            )

            if target is None:
                outcome = "does_not_have_vip"
            else:
                vip_name = target.vip.name
                role_id = target.vip.role_id

                await session.delete(target)

                outcome = "success"

    except Exception as e:
        logger.exception(
            "[remove/vip] Error removing VIP-status %s from user %s in guild %s: %s",  # noqa: E501
            vip_id,
            user.id,
            guild.id,
            e,
        )
        outcome = "remove_vip_error"

    if outcome == "does_not_have_vip":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка удаления VIP-status'a",
                "У пользователя нет этого VIP-status'a.",
            ),
        )
        return

    if outcome == "remove_vip_error":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка удаления VIP-status'a",
                "Не удалось удалить VIP-status у пользователя.",
            ),
        )
        return

    role_removed = True

    if role_id is not None:
        role = await ensure_role_exists(guild, role_id)
        member = await ensure_member_exists(guild, user.id)

        if role is None or member is None:
            role_removed = False
        else:
            try:
                await member.remove_roles(
                    role, reason="VIP-status removed via economy command."
                )
            except (Forbidden, HTTPException) as error:
                role_removed = False
                logger.warning(
                    "[remove/vip] Failed to remove role %s from user %s: %s",
                    role_id,
                    user.id,
                    error,
                )

    message = (
        f"VIP-status **{vip_name}** удален у пользователя <@{user.id}>.\n"
    )
    if not role_removed:
        message += "> Не удалось забрать роль VIP-status'a."

    await interaction.followup.send(
        view=SuccessViewV2("Удаление VIP-status", message),
    )

    bot.dispatch(
        "user_items_changed",
        dto=AwardNotificationEventDTO(
            guild=guild,
            event_type="remove/vip",
            logging_webhook=logging_webhook,
            user_id=user.id,
            moderator_id=interaction.user.id,
            item_name=vip_name,
            amount=-1,
            duration=None,
            reason=reason,
        ),
    )
