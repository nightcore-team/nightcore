"""DTO for notifying about clan shop purchases."""

from dataclasses import dataclass

from src.infra.db.models._enums import ShopOrderStateEnum


@dataclass
class ClanShopPurchaseNotifyDTO:
    guild_id: int
    user_id: int
    moderator_id: int
    clan_name: str
    clan_balance_before: float
    clan_balance_after: float
    item_name: str
    item_price: float
    custom_id: str
    state: ShopOrderStateEnum
    notifications_channel_id: int | None
