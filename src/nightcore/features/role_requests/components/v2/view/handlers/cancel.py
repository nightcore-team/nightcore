"""Handle the cancel role request button interaction."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, Member
from discord.interactions import Interaction

from src.infra.db.operations import get_latest_user_role_request
from src.nightcore.components.view.v2 import ErrorViewV2, SuccessViewV2
from src.nightcore.utils import (
    ensure_message_exists,
    ensure_messageable_channel_exists,
)
from src.utils._enums import RoleRequestStateEnum

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

    from ..send_role_request import SendRoleRequestView

logger = logging.getLogger(__name__)


async def handle_cancel(
    interaction: Interaction["Nightcore"],
    view: "SendRoleRequestView",
) -> None:
    """Handle the cancel button interaction."""
    guild = cast(Guild, interaction.guild)
    user = cast(Member, interaction.user)

    await interaction.response.defer(thinking=True, ephemeral=True)

    outcome = ""
    channel_id = 0
    message_id = 0
    role_id = 0
    moderator_id: int | None = None

    async with view.bot.uow.start() as session:
        last_rr = await get_latest_user_role_request(
            session, guild_id=guild.id, user_id=user.id, for_update=True
        )

        if not last_rr or last_rr.state in (
            RoleRequestStateEnum.CANCELED,
            RoleRequestStateEnum.DENIED,
            RoleRequestStateEnum.APPROVED,
        ):
            outcome = "no_active_request"
        else:
            channel_id = last_rr.channel_id
            message_id = last_rr.message_id
            role_id = last_rr.role_id
            moderator_id = last_rr.moderator_id

            await session.delete(last_rr)

            outcome = "success"

    if outcome == "no_active_request":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка при отмене запроса",
                "У вас нет активных запросов на роль.",
            ),
        )
        return

    if outcome == "success":
        channel = await ensure_messageable_channel_exists(guild, channel_id)
        if not channel:
            await interaction.followup.send(
                view=ErrorViewV2(
                    "Ошибка при отмене запроса",
                    "Канал для проверки запросов на роль "
                    "не существует или недоступен.",
                ),
            )
            return

        rr_message = await ensure_message_exists(view.bot, channel, message_id)
        if not rr_message:
            await interaction.followup.send(
                view=ErrorViewV2(
                    "Ошибка при отмене запроса",
                    "Сообщение с вашим запросом на роль не найдено.",
                ),
            )
            return

        from ..check_role_request import CheckRoleRequestView

        try:
            message = await rr_message.edit(
                view=CheckRoleRequestView(
                    bot=view.bot,
                    interaction_user_id=user.id,
                    interaction_user_nick=user.display_name,
                    role_requested_id=role_id,
                    moderator_id=moderator_id,
                    state=RoleRequestStateEnum.CANCELED,
                    all_disabled=True,
                )
            )
        except Exception as e:
            logger.error(
                "Failed to update role request message %s in guild %s: %s",
                message_id,
                guild.id,
                e,
            )
            await interaction.followup.send(
                view=ErrorViewV2(
                    "Ошибка при отмене запроса",
                    "Произошла ошибка при обновлении "
                    "сообщения с вашим запросом на роль.",
                ),
            )
            return

        from ..role_request_state import RoleRequestStateView

        try:
            await message.reply(
                view=RoleRequestStateView(
                    bot=view.bot,
                    moderator_id=cast(int, moderator_id),
                    user_id=user.id,
                    state=RoleRequestStateEnum.CANCELED,
                    roles_ids=[role_id],
                )
            )
        except Exception as e:
            logger.error(
                "Failed to reply to role request message %s in guild %s: %s",
                message.id,
                guild.id,
                e,
            )
            await interaction.followup.send(
                view=ErrorViewV2(
                    "Ошибка при отмене запроса",
                    "Произошла ошибка при отправке сообщения "
                    "об отмене вашего запроса на роль.",
                )
            )
            return

        await interaction.followup.send(
            view=SuccessViewV2(
                "Запрос отменен",
                "Вы успешно отменили свой запрос на роль.",
            )
        )

        logger.info(
            "User %s canceled role request in guild %s",
            user.id,
            guild.id,
        )
