"""Forum API module."""

from typing import Any

from src.infra.api.base_client import IAPIClient
from src.infra.api.forum.dto import Thread


class ForumApi:
    def __init__(self, client: IAPIClient) -> None:
        self._client = client

    async def get_threads_from_section(self, section_id: int) -> list[Thread]:
        """GET /threads?node_id={section_id}."""

        payload = await self._client.get(
            "/threads", params={"node_id": str(section_id)}
        )
        raw_threads: dict[str, Any] = (  # type: ignore
            payload.get("threads", []) if isinstance(payload, dict) else []  # type: ignore
        )

        return [Thread.from_dict(t) for t in raw_threads]  # type: ignore

    async def create_post_in_thread(
        self, thread_id: int, message: str
    ) -> None:
        """POST /posts (application/x-www-form-urlencoded)."""

        await self._client.post(
            "/posts", data={"thread_id": str(thread_id), "message": message}
        )

    async def update_thread(
        self, thread_id: int, prefix_id: int = 6, sticky: int = 1
    ) -> None:
        """POST /threads/{thread_id} (application/x-www-form-urlencoded)."""

        await self._client.post(
            f"/threads/{thread_id}",
            data={"prefix_id": str(prefix_id), "sticky": str(sticky)},
        )
