"""Pydantic field validators for Discord guild resources.

Each validator receives the raw value and a :class:`ValidationContext`
via *info.context* to look up roles and channels known for the guild.
"""

from dataclasses import dataclass
from typing import Any

import discord
from pydantic import (
    ValidationInfo,
)

from src.nightcore.api.domain.exceptions.base import ConfigValidationError
from src.nightcore.bot import Nightcore


@dataclass
class ValidationContext:
    """Context passed to every Pydantic validator via ``info.context``.

    Attributes:
        guild_id: The Discord guild (server) ID being validated against.
        roles: Mapping of role ID → role info known for the guild.
        channels: Mapping of channel ID → channel info known for the guild.
    """

    bot: Nightcore
    interaction_member: discord.Member


def validate_role_id(v: Any, info: ValidationInfo) -> int:
    """Validate that *v* is a role ID known in the guild.

    Args:
        v: Raw value to validate (cast to ``int`` internally).
        info: Pydantic validation info carrying the
            :class:`ValidationContext` in *info.context*.

    Returns:
        The validated integer role ID.

    Raises:
        ValueError: If the role is not found in the context.
    """

    value = int(v)
    ctx = info.context

    if not isinstance(ctx, ValidationContext):
        raise ValueError("Invalid validation context")

    guild = ctx.interaction_member.guild

    role = guild.get_role(value)

    if not role:
        raise ValueError(f"Роль {value} не найдена в гильдии {guild.id}")

    return value


def validate_role_no_adm_id(v: Any, info: ValidationInfo) -> int:
    """Validate *v* is a non-administrator role ID.

    Args:
        v: Raw value to validate (cast to ``int`` internally).
        info: Pydantic validation info carrying the
            :class:`ValidationContext` in *info.context*.

    Returns:
        The validated integer role ID.

    Raises:
        ValueError: If the role is not found, or if the role has
            ``administrator`` set to ``True``.
    """

    value = int(v)
    ctx = info.context

    if not isinstance(ctx, ValidationContext):
        raise ValueError("Invalid validation context")

    guild = ctx.interaction_member.guild

    role = guild.get_role(value)

    if not role:
        raise ValueError(f"Роль {value} не найдена в гильдии {guild.id}")

    if role.permissions.administrator:
        raise ValueError(
            "Нельзя использовать роль с правами администратора для этого поля"
        )

    return value


def validate_text_channel_id(v: Any, info: ValidationInfo) -> int:
    """Validate *v* is a text channel ID known in the guild.

    Args:
        v: Raw value to validate (cast to ``int`` internally).
        info: Pydantic validation info carrying the
            :class:`ValidationContext` in *info.context*.

    Returns:
        The validated integer channel ID.

    Raises:
        ValueError: If the channel is not found.
        ConfigValidationError: If the channel type is not ``"text"``.
    """

    value = int(v)
    ctx = info.context

    if not isinstance(ctx, ValidationContext):
        raise ValueError("Invalid validation context")

    guild = ctx.interaction_member.guild

    channel = guild.get_channel(value)

    if not channel:
        raise ValueError(f"Канал {value} не найден в гильдии {guild.id}")

    if channel.type != discord.ChannelType.text:
        raise ConfigValidationError("Ожидался канал с типом текстовый")

    return value


def validate_voice_channel_id(v: Any, info: ValidationInfo) -> int:
    """Validate *v* is a voice channel ID known in the guild.

    Args:
        v: Raw value to validate (cast to ``int`` internally).
        info: Pydantic validation info carrying the
            :class:`ValidationContext` in *info.context*.

    Returns:
        The validated integer channel ID.

    Raises:
        ConfigValidationError: If the channel is not found, or if its
            type is not ``"voice"``.
    """

    value = int(v)
    ctx = info.context

    if not isinstance(ctx, ValidationContext):
        raise ValueError("Invalid validation context")

    guild = ctx.interaction_member.guild

    channel = guild.get_channel(value)

    if not channel:
        raise ValueError(f"Канал {value} не найден в гильдии {guild.id}")

    if channel.type != discord.ChannelType.voice:
        raise ConfigValidationError("Ожидался канал с типом голосовой")

    return value


def validate_category_id(v: Any, info: ValidationInfo) -> int:
    """Validate *v* is a category channel ID known in the guild.

    Args:
        v: Raw value to validate (cast to ``int`` internally).
        info: Pydantic validation info carrying the
            :class:`ValidationContext` in *info.context*.

    Returns:
        The validated integer channel ID.

    Raises:
        ConfigValidationError: If the channel is not found, or if its
            type is not ``"category"``.
    """

    value = int(v)
    ctx = info.context

    if not isinstance(ctx, ValidationContext):
        raise ValueError("Invalid validation context")

    guild = ctx.interaction_member.guild

    channel = guild.get_channel(value)

    if not channel:
        raise ValueError(f"Канал {value} не найден в гильдии {guild.id}")

    if channel.type != discord.ChannelType.category:
        raise ConfigValidationError("Ожидался канал с типом категория")

    return value
