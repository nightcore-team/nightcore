"""Enumeration for types."""

from enum import Enum, StrEnum


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
    BATTLEPASS = "battlepass"


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
    NOTIFY = "notify"


class ComponentTypeEnum(Enum):
    EMBED = "embed"
    V2_COMPONENT = "v2_component"


class ClanManageActionEnum(Enum):
    CREATE = "Создание"
    DELETE = "Удаление"
    CHANGE_LEADER = "Изменение лидера"
    CHANGE_ROLE = "Изменение роли"
    CHANGE_NAME = "Изменение названия"
    CHANGE_CHANNEL = "Изменение канала"
    BUY_IMPOVEMENT = "Покупка улучшения"
    ADD_DEPUTY = "Добавление заместителя"
    REMOVE_DEPUTY = "Снятие заместителя"
    INVITE_MEMBER = "Приглашение участника"
    KICK_MEMBER = "Исключение участника"


class MetaConfigAccessTypeEnum(Enum):
    """Enumeration for meta config access types."""

    OTHER = "other_config_access_roles_ids"
    LOGGING = "logging_config_access_roles_ids"
    ECONOMY = "economy_config_access_roles_ids"
    LEVELS = "levels_config_access_roles_ids"
    CLANS = "clans_config_access_roles_ids"
    PRIVATE_CHANNELS = "private_channels_config_access_roles_ids"
    MODERATION = "moderation_config_access_roles_ids"
    NOTIFICATIONS = "notifications_config_access_roles_ids"
    INFOMAKER = "infomaker_config_access_roles_ids"

    @classmethod
    def all_values(cls) -> list[str]:
        """Get all enum values."""
        return [choice.value for choice in cls]

    @classmethod
    def from_choice(cls, choice: str) -> "MetaConfigAccessTypeEnum":
        """Get enum member from choice string."""
        mapping = {
            "clans": cls.CLANS,
            "economy": cls.ECONOMY,
            "levels": cls.LEVELS,
            "logging": cls.LOGGING,
            "moderation": cls.MODERATION,
            "notifications": cls.NOTIFICATIONS,
            "private_channels": cls.PRIVATE_CHANNELS,
            "other": cls.OTHER,
            "infomaker": cls.INFOMAKER,
        }
        return mapping[choice]

    @classmethod
    def choices(cls) -> list[tuple[str, str]]:
        """Get list of choices for Discord bot commands."""
        return [
            ("Кланы", "clans"),
            ("Экономика", "economy"),
            ("Уровни", "levels"),
            ("Логирование", "logging"),
            ("Модерация", "moderation"),
            ("Уведомления", "notifications"),
            ("Приватные каналы", "private_channels"),
            ("Другое", "other"),
            ("Инфомейкер", "infomaker"),
        ]


class CaseDropTypeEnum(Enum):
    EXP = 0
    COINS = 1
    COLOR = 3
    CASE = 4
    CUSTOM = 5
    BATTLEPASS_POINTS = 6

    def to_str(self):
        match self:
            case CaseDropTypeEnum.BATTLEPASS_POINTS:
                return "BP points"
            case CaseDropTypeEnum.EXP:
                return "опыт"
            case _:
                return self.name

    def requires_id(self) -> bool:
        return self == CaseDropTypeEnum.COLOR or self == CaseDropTypeEnum.CASE

    def requires_id_or_custom(self) -> bool:
        return (
            self == CaseDropTypeEnum.COLOR
            or self == CaseDropTypeEnum.CASE
            or self == CaseDropTypeEnum.CUSTOM
        )


class ItemChangeActionEnum(StrEnum):
    CREATE = "0"
    COLOR_UPDATE = "1"
    UPDATE_REWARD = "2"
    DELETE_REWARD = "3"
    ADD_REWARD = "4"
    CASE_UPDATE = "5"
    DELETE = "6"


class CasinoGameTypeEnum(Enum):
    ROULETTE = "roulette"


class CasinoPlayersTypeEnum(Enum):
    SINGLE = "single"
    MULTIPLAYER = "multiplayer"


class CasinoGameStateEnum(Enum):
    PENDING = "pending"
    FINISHED = "finished"


class CasinoBetResultTypeEnum(Enum):
    WIN = "win"
    LOSE = "lose"
