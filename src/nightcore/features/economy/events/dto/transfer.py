"""DTO for user items changed event."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from discord import Color, Embed, Guild, Member

from src.nightcore.events.dto.base import BaseEventDTO

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


@dataclass
class TransferCoinsEventDTO(BaseEventDTO):
    """DTO for user items changed event."""

    guild: Guild
    event_type: str
    logging_channel_id: int | None
    sender_id: int
    receiver: Member
    item_name: str
    amount: int
    comment: str | None = None

    def build_log_embed(self, bot: "Nightcore") -> Embed:
        """Build and return the log embed for the event."""

        return (
            Embed(
                title="Перевод коинов между пользователями",
                timestamp=datetime.now(timezone.utc),
                color=Color.orange(),
            )
            .add_field(
                name="Отправитель",
                value=f"<@{self.sender_id}> (`{self.sender_id}`)",
                inline=False,
            )
            .add_field(
                name="Получатель",
                value=f"<@{self.receiver.id}> (`{self.receiver.id}`)",
                inline=False,
            )
            .add_field(
                name="Коин", value=f"**{self.item_name}**", inline=False
            )
            .add_field(
                name="Количество",
                value=f"**{self.amount}**",
                inline=False,
            )
            .add_field(
                name="Комментарий",
                value=self.comment if self.comment else "Отсутствует",
                inline=False,
            )
            .set_footer(
                text="Powered by nightcore",
                icon_url=bot.user.display_avatar.url,  # type: ignore
            )
        )
