"""Enumeration for types."""

from enum import Enum


class LoggingChannelType(Enum):
    """Enumeration for logging channel types."""

    BANS = "bans_log_channel_id"
    CLANS = "clans_log_channel_id"
    MEMBERS = "members_log_channel_id"
    MESSAGES = "messages_log_channel_id"
    VOICES = "voices_log_channel_id"
    MODERATION = "moderation_log_channel_id"
    TICKETS = "tickets_log_channel_id"
    ROLES = "roles_log_channel_id"
    CHANNELS = "channels_log_channel_id"
    REACTIONS = "reactions_log_channel_id"
    PRIVATE_CHANNELS = "private_rooms_log_channel_id"
    IGNORE = "message_log_ignoring_channels_ids"
