"""Utility functions for handling Discord members."""

import logging
from collections.abc import Sequence
from enum import Enum
from typing import TYPE_CHECKING

from discord import (
    Guild,
    HTTPException,
    Member,
    Message,
    NotFound,
    Role,
    TextChannel,
    Thread,
    User,
)
from discord.abc import GuildChannel, Messageable

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


async def ensure_role_exists(guild: Guild, role_id: int) -> Role | None:
    """Ensure that a role with the given ID exists in the guild."""
    role = guild.get_role(role_id)
    if role is None:
        try:
            role = await guild.fetch_role(role_id)
        except NotFound as e:
            logger.error(
                "[ensure_role_exists] Role %s not found in guild %s: %s",
                role_id,
                guild.id,
                e,
            )
            return None
        except HTTPException as e:
            logger.error(
                "[ensure_role_exists] Failed refetching role %s in guild %s: %s",  # noqa: E501
                role_id,
                guild.id,
                e,
            )
            return None
    return role


def ensure_channel_is_messageable(channel: GuildChannel | Thread) -> bool:
    """Check if a channel is messageable."""
    return isinstance(channel, TextChannel | Thread)


async def ensure_message_exists(
    bot: "Nightcore", channel: GuildChannel | Thread, message_id: int
) -> Message | None:
    """Ensure that a message with the given ID exists in the channel."""

    cached = next((m for m in bot.cached_messages if m.id == message_id), None)
    if cached is not None:
        return cached

    try:
        message = await channel.fetch_message(message_id)  # type: ignore
    except NotFound as e:
        logger.error(
            "[ensure_message_exists] Message %s not found in channel %s: %s",
            message_id,
            channel.id,  # type: ignore
            e,
        )
        return None
    except HTTPException as e:
        logger.error(
            "[ensure_message_exists] Failed fetching message %s in channel %s: %s",  # noqa: E501
            message_id,
            channel.id,  # type: ignore
            e,
        )
        return None

    return message  # type: ignore


async def ensure_messageable_channel_exists(
    guild: Guild, channel_id: int
) -> GuildChannel | Thread | None:
    """Ensure that a channel with the given ID exists in the guild and is messageable."""  # noqa: E501

    channel = guild.get_channel(channel_id)
    if channel is None:
        try:
            channel = await guild.fetch_channel(channel_id)  # type: ignore
            if not isinstance(channel, Messageable):
                logger.error(
                    "[ensure_messageable_channel_exists] channel %s not messageable (%s)",  # noqa: E501
                    channel.id,  # type: ignore
                    type(channel).__name__,
                )
                return None
        except NotFound as e:
            logger.error(
                "[ensure_messageable_channel_exists] Channel %s not found in guild %s: %s",  # noqa: E501
                channel_id,
                guild.id,
                e,
            )
            return None
        except HTTPException as e:
            logger.error(
                "[ensure_messageable_channel_exists] Failed refetching channel %s in guild %s: %s",  # noqa: E501
                channel_id,
                guild.id,
                e,
            )
            return None

    return channel


async def ensure_member_exists(
    guild: Guild, user_id: int | None = None
) -> Member | None:
    """Ensure that a member with the given user ID exists in the guild."""

    if not user_id:
        return None

    member = guild.get_member(user_id)

    if member is None:
        try:
            logger.info("Refetching member %s in guild %s", user_id, guild.id)
            member = await guild.fetch_member(user_id)
        except NotFound as e:
            logger.error(
                "[ensure_member_exists] Member %s not found in guild %s: %s",
                user_id,
                guild.id,
                e,
            )
            return None
        except HTTPException as e:
            logger.error(
                "[ensure_member_exists] Failed refetching member %s in guild %s: %s",  # noqa: E501
                user_id,
                guild.id,
                e,
            )
        return None

    return member


async def ensure_guild_exists(bot: "Nightcore", guild_id: int) -> Guild | None:
    """Ensure that a guild with the given ID exists."""
    guild = bot.get_guild(guild_id)

    if guild is None:
        try:
            guild = await bot.fetch_guild(guild_id)
        except NotFound as e:
            logger.error(
                "[ensure_guild_exists] Guild %s not found: %s",
                guild_id,
                e,
            )
            return None
        except HTTPException as e:
            logger.error(
                "[ensure_guild_exists] Failed fetching guild %s: %s",
                guild_id,
                e,
            )
            return None

    return guild


def has_any_role_from_sequence(
    user: Member, roles_sequence: Sequence[int], with_roles: bool = False
) -> bool | list[Role | None]:
    """Check if a member has any of the specified roles."""
    if with_roles:
        return [
            user.get_role(role_id)
            for role_id in roles_sequence
            if user.get_role(role_id) is not None
        ]

    return any(user.get_role(role_id) for role_id in roles_sequence)


def has_any_role(user: Member, role_id: int) -> bool:
    """Check if a member has a specific role."""
    return user.get_role(role_id) is not None


async def get_all_members_with_specified_role(
    guild: Guild, role_id: int
) -> list[Member]:
    """Get all members with the specified role."""
    role = await ensure_role_exists(guild, role_id)
    if role is None:
        return []

    return role.members


async def get_discord_user(bot: "Nightcore", user_id: int) -> User | None:
    """Get a Discord user by ID, fetching from API if not cached."""
    user = bot.get_user(user_id)
    if user is None:
        try:
            user = await bot.fetch_user(user_id)
        except NotFound as e:
            logger.error(
                "[get_discord_user] User %s not found: %s",
                user_id,
                e,
            )
            return None
        except HTTPException as e:
            logger.error(
                "[get_discord_user] Failed fetching user %s: %s",
                user_id,
                e,
            )
            return None
    return user


def channel_type(type: Enum) -> str:
    """Convert a channel type enum to a human-readable string."""

    return str(type).split(".")[-1].replace("_", " ").title()


async def safe_delete_role(role: Role, reason: str) -> None:
    """Safely delete a role, logging any errors."""
    try:
        await role.delete(reason=reason)
    except Exception as e:
        logger.error(
            "[safe_delete_role] Failed deleting role %s in guild %s: %s",
            role.id,
            role.guild.id,
            e,
        )


def compare_top_roles(guild: Guild, entity: Member | Role) -> bool:
    """Compares the top roles between user and bot or check if bot's role is higher than chosen role."""  # noqa: E501
    if isinstance(entity, Member):
        if guild.owner_id == entity.id:
            return False

        if not guild.me.roles:
            return False

        if not entity.roles:
            return True

        bot_top_role = guild.me.top_role.position
        member_top_role = entity.top_role.position

        return bot_top_role > member_top_role
    else:
        if not guild.me.roles:
            return False

        bot_top_role = guild.me.top_role.position
        role_position = entity.position

        return bot_top_role > role_position
