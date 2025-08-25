"""Utility dataclass for moderation event data."""

from dataclasses import dataclass
from datetime import datetime

import discord


@dataclass
class EventData:
    moderator: discord.Member
    member: discord.Member | discord.User
    category: str
    reason: str
    send_dm: bool = False
    old_nickname: str | None = None
    new_nickname: str | None = None
    duration: str | None = None
    end_time: datetime | None = None
