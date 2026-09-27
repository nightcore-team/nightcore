from datetime import datetime


class SubscriptionCache:
    def __init__(self) -> None:
        self._subscriptions: dict[int, datetime] = {}

    def get(self, guild_id: int) -> datetime | None:
        return self._subscriptions.get(guild_id)

    def set(self, guild_id: int, expires_at: datetime) -> None:
        self._subscriptions[guild_id] = expires_at
