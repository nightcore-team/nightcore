"""Base event DTO protocol."""

from abc import abstractmethod
from typing import TYPE_CHECKING, Protocol

from discord import Embed, Guild
from discord.ui import LayoutView

from src.infra.db.models.discord_webhook import DiscordWebhook

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


class BaseEventDTO(Protocol):
    """Base event DTO protocol."""

    guild: Guild
    event_type: str
    logging_webhook: DiscordWebhook | None

    @abstractmethod
    def build_component(
        self,
        bot: "Nightcore",
    ) -> Embed | LayoutView:
        """Build and return the component for the event."""
