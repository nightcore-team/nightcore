"""Subscription cache."""

from datetime import datetime


class SubscriptionCache:
    def __init__(self) -> None:
        self._subscriptions: dict[int, datetime] = {}

    def get(self, guild_id: int) -> datetime | None:
        """Get guild by guild_id from cache."""

        return self._subscriptions.get(guild_id)

    def set(self, guild_id: int, expires_at: datetime) -> None:
        """Set guild by guild_id to cache."""

        self._subscriptions[guild_id] = expires_at
