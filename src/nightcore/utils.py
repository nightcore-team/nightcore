"""Defines the utility functions for the Nightcore bot."""

from typing import Any


def collect_provided_options(
    **kwargs: Any,
) -> dict[str, int | float | str | list[int] | list[str]]:
    """Filters out None values from the provided keyword arguments."""
    out: dict[str, Any] = {}
    for k, v in kwargs.items():
        if v is None:
            continue

        if hasattr(v, "id"):
            out[k] = v.id
        else:
            out[k] = v
    return out
