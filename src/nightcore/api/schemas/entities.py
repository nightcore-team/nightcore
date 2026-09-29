"""Pydantic schemas for guild entities API.

Entities: VIP statuses, Cases, Colors, Battlepass Levels.
"""

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.nightcore.api.schemas._discord import DiscordRoleNoAdmID
from src.utils._enums import EntityTypeEnum


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


class GuildVipStatusSchema(EntityBaseSchema):
    name: str
    emoji_str: str
    role_id: DiscordRoleNoAdmID | None = None
    deposit_max_balance: int = 0
    deposit_interest_rate: Decimal = Decimal("0.0000")
    deposit_interest_cap_amount: int = 0
    shop_discount: Decimal = Decimal("0.0000")


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


ENTITY_SCHEMA_MODEL_MAP: dict[EntityTypeEnum, type[EntityBaseSchema]] = {
    EntityTypeEnum.VIP_STATUS: GuildVipStatusSchema,
    EntityTypeEnum.CASE: GuildCaseSchema,
    EntityTypeEnum.COLOR: GuildColorSchema,
    EntityTypeEnum.BATTLEPASS_LEVEL: GuildBattlepassLevelSchema,
}
