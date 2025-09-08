"""Utility functions for handling Discord members."""

import logging

from discord import Guild, HTTPException, Member, NotFound, User
import discord

logger = logging.getLogger(__name__)


async def ensure_member_exists(
    guild: Guild, user: User | Member
) -> Member | None:
    """
    Resolve the given User or Member to a Member belonging to the provided guild.

    Parameters:
        user: A discord.User or discord.Member to check.
        guild: The guild in which membership should be verified.

    Returns:
        The Member instance if the user is (or can be fetched as) a member of the guild, otherwise None.
    """  # noqa: E501

    # If already a Member, ensure it belongs to the target guild; if not, try to refetch from the guild.  # noqa: E501
    if isinstance(user, Member):
        return user
    try:
        member = guild.get_member(user.id)
        if member is None:
            try:
                member = await guild.fetch_member(user.id)
            except NotFound:
                member = None
        return member
    except HTTPException as e:
        logger.debug(
            "Failed refetching member %s in guild %s: %s",
            user.id,
            guild.id,
            e,
        )
        return None
