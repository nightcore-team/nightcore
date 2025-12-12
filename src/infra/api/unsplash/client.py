"""Unsplash API module."""

from typing import Any

from src.infra.api.base_client import IAPIClient


class UnsplashAPIClient:
    def __init__(self, client: IAPIClient) -> None:
        self._client = client

    @property
    def client(self) -> IAPIClient:
        """Get the base API client."""
        return self._client

    async def get_random_photo(self, query: str) -> str | None:
        """GET /photos/random?query={query}."""

        payload = await self._client.get(
            "/photos/random",
            params={
                "query": query,
                "orientation": "landscape",
                "content_filter": "high",
            },
        )
        raw_photo: dict[str, Any] = (  # type: ignore
            payload if isinstance(payload, dict) else {}
        )

        return raw_photo.get("urls", {}).get("regular", None)
