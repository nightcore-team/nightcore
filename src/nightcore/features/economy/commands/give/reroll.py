"""Command to give rerolls to a user."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, User, app_commands
from discord.interactions import Interaction

from src.infra.db.models import GuildLoggingConfig
from src.infra.db.operations import get_or_create_user, get_specified_webhook
from src.nightcore.components.view.v2 import ErrorViewV2, SuccessViewV2
from src.nightcore.features.economy._groups import give as give_group
from src.nightcore.features.economy.events.dto import (
    AwardNotificationEventDTO,
)
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)
from src.utils._enums import ChannelType

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


@give_group.command(name="reroll", description="Выдать рероллы пользователю")  # type: ignore
@check_required_permissions(PermissionsFlagEnum.ECONOMY_ACCESS)
@app_commands.describe(
    user="Пользователь, которому выдаются рероллы",
    amount="Количество рероллов для выдачи",
    reason="Причина выдачи рероллов (необязательно)",
)
async def give_reroll(
    interaction: Interaction["Nightcore"],
    user: User,
    amount: int,
    reason: str | None = None,
):
    """Give rerolls to a user."""

    guild = cast(Guild, interaction.guild)
    bot = interaction.client

    outcome = ""

    if user == bot.user:
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка выдачи рероллов",
                "Невозможно выдать рероллы боту.",
            ),
            ephemeral=True,
        )
        return

    await interaction.response.defer(ephemeral=True, thinking=True)

    async with bot.uow.start() as session:
        logging_webhook = await get_specified_webhook(
            session,
            guild_id=guild.id,
            config_type=GuildLoggingConfig,
            channel_type=ChannelType.LOGGING_ECONOMY,
        )

        if not outcome:
            try:
                user_record, _ = await get_or_create_user(
                    session,
                    guild_id=guild.id,
                    user_id=user.id,
                    for_update=True,
                )
                user_record.rerolls += amount
                outcome = "success"

            except Exception as e:
                logger.exception(
                    "[give/reroll] Failed to give rerolls to user %s in guild %s: %s",  # noqa: E501
                    user.id,
                    guild.id,
                    e,
                )
                outcome = "give_reroll_error"

    if outcome == "give_reroll_error":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка выдачи рероллов",
                "Не удалось выдать рероллы пользователю.",
            ),
        )
        return

    if outcome == "success":
        await interaction.followup.send(
            view=SuccessViewV2(
                "Выдача рероллов успешна",
                f"Вы успешно выдали пользователю <@{user.id}> "
                f"**{amount} рероллов**.",
            ),
        )

        bot.dispatch(
            "user_items_changed",
            dto=AwardNotificationEventDTO(
                guild=guild,
                event_type="give/reroll",
                logging_webhook=logging_webhook,
                user_id=user.id,
                moderator_id=interaction.user.id,
                item_name="рероллы",
                amount=amount,
                reason=reason,
            ),
        )
