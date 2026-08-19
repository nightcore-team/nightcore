"""Pydantic schemas for logging revisions."""

from typing import Any

from pydantic import BaseModel
from pydantic_settings import SettingsConfigDict

from src.utils._enums import ConfigTypeEnum

from ..types import DiscordId


class Base(BaseModel):
    model_config = SettingsConfigDict(
        from_attributes=True,
        populate_by_name=True,
        extra="ignore",
    )


class LoggingRevisionRequestSchema(Base):
    guild_id: DiscordId
    config_type: ConfigTypeEnum
    limit: int = 100
    offset: int = 0


class LoggingRevisionSchema(Base):
    revision_id: str
    down_revision_id: str
    config_type: ConfigTypeEnum
    guild_id: DiscordId
    discord_user_id: DiscordId
    discord_username: str
    old_data: dict[str, Any]
    new_data: dict[str, Any]
