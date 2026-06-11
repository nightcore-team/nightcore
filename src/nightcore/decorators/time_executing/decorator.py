"""Decorator to measure and log command execution time."""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
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

from discord import Interaction

if TYPE_CHECKING:
    from discord.ext.commands import Cog  # type: ignore

    from src.nightcore.bot import Nightcore

from .patch_methods import patch_interaction_send_methods

P = ParamSpec("P")
T = TypeVar("T")
CogT = TypeVar("CogT", bound="Cog")

logger = logging.getLogger(__name__)


@overload
def time_executing[**P, T](
    func: Callable[Concatenate[Interaction[Nightcore], P], Awaitable[T]],
) -> Callable[Concatenate[Interaction[Nightcore], P], Awaitable[T]]: ...


@overload
def time_executing[CogT: "Cog", **P, T](
    func: Callable[Concatenate[CogT, Interaction[Nightcore], P], Awaitable[T]],
) -> Callable[Concatenate[CogT, Interaction[Nightcore], P], Awaitable[T]]: ...


def time_executing(
    func: Callable[..., Awaitable[Any]],
) -> Callable[..., Awaitable[Any]]:
    """Measure and log the execution time of a command.

    Automatically extracts the `Interaction` from the decorated function's
    arguments and records how long the command takes to run.

    Args:
        func: The command coroutine to wrap.

    Returns:
        The wrapped coroutine with timing instrumentation.

    Example:
        # In Cog:
        ```
        @time_executing
        async def my_command(self, interaction: Interaction, ...):
            ...
        ```

        # Standalone:
        ```
        @time_executing
        async def my_command(interaction: Interaction, ...):
            ...
        ```
    """

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        interaction: Interaction[Nightcore] | None = None

        for arg in args:
            if isinstance(arg, Interaction):
                interaction = cast(Interaction[Nightcore], arg)
                break

        if not interaction and "interaction" in kwargs:
            interaction = cast(Interaction[Nightcore], kwargs["interaction"])

        if not interaction:
            raise ValueError(
                f"Interaction not found in {func.__class__.__qualname__} arguments"  # noqa: E501
            )

        start_time = time.perf_counter()

        patch_interaction_send_methods(interaction)

        try:
            result = await func(*args, **kwargs)
        finally:
            end_time = time.perf_counter()
            logger.info(
                "[decorator/time_executing] - Executed %s in %.2f ms",
                func.__qualname__,
                (end_time - start_time) * 1000,
            )

        return result

    return wrapper
