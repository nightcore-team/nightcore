"""DTO for clan shop order notification event."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from discord import Color, Embed, Guild

from src.infra.db.models._enums import ShopOrderStateEnum
from src.nightcore.events.dto.base import BaseEventDTO

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


@dataclass
class ClanShopOrderNotifyDTO(BaseEventDTO):
    guild: Guild
    event_type: str
    user_id: int
    moderator_id: int
    clan_name: str
    clan_balance_before: float
    clan_balance_after: float
    item_name: str
    item_price: float
    custom_id: int
    state: ShopOrderStateEnum
    logging_channel_id: int | None
    notifications_channel_id: int | None

    def build_log_embed(self, bot: "Nightcore") -> Embed:
        """Build and return the log embed for the event."""

        if self.state == ShopOrderStateEnum.APPROVED:
            color = Color.green()
        else:
            color = Color.red()

        return (
            Embed(
                title="Покупка в клановом магазине",
                timestamp=datetime.now(UTC),
                color=color,
            )
            .add_field(
                name="Клан",
                value=f"**{self.clan_name}**",
                inline=False,
            )
            .add_field(
                name="Покупатель",
                value=f"<@{self.user_id}> (`{self.user_id}`)",
                inline=False,
            )
            .add_field(name="Предмет", value=f"**{self.item_name}**")
            .add_field(
                name="Цена",
                value=f"**{self.item_price}**",
            )
            .add_field(
                name="Баланс клана до покупки",
                value=f"**{self.clan_balance_before}**",
                inline=False,
            )
            .add_field(
                name="Баланс клана после покупки",
                value=f"**{self.clan_balance_after}**",
            )
            .add_field(
                name="Модератор",
                value=f"<@{self.moderator_id}> (`{self.moderator_id}`)",
                inline=False,
            )
            .add_field(
                name="Статус заказа",
                value=f"**{self.state.value}**",
                inline=False,
            )
            .set_footer(
                text="Powered by nightcore",
                icon_url=bot.user.display_avatar.url,  # type: ignore
            )
        )
