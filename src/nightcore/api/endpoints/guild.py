"""Guild related endpoints."""

import time
from collections import defaultdict
from typing import Annotated

from fastapi import HTTPException, Query, status
from fastapi.routing import APIRouter

from src.nightcore.api.dependencies import (
    AccessServiceDependency,
    BotDependency,
    GuildStateServiceDependency,
    LoggingRevisionServiceDependency,
    UserIdDependency,
)
from src.nightcore.api.schemas import ChannelInfoSchema, RoleInfoSchema
from src.nightcore.api.schemas.configuration import ConfigUpdateBody
from src.nightcore.api.schemas.logging_revision import (
    ListLoggingRevisionMetaResponseSchema,
    ListLoggingRevisionRequestSchema,
    LoggingRevisionDataSchema,
    LoggingRevisionRequestSchema,
)
from src.nightcore.utils import ensure_member_exists
from src.utils._enums import ConfigTypeEnum

router = APIRouter(prefix="/guilds", tags=["Guild Endpoints"])

# Per-user rate limiting: simple in-memory sliding window
_RATE_LIMIT_WINDOW_SECONDS = 60.0
_RATE_LIMIT_MAX_REQUESTS = 60
_RATE_LIMIT_STORE: dict[int, list[float]] = defaultdict(list)


def _check_per_user_rate_limit(user_id: int) -> None:
    """Enforce per-user rate limit (60 req / 60s)."""

    now = time.monotonic()
    window_start = now - _RATE_LIMIT_WINDOW_SECONDS
    timestamps = _RATE_LIMIT_STORE[user_id]
    # Prune old entries
    _RATE_LIMIT_STORE[user_id] = [t for t in timestamps if t > window_start]
    if len(_RATE_LIMIT_STORE[user_id]) >= _RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Try again later.",
        )
    _RATE_LIMIT_STORE[user_id].append(now)


async def _has_roles_channels_access(member, access_service) -> bool:
    """IDOR fix: require specific privileged config, not any configuration."""
    # Check specific configs that legitimately need role/channel enumeration
    for cfg in (
        ConfigTypeEnum.ACCESS,
        ConfigTypeEnum.MODERATION,
        ConfigTypeEnum.ROLE_REQUEST,
    ):
        try:
            if await access_service.has_config_access(
                member=member, config_type=cfg
            ):
                return True
        except Exception:
            continue
    # Fallback: administrator bypass
    perms = getattr(member, "guild_permissions", None)
    return bool(perms and getattr(perms, "administrator", False))


@router.get(
    "/{guild_id}/available-configurations",
    response_model=list[str],
    status_code=status.HTTP_200_OK,
)
async def get_available_configurations(
    guild_id: int,
    user_id: UserIdDependency,
    bot: BotDependency,
    access_service: AccessServiceDependency,
):
    """Returns a list of accessible guild configurations for the authenticated user."""  # noqa: E501

    _check_per_user_rate_limit(user_id)

    guild = bot.get_guild(guild_id)

    if guild is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Unknown guild"
        )

    member = await ensure_member_exists(guild, user_id)

    if member is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this guild",
        )

    return await access_service.get_available_configurations(member=member)


@router.get(
    "/{guild_id}/roles",
    response_model=list[RoleInfoSchema],
    status_code=status.HTTP_200_OK,
)
async def get_guild_roles(
    guild_id: int,
    user_id: UserIdDependency,
    bot: BotDependency,
    access_service: AccessServiceDependency,
    guild_state_service: GuildStateServiceDependency,
):
    """Get roles for a specific guild."""

    _check_per_user_rate_limit(user_id)

    guild = bot.get_guild(guild_id)

    if guild is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Unknown guild"
        )

    member = await ensure_member_exists(guild, user_id)

    if member is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this guild",
        )

    # IDOR fix: require specific config access, not any
    if not await _has_roles_channels_access(member, access_service):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must have access to a privileged configuration to get guild roles",  # noqa: E501
        )

    return guild_state_service.get_roles(guild)


@router.get(
    "/{guild_id}/channels",
    response_model=list[ChannelInfoSchema],
    status_code=status.HTTP_200_OK,
)
async def get_guild_channels(
    guild_id: int,
    user_id: UserIdDependency,
    bot: BotDependency,
    access_service: AccessServiceDependency,
    guild_state_service: GuildStateServiceDependency,
):
    """Get channels for a specific guild."""

    _check_per_user_rate_limit(user_id)

    guild = bot.get_guild(guild_id)

    if guild is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Unknown guild"
        )

    member = await ensure_member_exists(guild, user_id)

    if member is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this guild",
        )

    # IDOR fix: require specific config access, not any
    if not await _has_roles_channels_access(member, access_service):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must have access to a privileged configuration to get guild channels",  # noqa: E501
        )

    return guild_state_service.get_channels(guild)


@router.get(
    "/{guild_id}/configuration",
    status_code=status.HTTP_200_OK,
    response_model=dict,
)
async def get_guild_configuration(
    guild_id: int,
    config_type: ConfigTypeEnum,
    user_id: UserIdDependency,
    bot: BotDependency,
    access_service: AccessServiceDependency,
    guild_state_service: GuildStateServiceDependency,
):
    """Get configuration for a specific guild."""

    _check_per_user_rate_limit(user_id)

    guild = bot.get_guild(guild_id)

    if guild is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Unknown guild"
        )

    member = await ensure_member_exists(guild, user_id)

    if member is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this guild",
        )

    has_access = await access_service.has_config_access(
        member=member, config_type=config_type
    )

    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this configuration",
        )

    return await guild_state_service.get_config(
        guild=guild,
        config_type=config_type,
    )


@router.patch("/{guild_id}/configuration", status_code=status.HTTP_200_OK)
async def patch_guild_configuration(
    guild_id: int,
    update_data: ConfigUpdateBody,
    user_id: UserIdDependency,
    bot: BotDependency,
    access_service: AccessServiceDependency,
    guild_state_service: GuildStateServiceDependency,
    logging_revision_service: LoggingRevisionServiceDependency,
):
    """Update configuration for a specific guild."""

    _check_per_user_rate_limit(user_id)

    guild = bot.get_guild(guild_id)

    if guild is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Unknown guild"
        )

    member = await ensure_member_exists(guild, user_id)

    if member is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this guild",
        )

    has_access = await access_service.has_config_access(
        member=member, config_type=update_data.config_type
    )

    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this configuration",
        )

    await guild_state_service.update_config(
        member=member,
        config_type=update_data.config_type,
        data=update_data.data,
        logging_revision_service=logging_revision_service,
    )


@router.get(
    "/{guild_id:int}/logging-revisions",
    status_code=status.HTTP_200_OK,
    response_model=ListLoggingRevisionMetaResponseSchema,
)
async def get_guild_logging_revisions(
    guild_id: int,
    params: Annotated[ListLoggingRevisionRequestSchema, Query()],
    user_id: UserIdDependency,
    bot: BotDependency,
    access_service: AccessServiceDependency,
    logging_revision_service: LoggingRevisionServiceDependency,
):
    """List logging revisions for a specific guild."""

    _check_per_user_rate_limit(user_id)

    guild = bot.get_guild(guild_id)

    if guild is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Unknown guild"
        )

    member = await ensure_member_exists(guild, user_id)

    if member is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this guild",
        )

    if params.config_type is not None:
        has_access = await access_service.has_config_access(
            member=member, config_type=params.config_type
        )

        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this configuration",
            )

        config_types: list[ConfigTypeEnum] | None = [params.config_type]
    else:
        available = await access_service.get_available_configurations(
            member=member
        )
        config_types = [ConfigTypeEnum(value) for value in available]

        if not config_types:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to any configuration",
            )

    return await logging_revision_service.list_revisions_by_params(
        guild=guild,
        config_types=config_types,
        user_id=params.user_id,
        date_from=params.date_from,
        date_to=params.date_to,
        limit=params.limit,
        offset=params.offset,
    )


@router.get(
    "/{guild_id:int}/logging-revisions/{revision_id:str}",
    status_code=status.HTTP_200_OK,
    response_model=LoggingRevisionDataSchema,
)
async def get_guild_logging_revision(
    guild_id: int,
    revision_id: str,
    params: Annotated[LoggingRevisionRequestSchema, Query()],
    user_id: UserIdDependency,
    bot: BotDependency,
    access_service: AccessServiceDependency,
    logging_revision_service: LoggingRevisionServiceDependency,
):
    """Get logging revision for specific guild by revision_id."""

    _check_per_user_rate_limit(user_id)

    guild = bot.get_guild(guild_id)

    if guild is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Unknown guild"
        )

    member = await ensure_member_exists(guild, user_id)

    if member is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this guild",
        )

    has_access = await access_service.has_config_access(
        member=member, config_type=params.config_type
    )

    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this configuration",
        )

    return await logging_revision_service.get_by_params(
        guild_id=guild_id,
        revision_id=revision_id,
        config_type=params.config_type,
    )
