"""The module contains database operations for the Nightcore bot."""

from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from typing import TypeVar

from async_lru import alru_cache
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.cache.async_lru import alru_invalidator
from src.infra.db.models import (
    GuildClansConfig,
    GuildEconomyConfig,
    GuildLevelsConfig,
    GuildLoggingConfig,
    GuildModerationConfig,
    GuildNotificationsConfig,
    GuildPrivateChannelsConfig,
    GuildTicketsConfig,
    MainGuildConfig,
    Punish,
    TempPunish,
    User,
)
from src.infra.db.models._enums import ChannelType

GuildT = TypeVar(
    "GuildT",
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
    session: AsyncSession, *, config_type: type[GuildT], guild_id: int
) -> GuildT | None:
    """Get the guild configuration from the database."""
    stmt = select(config_type).where(config_type.guild_id == guild_id)
    return await session.scalar(stmt)


async def get_specified_channel(
    session: AsyncSession,
    *,
    guild_id: int,
    config_type: type[GuildT],
    channel_type: ChannelType,
) -> int | None:
    """Get the specified channel ID from the database."""
    column = getattr(config_type, channel_type.value)
    stmt = select(column).where(config_type.guild_id == guild_id)
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
    time_now: datetime,
    reason: str | None = None,
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
    alru_invalidator(get_user_infractions, guild_id=guild_id, user_id=user_id)
    return punish


async def create_temp_punish(
    session: AsyncSession,
    *,
    guild_id: int,
    user_id: int,
    category: str,
    end_time: datetime,
) -> TempPunish:
    """Create a new temporary punishment entry in the database."""
    temp_punish = TempPunish(
        guild_id=guild_id,
        user_id=user_id,
        category=category,
        end_time=end_time,
    )
    session.add(temp_punish)
    return temp_punish


async def get_temp_infractions(session: AsyncSession) -> Sequence[TempPunish]:
    """Get the list of temporary punishments from the database."""
    stmt = select(TempPunish)
    result = await session.scalars(stmt)
    return result.all()


async def get_latest_temp_punish(
    session: AsyncSession,
    *,
    guild_id: int,
    user_id: int,
    category: str,
) -> TempPunish | None:
    """Get the latest temporary punishment for a user in a guild."""
    stmt = (
        select(TempPunish)
        .where(
            TempPunish.guild_id == guild_id,
            TempPunish.user_id == user_id,
            func.lower(TempPunish.category) == category.lower(),
        )
        .order_by(TempPunish.end_time.asc().nulls_last())
        .limit(1)
    )
    res = await session.execute(stmt)
    return res.scalar_one_or_none()


async def get_fraction_roles(
    session: AsyncSession, *, guild_id: int
) -> list[int]:
    """Get the list of fraction roles for a guild."""

    stmt = select(MainGuildConfig.fraction_roles).where(
        MainGuildConfig.guild_id == guild_id
    )
    roles = await session.execute(stmt)

    return roles.scalar_one() or []


async def get_fraction_roles_access(
    session: AsyncSession, *, guild_id: int
) -> list[int]:
    """Get the list of fraction roles access for a guild."""

    stmt = select(GuildModerationConfig.fraction_roles_access_roles_ids).where(
        GuildModerationConfig.guild_id == guild_id
    )
    roles = await session.execute(stmt)

    return roles.scalar_one() or []


@alru_cache()
async def get_user_infractions(
    session: AsyncSession, *, guild_id: int, user_id: int
) -> Sequence[Punish]:
    """Get the list of punishments for a user in a guild."""
    stmt = (
        select(Punish)
        .where(Punish.guild_id == guild_id)
        .where(Punish.user_id == user_id)
        .order_by(Punish.time_now.asc())
    )
    result = await session.scalars(stmt)

    return result.all()


async def count_user_infractions_last_7_days(
    session: AsyncSession,
    *,
    guild_id: int,
    user_id: int,
) -> int:
    """Count the number of punishments for a user in the last 7 days."""
    boundary = datetime.now(timezone.utc) - timedelta(days=7)

    stmt = (
        select(func.count())
        .select_from(Punish)
        .where(
            Punish.guild_id == guild_id,
            Punish.user_id == user_id,
            Punish.time_now.is_not(None),
            Punish.time_now >= boundary,
        )
    )

    result = await session.execute(stmt)
    return result.scalar_one()


async def get_total_users_count(session: AsyncSession) -> int | None:
    """Get the total number of users in the database."""
    stmt = select(func.count()).select_from(User)

    return await session.scalar(stmt)


async def get_organization_roles_full_json(
    session: AsyncSession, *, guild_id: int
) -> dict[str, dict[str, int]] | None:
    """Get the list of organization roles for a guild."""
    stmt = select(MainGuildConfig.organizational_roles).where(
        MainGuildConfig.guild_id == guild_id
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_organization_roles_ids(
    session: AsyncSession, *, guild_id: int
) -> list[int]:
    """Get the list of organization role IDs for a guild."""
    ids: list[int] = []
    stmt = select(MainGuildConfig.organizational_roles).where(
        MainGuildConfig.guild_id == guild_id
    )
    result = (await session.execute(stmt)).scalar_one_or_none()
    if result is None:
        return []

    for _, value in result.items():
        role_id: int | None = value.get("role_id")
        if role_id is not None:
            ids.append(role_id)

    return ids


async def get_mute_role(session: AsyncSession, *, guild_id: int) -> int | None:
    """Get the mute role for a guild."""
    stmt = select(GuildModerationConfig.mute_role_id).where(
        GuildModerationConfig.guild_id == guild_id
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_mpmute_role(
    session: AsyncSession, *, guild_id: int
) -> int | None:
    """Get the marketplace mute role for a guild."""
    stmt = select(GuildModerationConfig.mpmute_role_id).where(
        GuildModerationConfig.guild_id == guild_id
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_vmute_role(
    session: AsyncSession, *, guild_id: int
) -> int | None:
    """Get the voice mute role for a guild."""
    stmt = select(GuildModerationConfig.vmute_role_id).where(
        GuildModerationConfig.guild_id == guild_id
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_mute_type(session: AsyncSession, *, guild_id: int) -> str | None:
    """Get the mute type for a guild."""
    stmt = select(GuildModerationConfig.mute_type).where(
        GuildModerationConfig.guild_id == guild_id
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
