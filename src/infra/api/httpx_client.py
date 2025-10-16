"""HTTPX-based implementation of the IAPIClient interface."""

import logging
from collections.abc import Mapping
from typing import Any

import httpx

from src.infra.api.base_client import IAPIClient

logger = logging.getLogger(__name__)


class HttpxAPIClient(IAPIClient):
    def __init__(
        self,
        base_url: str,
        default_headers: Mapping[str, str] | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers=default_headers,
            timeout=timeout,
        )

    async def get(
        self,
        endpoint: str,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Any:
        """Get data from the specified API endpoint."""
        try:
            resp = await self._client.get(
                endpoint, params=params, headers=headers
            )
            resp.raise_for_status()
            return resp.json()

        except httpx.HTTPError as e:
            logger.exception("[httpx] GET %s failed: %s", endpoint, e)
            raise

    async def post_form(
        self,
        endpoint: str,
        data: Mapping[str, Any],
        headers: Mapping[str, str] | None = None,
    ) -> Any:
        """Post form data to the specified API endpoint."""
        try:
            resp = await self._client.post(
                endpoint,
                data=data,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    **(headers or {}),
                },
            )
            resp.raise_for_status()

            return (
                resp.json()
                if resp.headers.get("content-type", "").startswith(
                    "application/json"
                )
                else resp.text
            )
        except httpx.HTTPError as e:
            logger.exception("[httpx] POST %s failed: %s", endpoint, e)
            raise

    async def aclose(self) -> None:
        """Asynchronously close the client session."""
        await self._client.aclose()
