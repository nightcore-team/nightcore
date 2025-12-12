"""Cache module for photos with TTL support."""

from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta

import discord


class PhotoCache:
    """Cache for photos with TTL support."""

    def __init__(self, default_ttl_seconds: int = 90):
        self._cache: dict[str, tuple[str | None, datetime]] = {}
        self.default_ttl = default_ttl_seconds

    async def get_or_fetch(
        self,
        key: str,
        fetch_fn: Callable[[], Awaitable[str | None]],
        ttl_seconds: int | None = None,
    ) -> str | None:
        """
        Get photo URL from cache or fetch it using provided function.

        Args:
            key: Cache key (e.g., "winter holidays")
            fetch_fn:  Async function that fetches the photo URL
            ttl_seconds: Time to live in seconds (uses default if None)

        Returns:
            Photo URL or None if fetch failed
        """
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        now = discord.utils.utcnow()

        # Check if we have cached data
        if key in self._cache:
            image_url, expires_at = self._cache[key]

            # If not expired and URL exists, return it
            if expires_at > now and image_url is not None:
                return image_url

        # Cache miss or expired - fetch new photo
        image_url = await fetch_fn()

        # Store in cache with new expiration time
        if image_url:
            self._cache[key] = (image_url, now + timedelta(seconds=ttl))

        return image_url

    def clear(self, key: str | None = None):
        """Clear specific key or entire cache."""
        if key:
            self._cache.pop(key, None)
        else:
            self._cache.clear()
