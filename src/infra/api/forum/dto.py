"""Data transfer objects for the forum API."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Server:
    section_id: int
    guild_id: int
    channel_id: int
    role_id: int
