"""Enumeration for types."""

from enum import Enum


class ChannelType(Enum):
    """Enumeration for channel types."""

    NOTIFICATIONS = "notifications_channel_id"
    NIGHTCORE_NOTIFICATIONS = "notifications_from_bot_channel_id"
    MODERATION_NOTIFICATIONS = "notifications_for_moderation_channel_id"

    LOGGING_ECONOMY = "economy_log_channel_id"
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
    CREATE_TICKETS = "create_ticket_channel_id"

    CREATE_PROPOSALS = "create_proposal_channel_id"

    CREATE_PRIVATE_VOICE_CHANNEL = "private_rooms_create_channel_id"

    ROLE_REQUESTS = "check_role_requests_channel_id"
    RULES_CHANNEL = "rules_channel_id"

    COUNT_MESSAGES = "count_messages_channel_id"

    COUNT_MODERATION_MESSAGES = "count_moderator_messages_channel_id"


class FieldTypeEnum(Enum):
    CLANS_ACCESS = "clans_access_roles_ids"


class TicketStateEnum(Enum):
    OPENED = "opened"
    PINNED = "pinned"
    CLOSED = "closed"
    DELETED = "deleted"


class RoleRequestStateEnum(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    CANCELED = "canceled"
    EXPIRED = "expired"
    REMOVED = "removed"


class NotifyStateEnum(Enum):
    PENDING = "pending"
    TIMED_OUT = "timed_out"


class ClanMemberRoleEnum(Enum):
    LEADER = "leader"
    DEPUTY = "deputy"
    MEMBER = "member"


class ShopOrderStateEnum(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"


class MultiplierTypeEnum(Enum):
    EXP = "exp"
    COINS = "coins"


class ChangeStatTypeEnum(Enum):
    BAN = "ban"
    KICK = "kick"
    MUTE = "mute"
    VMUTE = "vmute"
    MPMUTE = "mpmute"
    TICKETBAN = "ticketban"
    TICKET = "ticket"
    ROLE_REMOVE = "role_remove"
    ROLE_ACCEPT = "role_accept"
