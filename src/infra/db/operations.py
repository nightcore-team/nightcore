"""The module contains database operations for the Nightcore bot."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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


async def update_guild_config(  # noqa: D103
    session: AsyncSession,
    *,
    guild_id: int,
    field: str,
    value: Any,  # type: ignore
): ...
