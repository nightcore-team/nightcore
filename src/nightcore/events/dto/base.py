"""Base event DTO protocol."""

from abc import abstractmethod
from typing import TYPE_CHECKING, Protocol

from discord import Embed, Guild

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


class BaseEventDTO(Protocol):
    """Base event DTO protocol."""

    guild: Guild
    event_type: str
    logging_channel_id: int | None

    @abstractmethod
    def build_log_embed(
        self,
        bot: "Nightcore",
    ) -> Embed:
        """Build and return the log embed for the event."""
