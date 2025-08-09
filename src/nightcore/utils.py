"""Defines the utility functions for the Nightcore bot."""


def collect_provided_options(**kwargs) -> dict[str, str]:
    """Filters out None values from the provided keyword arguments."""
    return {k: v for k, v in kwargs.items() if v is not None}
