"""Pydantic schemas for guild entities API.

Entities: VIP statuses, Cases, Colors, Battlepass Levels.
"""

from typing import Annotated, Any

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    PlainSerializer,
)

from src.nightcore.api.utils.validators import (
    validate_role_id,
    validate_role_no_adm_id,
)
from src.utils._enums import EntityTypeEnum


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


class EntityBaseSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        extra="ignore",
    )


class GuildCaseSchema(EntityBaseSchema):
    name: str
    drop: list[dict[str, Any]] = Field(default_factory=list[dict[str, Any]])


class GuildColorSchema(EntityBaseSchema):
    role_id: DiscordRoleNoAdmID


class GuildBattlepassLevelSchema(EntityBaseSchema):
    level: int
    exp_required: int
    reward: dict[str, Any]
    additional_reward: dict[str, Any] | None = None


class EntityBatchItem(BaseModel):
    entity_id: int = Field(default=0, ge=0)
    data: dict[str, Any]


class EntityBatchUpdateBody(BaseModel):
    entity_type: EntityTypeEnum
    items: list[EntityBatchItem] = Field(min_length=1, max_length=200)


class EntityBatchError(BaseModel):
    index: int
    entity_id: int
    error: str


class EntityBatchResult(BaseModel):
    updated: list[dict[str, Any]] = Field(default_factory=list[dict[str, Any]])
    errors: list[EntityBatchError] = Field(
        default_factory=list[EntityBatchError]
    )
