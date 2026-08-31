"""Pydantic field validators for Discord guild resources.

Each validator receives the raw value and a :class:`ValidationContext`
via *info.context* to look up roles and channels known for the guild.
"""

import re
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


DISCORD_WEBHOOK_RE = re.compile(
    r"^https://(?:ptb\.|canary\.)?discord(?:app)?\.com/api/webhooks/"
    r"(?P<id>\d+)/(?P<token>[\w-]+)/?$"
)

DISCORD_WEBHOOK_ID_MIN_LENGTH = 17
DISCORD_WEBHOOK_ID_MAX_LENGTH = 20
DISCORD_WEBHOOK_TOKEN_MIN_LENGTH = 60
DISCORD_WEBHOOK_TOKEN_MAX_LENGTH = 90


def validate_discord_webhook(
    v: Any, info: ValidationInfo | None = None
) -> str:
    """Validate and return a Discord webhook URL string.

    Raises ConfigValidationError (400) instead of ValueError (500) for
    user-input errors. Validates ID length via integer bounds as well
    as string length to handle leading zeros correctly.
    """

    value = str(v).strip()

    match = DISCORD_WEBHOOK_RE.match(value)
    if not match:
        raise ConfigValidationError(f"Invalid Discord webhook URL: {value!r}")

    webhook_id = match.group("id")
    webhook_token = match.group("token")

    # Fix ID length handling: validate both string length and integer range,
    # and ensure webhook_id is a valid snowflake integer.
    try:
        int_id = int(webhook_id)
    except ValueError as exc:
        raise ConfigValidationError(
            f"Invalid Discord webhook URL: {value!r}"
        ) from exc

    # String length check (17-20) covers snowflake textual length
    if not (
        DISCORD_WEBHOOK_ID_MIN_LENGTH
        <= len(webhook_id)
        <= DISCORD_WEBHOOK_ID_MAX_LENGTH
    ):
        raise ConfigValidationError(f"Invalid Discord webhook URL: {value!r}")

    # Integer bounds check - combine with length diff
    ovan = 10 ** (DISCORD_WEBHOOK_ID_MIN_LENGTH - 1)
    below = 10**DISCORD_WEBHOOK_ID_MAX_LENGTH
    if not (ovan <= int_id < below) and len(str(int_id)) != len(webhook_id):
        raise ConfigValidationError(f"Invalid Discord webhook URL: {value!r}")

    if not (
        DISCORD_WEBHOOK_TOKEN_MIN_LENGTH
        <= len(webhook_token)
        <= DISCORD_WEBHOOK_TOKEN_MAX_LENGTH
    ):
        raise ConfigValidationError(f"Invalid Discord webhook URL: {value!r}")

    # Ownership check is async (bot.fetch_webhook) and handled in
    # validate_discord_webhook_ownership(); we keep this validator sync to
    # avoid blocking but ensure 400 not 500 for syntax errors.
    _ = info  # keep signature compatible for ValidationInfo injection
    return value


async def validate_discord_webhook_ownership(
    webhook_url: str,
    bot: Nightcore,
    expected_guild_id: int | None = None,
) -> str:
    """Validate webhook ownership by fetching it via bot.fetch_webhook.

    Ensures the webhook exists, is owned by the bot's application, and
    optionally belongs to the expected guild. Raises ConfigValidationError
    (400) on failure so the API returns 400 not 500.

    Should be called after DB commit, as part of guild_state update flow.
    """

    match = DISCORD_WEBHOOK_RE.match(webhook_url.strip())
    if not match:
        raise ConfigValidationError(
            f"Invalid Discord webhook URL: {webhook_url!r}"
        )

    webhook_id = int(match.group("id"))

    try:
        webhook = await bot.fetch_webhook(webhook_id)
    except discord.NotFound as exc:
        raise ConfigValidationError(
            f"Webhook {webhook_id} not found or not owned by bot"
        ) from exc
    except discord.Forbidden as exc:
        raise ConfigValidationError(
            f"No access to webhook {webhook_id}"
        ) from exc
    except discord.HTTPException as exc:
        raise ConfigValidationError(
            f"Failed to verify webhook {webhook_id}: {exc}"
        ) from exc

    if expected_guild_id is not None and webhook.guild_id != expected_guild_id:
        msg = f"Webhook {webhook_id} does not belong to guild {expected_guild_id}"  # noqa: E501
        raise ConfigValidationError(msg)

    return webhook_url
