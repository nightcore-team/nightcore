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

from discord import Guild, Interaction, Member, app_commands

from src.infra.db.operations import get_specified_field
from src.nightcore.exceptions import FieldNotConfiguredError
from src.nightcore.utils import has_any_role_from_sequence

if TYPE_CHECKING:
    from discord.ext.commands import Cog  # type: ignore
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.infra.db.operations import GuildT
    from src.nightcore.bot import Nightcore

from .types import PERMISSION_CONFIG_MAP, PermissionsFlagEnum

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
        ```
        @check_required_permissions(PermissionsFlagEnum.ADMINISTRATOR)
        async def my_command(self, interaction: Interaction):
            ...
        ```

        # Standalone:
        ```
        @check_required_permissions(PermissionsFlagEnum.ADMINISTRATOR)
        async def my_function(interaction: Interaction):
            ...
        ```
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
                    f"Interaction not found in {func.__class__.__qualname__} arguments"  # noqa: E501
                )

            has_permission = await _check_user_permission(
                interaction, permissions_flag
            )

            if not has_permission:
                raise app_commands.MissingPermissions(
                    missing_permissions=[permissions_flag.value]
                )

            func.__permissions_flag__ = permissions_flag  # type: ignore

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
        user: Discord member
        session: Database session
        guild_id: Guild ID
        config_type: Guild config type
        field_name: Field name in guild config
        access_name: Access name for error message

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
        raise FieldNotConfiguredError(access_name)

    return bool(has_any_role_from_sequence(user, roles_access_ids))


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

    if permissions == PermissionsFlagEnum.UNSAFE:
        """
            >>> UNSAFE permission bypasses all checks and always returns True.
            So, if a command is marked with UNSAFE, it means that you have
            to check manually user's permissions inside the command implementation.
        """  # noqa: E501

        return True

    if permissions == PermissionsFlagEnum.NONE:
        return True

    async with bot.uow.start() as session:
        if permissions in PERMISSION_CONFIG_MAP:
            config_type, field_name, access_name = PERMISSION_CONFIG_MAP[
                permissions
            ]

            async with bot.uow.start() as session:
                return await has_specified_permission(
                    member,
                    session=session,
                    guild_id=guild.id,
                    config_type=config_type,
                    field_name=field_name,
                    access_name=access_name,
                )

    return False
