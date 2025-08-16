"""Enumeration for types."""

from enum import Enum

from src.infra.db.models.guild import GuildConfig


class LoggingChannelType(Enum):
    """Enumeration for logging channel types."""

    REACTIONS = GuildConfig.reactions_log_channel_id
    MESSAGES = GuildConfig.messages_log_channel_id
    IGNORE = GuildConfig.message_log_ignoring_channels_ids
