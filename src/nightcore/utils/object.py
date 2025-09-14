"""Utility functions for handling Discord members."""

import logging
from collections.abc import Sequence

from discord import (
    Guild,
    HTTPException,
    Member,
    NotFound,
    Role,
    TextChannel,
    Thread,
    User,
)
from discord.abc import GuildChannel, Messageable

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
    guild: Guild, user: User | Member
) -> Member | None:
    """Ensure that a member with the given user ID exists in the guild."""
    if isinstance(user, Member):
        return user

    member = guild.get_member(user.id)

    if member is None:
        try:
            member = await guild.fetch_member(user.id)
        except NotFound as e:
            logger.error(
                "[ensure_member_exists] Member %s not found in guild %s: %s",
                user.id,
                guild.id,
                e,
            )
            return None
        except HTTPException as e:
            logger.error(
                "[ensure_member_exists] Failed refetching member %s in guild %s: %s",  # noqa: E501
                user.id,
                guild.id,
                e,
            )
        return None

    return member


def has_any_role_from_sequence(
    user: Member, roles_sequence: Sequence[int]
) -> bool:
    """Check if a member has any of the specified roles."""
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
