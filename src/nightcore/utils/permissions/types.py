"""Permissions enums for the bot."""

from enum import Enum

from src.infra.db.models import (
    GuildClansConfig,
    GuildEconomyConfig,
    GuildMetaConfig,
    GuildModerationConfig,
)


class PermissionsFlagEnum(str, Enum):
    """Enum representing permission flags."""

    NONE = "nonetype"
    BOT_ACCESS = "bot_access"
    OTHER_CONFIG_ACCESS = "config_access"
    CLANS_CONFIG_ACCESS = "clans_config_access"
    ECONOMY_CONFIG_ACCESS = "economy_config_access"
    MODERATION_CONFIG_ACCESS = "moderation_config_access"
    LOGGING_CONFIG_ACCESS = "logging_config_access"
    LEVELS_CONFIG_ACCESS = "levels_config_access"
    NOTIFICATIONS_CONFIG_ACCESS = "notifications_config_access"
    PRIVATE_CHANNELS_CONFIG_ACCESS = "private_channels_config_access"
    INFOMAKER_CONFIG_ACCESS = "infomaker_config_access"
    ADMINISTRATOR = "administrator"
    HEAD_MODERATION_ACCESS = "head_moderation_access"
    MODERATION_ACCESS = "moderation_access"
    ECONOMY_ACCESS = "economy_access"
    CLANS_ACCESS = "clans_access"
    BAN_ACCESS = "ban_access"
    UNSAFE = "unsafe"


PERMISSION_CONFIG_MAP: dict[PermissionsFlagEnum, tuple[type, str, str]] = {
    PermissionsFlagEnum.CLANS_ACCESS: (
        GuildClansConfig,
        "clans_access_roles_ids",
        "доступ к кланам",
    ),
    PermissionsFlagEnum.MODERATION_ACCESS: (
        GuildModerationConfig,
        "moderation_access_roles_ids",
        "доступ к модерации",
    ),
    PermissionsFlagEnum.BAN_ACCESS: (
        GuildModerationConfig,
        "ban_access_roles_ids",
        "доступ к бану",
    ),
    PermissionsFlagEnum.HEAD_MODERATION_ACCESS: (
        GuildModerationConfig,
        "leadership_access_roles_ids",
        "доступ к главной модерации",
    ),
    PermissionsFlagEnum.ECONOMY_ACCESS: (
        GuildEconomyConfig,
        "economy_access_roles_ids",
        "доступ к экономике",
    ),
    PermissionsFlagEnum.OTHER_CONFIG_ACCESS: (
        GuildMetaConfig,
        "other_config_access_roles_ids",
        "доступ к настройке остальной конфигурации",
    ),
    PermissionsFlagEnum.LOGGING_CONFIG_ACCESS: (
        GuildMetaConfig,
        "logging_config_access_roles_ids",
        "доступ к настройке системы логов",
    ),
    PermissionsFlagEnum.ECONOMY_CONFIG_ACCESS: (
        GuildMetaConfig,
        "economy_config_access_roles_ids",
        "доступ к настройке системы экономики",
    ),
    PermissionsFlagEnum.LEVELS_CONFIG_ACCESS: (
        GuildMetaConfig,
        "levels_config_access_roles_ids",
        "доступ к настройке системы уровней",
    ),
    PermissionsFlagEnum.NOTIFICATIONS_CONFIG_ACCESS: (
        GuildMetaConfig,
        "notifications_config_access_roles_ids",
        "доступ к настройке системы уведомлений",
    ),
    PermissionsFlagEnum.PRIVATE_CHANNELS_CONFIG_ACCESS: (
        GuildMetaConfig,
        "private_channels_config_access_roles_ids",
        "доступ к настройке системы приватных каналов",
    ),
    PermissionsFlagEnum.INFOMAKER_CONFIG_ACCESS: (
        GuildMetaConfig,
        "infomaker_config_access_roles_ids",
        "доступ к настройке системы инфомейкера",
    ),
    PermissionsFlagEnum.CLANS_CONFIG_ACCESS: (
        GuildMetaConfig,
        "clans_config_access_roles_ids",
        "доступ к настройке системы кланов",
    ),
    PermissionsFlagEnum.MODERATION_CONFIG_ACCESS: (
        GuildMetaConfig,
        "moderation_config_access_roles_ids",
        "доступ к настройке системы модерации",
    ),
}
