"""Repository for storing Discord guild state in Redis."""

import asyncio
import json
import logging
from dataclasses import asdict

from redis.asyncio import Redis
from redis.exceptions import ConnectionError, TimeoutError
from src.config.config import config

from .models import (
    ChannelCacheEntry,
    GuildCacheEntry,
    GuildStateSnapshot,
    RoleCacheEntry,
)

logger = logging.getLogger(__name__)


class GuildStateRepository:
    """Persist and retrieve Discord guild state from Redis."""

    def __init__(self, redis: Redis):
        self.redis = redis

    @property
    def _ready_key(self) -> str:
        return "nightcore:discord_state:ready"

    @property
    def _guilds_key(self) -> str:
        return "nightcore:discord_state:guilds"

    def _roles_key(self, guild_id: str) -> str:
        return f"nightcore:discord_state:guild:{guild_id}:roles"

    def _channels_key(self, guild_id: str) -> str:
        return f"nightcore:discord_state:guild:{guild_id}:channels"

    async def connect(self) -> None:
        """Ensure the Redis connection is available."""
        attempts = max(1, config.redis.REDIS_CONNECT_RETRIES)
        delay_seconds = max(
            0.0,
            config.redis.REDIS_CONNECT_RETRY_DELAY_SECONDS,
        )

        for attempt in range(1, attempts + 1):
            try:
                await self.redis.ping()  # type: ignore
                if attempt > 1:
                    logger.info(
                        "[redis] Connection restored on attempt %d/%d",
                        attempt,
                        attempts,
                    )
                return
            except (ConnectionError, TimeoutError) as exc:
                if attempt == attempts:
                    logger.error(
                        "[redis] Failed to connect after %d attempts",
                        attempts,
                    )
                    raise

                logger.warning(
                    "[redis] Connect attempt %d/%d failed: %s. "
                    "Retrying in %.2fs",
                    attempt,
                    attempts,
                    exc,
                    delay_seconds,
                )
                await asyncio.sleep(delay_seconds)

    async def close(self) -> None:
        """Close the Redis connection."""

        await self.redis.aclose()

    async def mark_ready(self) -> None:
        """Mark the cached Discord state as ready for API reads."""

        await self.redis.set(self._ready_key, "1")

    async def mark_not_ready(self) -> None:
        """Mark the cached Discord state as not ready for API reads."""

        await self.redis.set(self._ready_key, "0")

    async def is_ready(self) -> bool:
        """Return whether the cached Discord state is ready."""

        return await self.redis.get(self._ready_key) == "1"

    async def get_guilds(self) -> list[dict[str, str]]:
        """Return all cached guilds."""

        values = await self.redis.hvals(self._guilds_key)  # type: ignore
        guilds = [self._loads(value) for value in values]  # type: ignore
        return sorted(guilds, key=lambda guild: guild["name"].casefold())

    async def get_guild(self, guild_id: str) -> dict[str, str] | None:
        """Return a cached guild by ID."""

        value = await self.redis.hget(self._guilds_key, guild_id)  # type: ignore
        if value is None:
            return None
        return self._loads(value)  # type: ignore

    async def get_roles(self, guild_id: str) -> list[dict[str, str]]:
        """Return cached roles for a guild."""

        values = await self.redis.hvals(self._roles_key(guild_id))  # type: ignore
        roles = [self._loads(value) for value in values]  # type: ignore
        return sorted(roles, key=lambda role: role["name"].casefold())

    async def get_channels(self, guild_id: str) -> list[dict[str, str]]:
        """Return cached channels for a guild."""

        values = await self.redis.hvals(self._channels_key(guild_id))  # type: ignore
        channels = [self._loads(value) for value in values]  # type: ignore
        return sorted(
            channels,
            key=lambda channel: (channel["type"], channel["name"].casefold()),
        )

    async def sync_guilds(self, snapshots: list[GuildStateSnapshot]) -> None:
        """Replace the cached Discord state with a fresh bot snapshot."""

        current_guild_ids = set(await self.redis.hkeys(self._guilds_key))  # type: ignore
        next_guild_ids = {snapshot.guild.id for snapshot in snapshots}
        stale_guild_ids = current_guild_ids - next_guild_ids  # type: ignore

        if stale_guild_ids:
            async with self.redis.pipeline(transaction=True) as pipeline:
                pipeline.hdel(self._guilds_key, *stale_guild_ids)  # type: ignore
                for guild_id in stale_guild_ids:  # type: ignore
                    pipeline.delete(
                        self._roles_key(guild_id),  # type: ignore
                        self._channels_key(guild_id),  # type: ignore
                    )
                await pipeline.execute()

        if snapshots:
            await self.redis.hset(  # type: ignore
                self._guilds_key,
                mapping={
                    snapshot.guild.id: self._dumps(snapshot.guild)
                    for snapshot in snapshots
                },
            )
        else:
            await self.redis.delete(self._guilds_key)

        for snapshot in snapshots:
            await self.replace_roles(snapshot.guild.id, snapshot.roles)
            await self.replace_channels(snapshot.guild.id, snapshot.channels)

    async def upsert_guild(self, guild: GuildCacheEntry) -> None:
        """Upsert a guild entry."""

        await self.redis.hset(  # type: ignore
            self._guilds_key,
            guild.id,
            self._dumps(guild),
        )  # type: ignore

    async def delete_guild(self, guild_id: str) -> None:
        """Delete a guild and all of its cached entities."""

        async with self.redis.pipeline(transaction=True) as pipeline:
            pipeline.hdel(self._guilds_key, guild_id)
            pipeline.delete(
                self._roles_key(guild_id),  # type: ignore
                self._channels_key(guild_id),  # type: ignore
            )
            await pipeline.execute()

    async def upsert_guild_snapshot(
        self, snapshot: GuildStateSnapshot
    ) -> None:
        """Upsert a guild and replace its roles and channels."""

        await self.upsert_guild(snapshot.guild)
        await self.replace_roles(snapshot.guild.id, snapshot.roles)
        await self.replace_channels(snapshot.guild.id, snapshot.channels)

    async def replace_roles(
        self, guild_id: str, roles: list[RoleCacheEntry]
    ) -> None:
        """Replace all cached roles for a guild."""

        key = self._roles_key(guild_id)
        if not roles:
            await self.redis.delete(key)
            return

        async with self.redis.pipeline(transaction=True) as pipeline:
            pipeline.delete(key)
            pipeline.hset(  # type: ignore
                key,
                mapping={role.id: self._dumps(role) for role in roles},
            )
            await pipeline.execute()

    async def upsert_role(self, guild_id: str, role: RoleCacheEntry) -> None:
        """Upsert a single role for a guild."""

        await self.redis.hset(  # type: ignore
            self._roles_key(guild_id),
            role.id,
            self._dumps(role),
        )  # type: ignore

    async def delete_role(self, guild_id: str, role_id: str) -> None:
        """Delete a single cached role for a guild."""

        await self.redis.hdel(self._roles_key(guild_id), role_id)  # type: ignore

    async def replace_channels(
        self, guild_id: str, channels: list[ChannelCacheEntry]
    ) -> None:
        """Replace all cached channels for a guild."""

        key = self._channels_key(guild_id)
        if not channels:
            await self.redis.delete(key)
            return

        async with self.redis.pipeline(transaction=True) as pipeline:
            pipeline.delete(key)
            pipeline.hset(  # type: ignore
                key,
                mapping={
                    channel.id: self._dumps(channel) for channel in channels
                },
            )
            await pipeline.execute()

    async def upsert_channel(
        self, guild_id: str, channel: ChannelCacheEntry
    ) -> None:
        """Upsert a single channel for a guild."""

        await self.redis.hset(  # type: ignore
            self._channels_key(guild_id),
            channel.id,
            self._dumps(channel),
        )

    async def delete_channel(self, guild_id: str, channel_id: str) -> None:
        """Delete a single cached channel for a guild."""

        await self.redis.hdel(self._channels_key(guild_id), channel_id)  # type: ignore

    def _dumps(
        self,
        value: GuildCacheEntry | RoleCacheEntry | ChannelCacheEntry,
    ) -> str:
        return json.dumps(asdict(value))

    def _loads(self, value: str) -> dict[str, str]:
        return json.loads(value)
