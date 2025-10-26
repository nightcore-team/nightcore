"""DTO for user items changed event."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from discord import Color, Embed, Guild

from src.nightcore.events.dto.base import BaseEventDTO

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


@dataclass
class AwardNotificationEventDTO(BaseEventDTO):
    """DTO for user items changed event."""

    guild: Guild
    event_type: str
    logging_channel_id: int | None
    user_id: int
    moderator_id: int
    item_name: str
    amount: int

    def build_log_embed(self, bot: "Nightcore") -> Embed:
        """Build and return the log embed for the event."""

        return (
            Embed(
                title="Выдача предмета пользователю",
                timestamp=datetime.now(timezone.utc),
                color=Color.dark_purple(),
            )
            .add_field(
                name="Выдал",
                value=f"<@{self.moderator_id}> (`{self.moderator_id}`)",
            )
            .add_field(
                name="Пользователь",
                value=f"<@{self.user_id}> (`{self.user_id}`)",
                inline=False,
            )
            .add_field(name="Предмет", value=f"**{self.item_name}**")
            .add_field(
                name="Количество",
                value=f"**{self.amount}**",
            )
            .set_footer(
                text="Powered by nightcore",
                icon_url=bot.user.display_avatar.url,  # type: ignore
            )
        )
