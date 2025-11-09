"""Decorator to check for required permissions before executing a command."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from functools import wraps
from typing import (
    TYPE_CHECKING,
    Any,
    Concatenate,
    ParamSpec,
    TypeVar,
    overload,
)

from discord import Interaction, app_commands

if TYPE_CHECKING:
    from discord.ext.commands import Cog  # type: ignore

    from src.nightcore.bot import Nightcore

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

    member = interaction.user

    if not hasattr(member, "guild_permissions"):
        return False

    if permissions == PermissionsFlagEnum.ADMINISTRATOR:
        return member.guild_permissions.administrator  # type: ignore

    return False
