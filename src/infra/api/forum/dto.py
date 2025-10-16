from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Server:
    section_id: int
    guild_id: str
    channel_id: str
    role_id: str


@dataclass
class Thread:
    thread_id: int
    title: str
    prefix_id: int
    sticky: int
    node_id: int
    user_id: str
    username: str

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Thread":
        """Create a Thread instance from a dictionary."""

        return Thread(
            thread_id=int(data.get("thread_id") or 0),
            title=str(data.get("title") or ""),
            prefix_id=int(data.get("prefix_id") or 0),
            sticky=int(data.get("sticky") or 0),
            node_id=int(data.get("node_id") or 0),
            user_id=str(data.get("user_id") or ""),
            username=str(data.get("username") or ""),
        )
