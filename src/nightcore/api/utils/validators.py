from dataclasses import dataclass, field
from typing import Any, TypedDict

from pydantic import (
    ValidationInfo,
)

from src.nightcore.api.domain.exceptions.base import ConfigValidationError


class RoleInfo(TypedDict):
    administrator: bool


class ChannelInfo(TypedDict):
    type: str


@dataclass
class ValidationContext:
    guild_id: int
    roles: dict[int, RoleInfo] = field(default_factory=dict[int, RoleInfo])
    channels: dict[int, ChannelInfo] = field(
        default_factory=dict[int, ChannelInfo]
    )


def validate_role_id(v: Any, info: ValidationInfo) -> int:
    value = int(v)
    ctx = info.context

    if not isinstance(ctx, ValidationContext):
        raise ValueError("Invalid validation context")

    if value not in ctx.roles:
        raise ValueError(f"Роль {value} не найдена в гильдии {ctx.guild_id}")

    return value


def validate_role_no_adm_id(v: Any, info: ValidationInfo) -> int:
    value = int(v)
    ctx = info.context

    if not isinstance(ctx, ValidationContext):
        raise ValueError("Invalid validation context")

    if value not in ctx.roles:
        raise ValueError(f"Роль {value} не найдена в гильдии {ctx.guild_id}")

    role = ctx.roles[value]

    if role["administrator"]:
        raise ValueError(
            "Нельзя использовать роль с правами администратора для этого поля"
        )

    return value


def validate_text_channel_id(v: Any, info: ValidationInfo) -> int:
    value = int(v)
    ctx = info.context

    if not isinstance(ctx, ValidationContext):
        raise ValueError("Invalid validation context")

    if value not in ctx.channels:
        raise ValueError(f"Канал {value} не найден в гильдии {ctx.guild_id}")

    channel = ctx.channels[value]

    if channel["type"] != "text":
        raise ConfigValidationError("Ожидался канал с типом текстовый")

    return value


def validate_voice_channel_id(v: Any, info: ValidationInfo) -> int:
    value = int(v)
    ctx = info.context

    if not isinstance(ctx, ValidationContext):
        raise ValueError("Invalid validation context")

    if value not in ctx.channels:
        raise ConfigValidationError(
            f"Канал {value} не найден в гильдии {ctx.guild_id}"
        )

    channel = ctx.channels[value]

    if channel["type"] != "voice":
        raise ConfigValidationError("Ожидался канал с типом голосовой")

    return value


def validate_category_id(v: Any, info: ValidationInfo) -> int:
    value = int(v)
    ctx = info.context

    if not isinstance(ctx, ValidationContext):
        raise ValueError("Invalid validation context")

    if value not in ctx.channels:
        raise ConfigValidationError(
            f"Канал {value} не найден в гильдии {ctx.guild_id}"
        )

    channel = ctx.channels[value]

    if channel["type"] != "category":
        raise ConfigValidationError("Ожидался канал с типом категория")

    return value
