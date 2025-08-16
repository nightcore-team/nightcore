"""The module contains database operations for the Nightcore bot."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.db.models._enums import LoggingChannelType
from src.infra.db.models.guild import GuildConfig


async def get_guild_config(
    session: AsyncSession, *, guild_id: int
) -> GuildConfig | None:
    """Get the guild configuration from the database."""
    result = await session.scalar(
        select(GuildConfig).where(GuildConfig.guild_id == guild_id)
    )

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
