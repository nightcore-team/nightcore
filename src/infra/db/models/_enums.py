"""Enumeration for types."""

from enum import Enum


class ChannelType(Enum):
    """Enumeration for channel types."""

    NOTIFICATIONS = "notifications_channel_id"
    NIGHTCORE_NOTIFICATIONS = "notifications_from_bot_channel_id"
    LOGGING_BANS = "bans_log_channel_id"
    LOGGING_CLANS = "clans_log_channel_id"
    LOGGING_MEMBERS = "members_log_channel_id"
    LOGGING_MESSAGES = "messages_log_channel_id"
    LOGGING_VOICES = "voices_log_channel_id"
    LOGGING_MODERATION = "moderation_log_channel_id"
    LOGGING_TICKETS = "tickets_log_channel_id"
    LOGGING_ROLES = "roles_log_channel_id"
    LOGGING_CHANNELS = "channels_log_channel_id"
    LOGGING_REACTIONS = "reactions_log_channel_id"
    LOGGING_PRIVATE_CHANNELS = "private_rooms_log_channel_id"
    LOGGING_IGNORE = "message_log_ignoring_channels_ids"
    NEW_TICKETS_CATEGORY = "new_tickets_category_id"
    CLOSED_TICKETS_CATEGORY = "closed_tickets_category_id"
    PINNED_TICKETS_CATEGORY = "pinned_tickets_category_id"

    ROLE_REQUESTS = "check_role_requests_channel_id"


class TicketStateEnum(Enum):
    OPENED = "opened"
    PINNED = "pinned"
    CLOSED = "closed"
    DELETED = "deleted"


class RoleRequestStateEnum(Enum):
    PENDING = "pending"
    REQUESTED = "requested"
    APPROVED = "approved"
    DENIED = "denied"
    STATS_PROVIDED = "has_stats"
