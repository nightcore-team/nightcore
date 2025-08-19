"""Enumeration for types."""

from enum import Enum

from src.infra.db.models.guild import (
    GuildLoggingConfig,
)


class LoggingChannelType(Enum):
    """Enumeration for logging channel types."""

    REACTIONS = GuildLoggingConfig.reactions_log_channel_id
    MESSAGES = GuildLoggingConfig.messages_log_channel_id
    IGNORE = GuildLoggingConfig.message_log_ignoring_channels_ids
