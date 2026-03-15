"""Redis cache models for Discord state."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GuildCacheEntry:
    id: str
    name: str


@dataclass(frozen=True, slots=True)
class RoleCacheEntry:
    id: str
    name: str
    color: str
    position: int
    administrator: bool


@dataclass(frozen=True, slots=True)
class ChannelCacheEntry:
    id: str
    name: str
    type: str


@dataclass(frozen=True, slots=True)
class GuildStateSnapshot:
    guild: GuildCacheEntry
    roles: list[RoleCacheEntry]
    channels: list[ChannelCacheEntry]
