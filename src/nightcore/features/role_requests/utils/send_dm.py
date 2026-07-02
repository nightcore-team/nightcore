"""Utilities for sending DMs related to role requests."""

import logging
from typing import TYPE_CHECKING

import discord
from discord import Member

from src.nightcore.utils.webhook import send_to_webhook
from src.utils._enums import RoleRequestStateEnum

if TYPE_CHECKING:
    from src.infra.db.models.discord_webhook import DiscordWebhook
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)

APPROVED_MESSAGE = """
<:check:1442915033079353404> | APPROVED <:42920arrowrightalt:1442924551880314921> <@{user_id}>, модератор <@{moderator_id}> одобрил ваш запрос на получение роли.
"""  # noqa: E501

DENIED_MESSAGE = """
<:failed:1442915170320912506> | DENIED <:42920arrowrightalt:1442924551880314921> <@{user_id}>, модератор <@{moderator_id}> отклонил ваш запрос на получение роли.

Причина: {reason}
"""  # noqa: E501


async def send_role_request_dm(
    bot: "Nightcore",
    moderator_id: int,
    reserve_webhook: "DiscordWebhook | None",
    user: Member,
    state: RoleRequestStateEnum,
    reason: str | None = None,
) -> None:
    """Send a DM to the user about their role request status.

    Falls back to ``reserve_webhook`` if the user has DMs disabled.
    """
    match state:
        case RoleRequestStateEnum.APPROVED:
            message = APPROVED_MESSAGE.format(
                user_id=user.id, moderator_id=moderator_id
            )
        case RoleRequestStateEnum.DENIED:
            message = DENIED_MESSAGE.format(
                user_id=user.id,
                moderator_id=moderator_id,
                reason=reason,
            )
        case _:
            return

    try:
        await user.send(message)
        return
    except discord.Forbidden:
        logger.info(
            "[%s/log] Failed to send private message for user %s in guild %s because he doesn't accept DM",  # noqa: E501
            "role_request",
            user.id,
            user.guild.id,
        )
    except Exception as e:
        logger.warning(
            "[%s/log] Failed to send private message for user %s in guild %s: %s",  # noqa: E501
            "role_request",
            user.id,
            user.guild.id,
            e,
        )

    if not reserve_webhook or not reserve_webhook.valid:
        return

    await send_to_webhook(
        bot,
        reserve_webhook,
        discord.Embed(description=message),
        context="role_request/dm_fallback",
        guild_id=user.guild.id,
    )
