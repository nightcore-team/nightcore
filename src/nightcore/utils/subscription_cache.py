"""In-memory cache of guild subscription expiry timestamps."""

from datetime import datetime


class SubscriptionCache:
    """Store subscription expiry per guild to avoid repeat service lookups."""

    def __init__(self) -> None:
        self._subscriptions: dict[int, datetime] = {}

    def get(self, guild_id: int) -> datetime | None:
        """Return the cached expiry for a guild, if any.

        Args:
            guild_id: Id of the guild to look up.

        Returns:
            The cached expiry timestamp, or None when not cached.
        """
        return self._subscriptions.get(guild_id)

    def set(self, guild_id: int, expires_at: datetime) -> None:
        """Cache the expiry timestamp for a guild.

        Args:
            guild_id: Id of the guild to store the expiry for.
            expires_at: Timestamp the guild subscription expires at.
        """
        self._subscriptions[guild_id] = expires_at
