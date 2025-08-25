"""Utility to invalidate async_lru caches."""

from typing import Any, TypeVar

from async_lru import _LRUCacheWrapper  # type: ignore

T = TypeVar("T")


def alru_invalidator(
    func: _LRUCacheWrapper[T],
    *args: Any,
    **kwargs: Any,
) -> None:
    """Decorator to add a cache invalidation method to an async_lru cached function."""  # noqa: E501
    try:
        func.cache_invalidate(*args, **kwargs)  # type: ignore
    except AttributeError:
        func.cache_clear()  # type: ignore
