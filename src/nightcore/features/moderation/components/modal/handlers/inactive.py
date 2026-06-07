"""Handlers for inactive modals."""

import logging
from typing import TYPE_CHECKING, cast

from discord.interactions import Interaction

from src.infra.db.models._enums import InactiveRequestStateEnum
from src.nightcore.features.moderation.utils.content import (
    parse_author_id_from_components,
    parse_inactive_text_from_components,
    parse_nickname_from_components,
)
from src.nightcore.utils.object import cast_guild, cast_message

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.components.embed import ErrorEmbed

from ..inactive import InactiveRequestViewV2

logger = logging.getLogger(__name__)


async def handle_inactive_reject_modal_submit(
    interaction: Interaction["Nightcore"],
):
    """Handle the reject modal submit button interaction."""

    bot = interaction.client
    guild = cast_guild(interaction.guild)
    message = cast_message(interaction.message)

    author_id = parse_author_id_from_components(message.components)
    if not author_id:
        logger.error(
            "[inactive] Failed to parse author ID from message components for guild=%s, message_id=%s",  # noqa: E501
            guild.id,
            message.id,
        )
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка отправки запроса не неактив",
                "Не удалось определить автора запроса на неактив.",
                bot.user.name,
                bot.user.display_avatar.url,
            ),
            ephemeral=True,
        )

    inactive_message = parse_inactive_text_from_components(message.components)
    if not inactive_message:
        logger.error(
            "[inactive] Failed to parse inactive message from message components for guild=%s, message_id=%s",  # noqa: E501
            guild.id,
            message.id,
        )
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка отправки запроса не неактив",
                "Не удалось определить текст запроса на неактив.",
                bot.user.name,
                bot.user.display_avatar.url,
            ),
            ephemeral=True,
        )
    nickname = parse_nickname_from_components(message.components)
    if not nickname:
        logger.error(
            "[inactive] Failed to parse nickname from message components for guild=%s, message_id=%s",  # noqa: E501
            guild.id,
            message.id,
        )
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка отправки запроса не неактив",
                "Не удалось определить никнейм в запросе на неактив.",
                bot.user.name,
                bot.user.display_avatar.url,
            ),
            ephemeral=True,
        )

    reason = cast(
        str,
        interaction.data["components"][0]["components"][0]["value"],  # type: ignore
    )

    view = InactiveRequestViewV2(
        bot=bot,
        author_id=author_id,
        message=inactive_message,
        state=InactiveRequestStateEnum.DENIED,
        user_answer_id=interaction.user.id,
        answer=reason,
    )

    try:
        await message.edit(view=view)
    except Exception:
        logger.exception(
            "[inactive] Failed to edit message with rejection view for guild=%s, message_id=%s",  # noqa: E501
            guild.id,
            message.id,
        )
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка отправки запроса не неактив",
                "Не удалось обновить сообщение с результатом отклонения.",
                bot.user.name,
                bot.user.display_avatar.url,
            ),
            ephemeral=True,
        )

    await interaction.response.send_message(
        "Заявление на неактив отклонено.",
        ephemeral=True,
    )
