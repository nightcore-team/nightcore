"""Base interface for API clients."""

from abc import abstractmethod
from collections.abc import Mapping
from typing import Any, Protocol


class IAPIClient(Protocol):
    base_url: str
    default_headers: Mapping[str, str] | None
    timeout: float

    @abstractmethod
    def get(
        self,
        endpoint: str,
        params: Mapping[str, Any],
        headers: Mapping[str, str] | None = None,
    ) -> Any:
        """Get data from the specified API endpoint."""

    @abstractmethod
    def post(
        self,
        endpoint: str,
        data: Mapping[str, Any],
        headers: Mapping[str, str] | None = None,
    ) -> Any:
        """Post data to the specified API endpoint."""

    @abstractmethod
    async def aclose(self) -> None:
        """Asynchronously close the client session."""
