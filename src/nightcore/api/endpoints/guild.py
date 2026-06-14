"""Guild related endpoints."""

from fastapi import HTTPException, status
from fastapi.routing import APIRouter

from src.utils._enums import ConfigTypeEnum

from ..dependencies import (
    AccessServiceDependency,
    BotDependency,
    GuildStateServiceDependency,
    UserIdDependency,
)
from ..schemas import ChannelInfoSchema, RoleInfoSchema
from ..schemas.configuration import ConfigUpdateBody

router = APIRouter(prefix="/guilds", tags=["Guild Endpoints"])


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

    guild = bot.get_guild(guild_id)

    if guild is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Unknown guild"
        )

    member = guild.get_member(user_id)

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

    guild = bot.get_guild(guild_id)

    if guild is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Unknown guild"
        )

    member = guild.get_member(user_id)

    if member is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this guild",
        )

    available_configurations = (
        await access_service.get_available_configurations(member=member)
    )

    if len(available_configurations) < 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must have access to at least one configuration to get guild roles",  # noqa: E501
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

    guild = bot.get_guild(guild_id)

    if guild is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Unknown guild"
        )

    member = guild.get_member(user_id)

    if member is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this guild",
        )

    available_configurations = (
        await access_service.get_available_configurations(member=member)
    )

    if len(available_configurations) < 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must have access to at least one configuration to get guild channels",  # noqa: E501
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

    guild = bot.get_guild(guild_id)

    if guild is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Unknown guild"
        )

    member = guild.get_member(user_id)

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
):
    """Update configuration for a specific guild."""

    guild = bot.get_guild(guild_id)

    if guild is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Unknown guild"
        )

    member = guild.get_member(user_id)

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
        guild=guild,
        config_type=update_data.config_type,
        data=update_data.data,
    )
