"""Shared Discord-related type annotations."""

from typing import Annotated, Any

from pydantic import BeforeValidator, Field, PlainSerializer

from src.nightcore.api.utils.validators import (
    validate_category_id,
    validate_discord_webhook,
    validate_role_id,
    validate_role_no_adm_id,
    validate_text_channel_id,
    validate_voice_channel_id,
)


def _parse_snowflake(v: Any) -> int:
    return int(v)


def _serialize_snowflake(v: int) -> str:
    return str(v)


SnowflakeValidator = BeforeValidator(_parse_snowflake)
SnowflakeSerializer = PlainSerializer(
    _serialize_snowflake, return_type=str, when_used="json"
)

DiscordRoleID = Annotated[
    int,
    SnowflakeValidator,
    SnowflakeSerializer,
    validate_role_id,
]
DiscordRoleNoAdmID = Annotated[
    int,
    SnowflakeValidator,
    SnowflakeSerializer,
    validate_role_no_adm_id,
]
DiscordTextChannelID = Annotated[
    int,
    SnowflakeValidator,
    SnowflakeSerializer,
    validate_text_channel_id,
]
DiscordCategoryID = Annotated[
    int,
    SnowflakeValidator,
    SnowflakeSerializer,
    validate_category_id,
]
DiscordVoiceChannelID = Annotated[
    int,
    SnowflakeValidator,
    SnowflakeSerializer,
    validate_voice_channel_id,
]

DiscordRoleIDList = Annotated[list[DiscordRoleID], Field(max_length=250)]
DiscordChannelIDList = Annotated[
    list[DiscordTextChannelID], Field(max_length=500)
]
DiscordCategoryIDList = Annotated[
    list[DiscordCategoryID], Field(max_length=50)
]

DiscordWebhookURL = Annotated[
    str,
    validate_discord_webhook,
]
