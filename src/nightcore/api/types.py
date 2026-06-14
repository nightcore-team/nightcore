"""API types."""

from typing import Annotated

from pydantic import AfterValidator, PlainSerializer


def normalize_discord_id(v: int | str) -> int:
    """Normalize a Discord ID to an integer."""

    return int(v)


DiscordId = Annotated[
    int,
    AfterValidator(normalize_discord_id),
    PlainSerializer(lambda v: str(v), return_type=str),
]
