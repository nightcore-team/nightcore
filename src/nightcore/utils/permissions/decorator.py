"""Decorator to check for required permissions before executing a command."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from functools import wraps
from typing import (
    TYPE_CHECKING,
    Any,
    Concatenate,
    ParamSpec,
    TypeVar,
    cast,
    overload,
)

from discord import Interaction, app_commands, Member, Guild

from src.infra.db.models import GuildClansConfig, GuildModerationConfig, GuildEconomyConfig
from src.infra.db.operations import get_specified_field
from src.nightcore.utils import has_any_role_from_sequence

from src.nightcore.exceptions import FieldNotConfiguredError

if TYPE_CHECKING:
    from discord.ext.commands import Cog  # type: ignore
    from sqlalchemy.ext.asyncio import AsyncSession
    from src.nightcore.bot import Nightcore

    from src.infra.db.operations import GuildT

from ._enums import PermissionsFlagEnum

P = ParamSpec("P")
T = TypeVar("T")
CogT = TypeVar("CogT", bound="Cog")


@overload
def check_required_permissions(  # type: ignore
    permissions_flag: PermissionsFlagEnum,
) -> Callable[
    [Callable[Concatenate[Interaction[Nightcore], P], Awaitable[T]]],
    Callable[Concatenate[Interaction[Nightcore], P], Awaitable[T]],
]: ...


@overload
def check_required_permissions(  # type: ignore
    permissions_flag: PermissionsFlagEnum,
) -> Callable[
    [Callable[Concatenate[CogT, Interaction[Nightcore], P], Awaitable[T]]],
    Callable[Concatenate[CogT, Interaction[Nightcore], P], Awaitable[T]],
]: ...


def check_required_permissions(
    permissions_flag: PermissionsFlagEnum,
) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    """Decorator to check for required permissions before executing a command.

    Args:
        permissions_flag: Required permission flag

    Returns:
        Decorated function with permission check

    Example:
        # In Cog:
        @check_required_permissions(PermissionsFlagEnum.ADMINISTRATOR)
        async def my_command(self, interaction: Interaction):
            ...

        # Standalone:
        @check_required_permissions(PermissionsFlagEnum.ADMINISTRATOR)
        async def my_function(interaction: Interaction):
            ...
    """

    def decorator(
        func: Callable[..., Awaitable[Any]],
    ) -> Callable[..., Awaitable[Any]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            interaction: Interaction[Nightcore] | None = None

            for arg in args:
                if isinstance(arg, Interaction):
                    interaction = arg  # type: ignore
                    break

            if not interaction and "interaction" in kwargs:
                interaction = kwargs["interaction"]

            if not interaction:
                raise ValueError(
                    f"Interaction not found in {func.__name__} arguments"
                )

            # Перевіряємо права
            has_permission = await _check_user_permission(
                interaction, permissions_flag
            )

            if not has_permission:
                raise app_commands.MissingPermissions(
                    missing_permissions=[permissions_flag.value]
                )

            return await func(*args, **kwargs)

        wrapper.__permissions_flag__ = permissions_flag  # type: ignore

        return wrapper

    return decorator

async def has_specified_permission(
    user: Member,
    *,
    session: AsyncSession,
    guild_id: int,
    config_type: type[GuildT],
    field_name: str,
    access_name: str,
) -> bool:
    """Check if specified permission exists in guild config.

    Args:
        session: Database session
        guild_id: Guild ID
        config_type: Guild config type

    Returns:
        True if permission exists, False otherwise
    """

    roles_access_ids: Sequence[int] | None = await get_specified_field(
        session,
        guild_id=guild_id,
        config_type=config_type,
        field_name=field_name,
    )
    if not roles_access_ids:
        raise FieldNotConfiguredError(
            access_name
        )

    return bool(has_any_role_from_sequence(
        user, roles_access_ids
    ))



async def _check_user_permission(
    interaction: Interaction[Nightcore],
    permissions: PermissionsFlagEnum,
) -> bool:
    """Check if user has required permission.

    Args:
        interaction: Discord interaction
        permissions: Required permission flag

    Returns:
        True if user has permission, False otherwise
    """

    member = cast(Member, interaction.user)
    bot = interaction.client
    guild = cast(Guild, interaction.guild)

    if not hasattr(member, "guild_permissions"):
        return False

    if permissions == PermissionsFlagEnum.ADMINISTRATOR:
        return member.guild_permissions.administrator

    if permissions == PermissionsFlagEnum.NONE:
        return True

    async with bot.uow.start() as session:
        if permissions == PermissionsFlagEnum.CLANS_ACCESS:
            return await has_specified_permission(
                member,
                session=session,
                guild_id=guild.id,
                config_type=GuildClansConfig,
                field_name="clans_access_roles_ids",
                access_name="доступ к кланам",
            )
        if permissions == PermissionsFlagEnum.MODERATION_ACCESS:
            return await has_specified_permission(
                member,
                session=session,
                guild_id=guild.id,
                config_type=GuildModerationConfig,
                field_name="moderation_access_roles_ids",
                access_name="доступ к модерации",
            )
        if permissions == PermissionsFlagEnum.BAN_ACCESS:
            return await has_specified_permission(
                member,
                session=session,
                guild_id=guild.id,
                config_type=GuildModerationConfig,
                field_name="ban_access_roles_ids",
                access_name="доступ к бану",
            )
        if permissions == PermissionsFlagEnum.HEAD_MODERATION_ACCESS:
            return await has_specified_permission(
                member,
                session=session,
                guild_id=guild.id,
                config_type=GuildModerationConfig,
                field_name="leadership_access_roles_ids",
                access_name="доступ к главной модерации",
            )
        if permissions == PermissionsFlagEnum.ECONOMY_ACCESS:
            return await has_specified_permission(
                member,
                session=session,
                guild_id=guild.id,
                config_type=GuildEconomyConfig,
                field_name="economy_access_roles_ids",
                access_name="доступ к экономике",
            )

    return False
