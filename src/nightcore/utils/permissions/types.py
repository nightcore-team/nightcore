"""Permissions enums for the bot."""

from enum import Enum

from src.infra.db.models import (
    GuildClansConfig,
    GuildEconomyConfig,
    GuildModerationConfig,
)


class PermissionsFlagEnum(str, Enum):
    """Enum representing permission flags."""

    NONE = "nonetype"
    BOT_ACCESS = "bot_access"
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
}
