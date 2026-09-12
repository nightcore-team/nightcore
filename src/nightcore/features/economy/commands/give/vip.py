"""Command to give a VIP-status to a user."""

import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, cast

from discord import Guild, User, app_commands
from discord.interactions import Interaction

from src.infra.db.models import GuildEconomyConfig, GuildLoggingConfig
from src.infra.db.models.user import UserVipStatus
from src.infra.db.operations import (
    accrue_deposit_interest_if_due,
    get_or_create_bank_account,
    get_or_create_user,
    get_specified_webhook,
    get_user_vip_statuses_for_update,
    get_vip_status_by_id,
)
from src.nightcore.components.view.v2 import (
    ErrorViewV2,
    SuccessViewV2,
    ValidationErrorViewV2,
)
from src.nightcore.features.economy._groups import give as give_group
from src.nightcore.features.economy.events.dto import (
    AwardNotificationEventDTO,
)
from src.nightcore.features.economy.utils.autocomplete import (
    guild_vip_statuses_autocomplete,
)
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)
from src.nightcore.utils.time_utils import discord_ts, parse_duration
from src.nightcore.utils.transformers.str_to_int import StrToIntTransformer
from src.utils._enums import ChannelType

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


@give_group.command(name="vip", description="Выдать VIP-status пользователю")  # type: ignore
@app_commands.describe(
    user="Пользователь, которому выдается VIP-status.",
    case_id="VIP-status для выдачи.",
    duration="Срок действия VIP-status'a. Формат: s/m/h/d (например, 1h, 1d, 7d).",  # noqa: E501
    reason="Причина выдачи VIP-status'а.",
)
@app_commands.autocomplete(vip_id=guild_vip_statuses_autocomplete)
@app_commands.rename(vip_id="vip")
@check_required_permissions(PermissionsFlagEnum.ECONOMY_ACCESS)
async def give_vip(
    interaction: Interaction["Nightcore"],
    user: User,
    vip_id: app_commands.Transform[int, StrToIntTransformer],
    duration: app_commands.Range[str, 1, 20] | None = None,
    reason: str | None = None,
):
    """Give a case to user."""

    guild = cast(Guild, interaction.guild)
    bot = interaction.client

    if user == bot.user:
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка выдачи кейса",
                "Невозможно выдать кейс боту.",
            ),
            ephemeral=True,
        )
        return

    parsed_duration: int | None = None
    expires_at: datetime | None = None

    if duration:
        parsed_duration = parse_duration(duration)

        if not parsed_duration:
            await interaction.response.send_message(
                view=ValidationErrorViewV2(
                    "Неверная продолжительность. Используйте s/m/h/d (например, 1h, 1d, 7d).",  # noqa: E501
                ),
                ephemeral=True,
            )
            return

    if parsed_duration is not None:
        now = datetime.now(UTC)

        expires_at = now + timedelta(seconds=parsed_duration)

    await interaction.response.defer(ephemeral=True, thinking=True)

    outcome = ""

    try:
        async with specified_guild_config(
            interaction.client,
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

            vip_status_to_give = await get_vip_status_by_id(
                session, guild_id=guild.id, vip_id=vip_id
            )

            if vip_status_to_give is None:
                outcome = "unknown_vip_status"
            else:
                user_vip_statuses = await get_user_vip_statuses_for_update(
                    session,
                    guild_id=guild.id,
                    user_id=user_record.id,
                    for_update=True,
                )

                if not user_vip_statuses:
                    outcome = "success_with_new_unique"

                elif (
                    len(user_vip_statuses) + 1
                    > interaction.client.config.bot.MAX_USER_VIPS
                ):
                    outcome = "max_user_vips_limit_exceeded"

                needed_vip_id = 0
                if not outcome:
                    for idx, vip in enumerate(user_vip_statuses):
                        # check if user already has this vip status
                        if vip.id == vip_id:
                            # check if user has unlimited vip status
                            if vip.expires_at is None:
                                outcome = "already_has_unlimited"
                                break
                            else:
                                outcome = "success_with_extend"
                                needed_vip_id = idx
                                break

                        outcome = "success_with_new_unique"

                if (
                    outcome == "success_with_extend"
                    or outcome == "success_with_new_unique"
                ):
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
                        config=guild_config,
                        locked=False,
                    )

                if outcome == "success_with_extend":
                    needed_vip_status = user_vip_statuses[needed_vip_id]
                    needed_vip_status.expires_at = expires_at

                elif outcome == "success_with_new_unique":
                    session.add(
                        UserVipStatus(
                            user_id=user_record.id,
                            vip_id=vip_id,
                            expires_at=expires_at,
                        )
                    )

    except Exception as e:
        logger.exception(
            "[give/vip] Error giving VIP-status %s to user %s in guild %s: %s",
            vip_id,
            user.id,
            guild.id,
            e,
        )
        outcome = "give_vip_error"

    if outcome == "unknown_vip_status":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка выдачи VIP-status'a",
                "VIP-status не найден.",
            ),
        )
        return

    elif outcome == "give_vip_error":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка выдачи VIP-status'a",
                "Не удалось выдать VIP-status пользователю.",
            ),
        )
        return

    elif outcome == "max_user_vips_limit_exceeded":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка выдачи VIP-status'a",
                "Достигнуто максимальное количество доступных VIP-status'ов у пользователя.",  # noqa: E501
            ),
        )
        return

    elif outcome == "already_has_unlimited":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка выдачи VIP-status'a",
                "У пользователя уже есть данный VIP-status навсегда.",
            ),
        )
        return

    else:
        move = "продлили" if outcome == "success_with_extend" else "выдали"
        time_to = (
            "навсегда" if duration is None else f"до {discord_ts(expires_at)}",
        )

        await interaction.followup.send(
            view=SuccessViewV2(
                "Выдача VIP-статуса",
                f"Вы успешно {move} пользователю <@{user.id}> "
                f"VIP-статус **{vip_status_to_give.name}** {time_to}.",  # type: ignore
            ),
        )

        bot.dispatch(
            "user_items_changed",
            dto=AwardNotificationEventDTO(
                guild=guild,
                event_type="give/vip",
                logging_webhook=logging_webhook,  # type: ignore
                user_id=user.id,
                moderator_id=interaction.user.id,
                item_name=vip_status_to_give.name,  # type: ignore
                amount=1,
                duration=duration,
                reason=reason,
            ),
        )
