"""Utility functions for logging events."""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore
    from src.nightcore.events.dto.base import BaseEventDTO

from src.nightcore.utils import ensure_messageable_channel_exists

logger = logging.getLogger(__name__)


async def send_log_message(
    bot: "Nightcore",
    dto: "BaseEventDTO",
):
    """Send a log message based on the provided DTO."""
    embed = dto.build_log_embed(bot)

    if not dto.logging_channel_id:
        logger.error(
            "[%s/log] No logging channel configured for guild %s",
            dto.event_type,
            dto.guild.id,
        )
        return None

    channel = await ensure_messageable_channel_exists(
        dto.guild, dto.logging_channel_id
    )  # type: ignore
    if not channel:
        logger.error(
            "[%s/log] Logging channel with ID %s not found in guild %s",
            dto.event_type,
            dto.logging_channel_id,
            dto.guild.id,
        )
        return None

    try:
        await channel.send(embed=embed)  # type: ignore
    except Exception as e:
        logger.exception(
            "[%s/log] Failed to send log message to channel %s in guild %s: %s",  # noqa: E501
            dto.event_type,
            channel.id,
            dto.guild.id,
            e,
        )
        return None
