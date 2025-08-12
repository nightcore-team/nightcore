"""The module contains database operations for the Nightcore bot."""

from collections.abc import Sequence
from typing import Any, get_origin

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.db.models.enums import LoggingChannelType
from src.infra.db.models.guild import GuildConfig


async def get_guild_config(
    session: AsyncSession, *, guild_id: int
) -> GuildConfig | None:
    """Get the guild configuration from the database."""
    result = await session.scalar(
        select(GuildConfig).where(GuildConfig.guild_id == guild_id)
    )
    if not result:
        session.add(GuildConfig(guild_id=guild_id))

    return result


async def get_specified_logging_channel(
    session: AsyncSession,
    *,
    guild_id: int,
    channel_type: LoggingChannelType,
) -> int | None:
    """Get the specified logging channel ID from the database."""
    result = await session.scalar(
        select(channel_type).where(GuildConfig.guild_id == guild_id)  # type: ignore
    )

    return result


def apply_field_mapping_to_model(
    obj: Any,
    *,
    provided: dict[str, str],
    attr_template: str = "{field}",
    cast_type: type | None = int,
) -> tuple[list[str], list[str]]:
    """Update model fields based on attribute template, supports lists."""
    changed, skipped = [], []

    for field, new_value in provided.items():
        attr = attr_template.format(field=field)
        if not hasattr(obj, attr):
            skipped.append(field)
            continue

        # Determine if the target attribute is a list
        is_list_target = cast_type is list or (
            cast_type is not None and get_origin(cast_type) is list
        )

        new_value_casted: Any

        if is_list_target:
            # If the new value is a string, split it into a list
            if isinstance(new_value, str):
                new_value_casted = [
                    int(x.strip()) for x in new_value.split(",") if x.strip()
                ]
            elif isinstance(new_value, Sequence):
                new_value_casted = list(new_value)
            else:
                skipped.append(field)
                continue
        else:
            # default casting
            new_value_casted = cast_type(new_value) if cast_type else new_value

        old_value = getattr(obj, attr)

        if old_value == new_value_casted:
            skipped.append(field)
            continue

        setattr(obj, attr, new_value_casted)
        changed.append(f"{field}: {old_value} -> {new_value_casted}")

    return changed, skipped
