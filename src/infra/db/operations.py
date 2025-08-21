"""The module contains database operations for the Nightcore bot."""

from datetime import datetime
from typing import TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.db.models._enums import LoggingChannelType
from src.infra.db.models.guild import (
    GuildClansConfig,
    GuildEconomyConfig,
    GuildLevelsConfig,
    GuildLoggingConfig,
    GuildModerationConfig,
    GuildNotificationsConfig,
    GuildPrivateChannelsConfig,
    GuildTicketsConfig,
    MainGuildConfig,
)
from src.infra.db.models.punish import Punish

T = TypeVar(
    "T",
    GuildClansConfig,
    GuildEconomyConfig,
    GuildLevelsConfig,
    GuildLoggingConfig,
    GuildModerationConfig,
    GuildPrivateChannelsConfig,
    GuildNotificationsConfig,
    GuildTicketsConfig,
    MainGuildConfig,
)


async def get_specified_guild_config(
    session: AsyncSession, *, config_type: type[T], guild_id: int
) -> T | None:
    """Get the guild configuration from the database."""
    stmt = select(config_type).where(config_type.guild_id == guild_id)
    return await session.scalar(stmt)


async def get_specified_logging_channel(
    session: AsyncSession,
    *,
    guild_id: int,
    channel_type: LoggingChannelType,
) -> int | None:
    """Get the specified logging channel ID from the database."""
    column = getattr(GuildLoggingConfig, channel_type.value)
    stmt = select(column).where(GuildLoggingConfig.guild_id == guild_id)
    return await session.scalar(stmt)


async def get_moderation_access_roles(
    session: AsyncSession, *, guild_id: int
) -> list[int]:
    """Get the list of moderation access roles for a guild."""
    stmt = select(GuildModerationConfig.moderation_access_roles_ids).where(
        GuildModerationConfig.guild_id == guild_id
    )
    result = await session.scalar(stmt)
    return result or []


async def create_punish(
    session: AsyncSession,
    *,
    guild_id: int,
    user_id: int,
    moderator_id: int,
    category: str,
    reason: str,
    time_now: datetime,
    duration: int | None = None,
    end_time: datetime | None = None,
) -> Punish:
    """Create a new punishment entry in the database."""
    punish = Punish(
        guild_id=guild_id,
        user_id=user_id,
        moderator_id=moderator_id,
        category=category,
        reason=reason,
        time_now=time_now,
        duration=duration,
        end_time=end_time,
    )
    session.add(punish)

    return punish
