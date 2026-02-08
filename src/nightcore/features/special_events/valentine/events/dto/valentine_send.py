"""DTO for valentine send event."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from discord import Color, Embed, Guild

from src.nightcore.events.dto.base import BaseEventDTO

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


@dataclass
class ValentineSendEventDTO(BaseEventDTO):
    """DTO for valentine send event."""

    guild: Guild
    event_type: str
    logging_channel_id: int | None
    user_id: int
    reciever_id: int
    text: str

    def build_log_embed(self, bot: "Nightcore") -> Embed:
        """Build and return the log embed for the event."""

        return (
            Embed(
                title="Отправка валентинки",
                timestamp=datetime.now(UTC),
                color=Color.dark_purple(),
            )
            .add_field(
                name="Пользователь",
                value=f"<@{self.user_id}> (`{self.user_id}`)",
                inline=False,
            )
            .add_field(
                name="Получатель",
                value=f"<@{self.reciever_id}> (`{self.reciever_id}`)",
                inline=False,
            )
            .add_field(name="Текст", value=self.text)
        )
