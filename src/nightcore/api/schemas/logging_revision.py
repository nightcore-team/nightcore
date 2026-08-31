"""Pydantic schemas for logging revisions."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field
from pydantic_settings import SettingsConfigDict

from src.utils._enums import ConfigTypeEnum

from ..types import DiscordId


class Base(BaseModel):
    model_config = SettingsConfigDict(
        from_attributes=True,
        populate_by_name=True,
        extra="ignore",
    )


class ListLoggingRevisionRequestSchema(Base):
    config_type: ConfigTypeEnum | None = None
    user_id: DiscordId | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    limit: int = Field(default=100, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=100)


class LoggingRevisionRequestSchema(Base):
    config_type: ConfigTypeEnum


class LoggingRevisionMetaSchema(Base):
    revision_id: str
    down_revision_id: str
    config_type: ConfigTypeEnum
    discord_user_id: DiscordId
    discord_username: str
    created_at: datetime


class ListLoggingRevisionMetaResponseSchema(Base):
    total: int
    revisions: list[LoggingRevisionMetaSchema]


class LoggingRevisionDataSchema(Base):
    revision_id: str
    old_data: dict[str, Any]
    new_data: dict[str, Any]
