"""Permissions enums for the bot."""

from enum import Enum


class PermissionsFlagEnum(str, Enum):
    """Enum representing permission flags."""

    NONE = "nonetype"
    BOT_ACCESS = "bot_access"
    ADMINISTRATOR = "administrator"
    HEAD_MODERATION_ACCESS = "head_moderation_access"
    MODERATION_ACCESS = "moderation_access"
    ECONOMY_ACCESS = "economy_access"
    CLANS_ACCESS = "clans_access"
