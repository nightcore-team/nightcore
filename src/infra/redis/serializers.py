"""Serialize Discord entities into Redis cache payloads."""

import discord

from .models import (
    ChannelCacheEntry,
    GuildCacheEntry,
    GuildStateSnapshot,
    RoleCacheEntry,
)


def serialize_guild(guild: discord.Guild) -> GuildCacheEntry:
    """Serialize a Discord guild."""

    return GuildCacheEntry(
        id=str(guild.id),
        name=guild.name,
    )


def serialize_role(role: discord.Role) -> RoleCacheEntry:
    """Serialize a Discord role."""

    return RoleCacheEntry(
        id=str(role.id),
        name=role.name,
        color=f"#{role.color.value:06X}",
        position=role.position,
        administrator=role.permissions.administrator,
    )


def serialize_channel(
    channel: discord.abc.GuildChannel,
) -> ChannelCacheEntry:
    """Serialize a Discord guild channel."""

    return ChannelCacheEntry(
        id=str(channel.id),
        name=channel.name,
        type=channel.type.name,
    )


def snapshot_guild_state(guild: discord.Guild) -> GuildStateSnapshot:
    """Build a full Redis snapshot for a guild."""

    return GuildStateSnapshot(
        guild=serialize_guild(guild),
        roles=[serialize_role(role) for role in guild.roles],
        channels=[serialize_channel(channel) for channel in guild.channels],
    )
