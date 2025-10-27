from dataclasses import dataclass

from discord import Guild

from src.infra.db.models._enums import ShopOrderStateEnum


@dataclass
class CoinsShopOrderNotifyDTO:
    guild: Guild
    user_id: int
    moderator_id: int
    user_balance_before: float
    user_balance_after: float
    item_name: str
    item_price: float
    custom_id: str
    state: ShopOrderStateEnum
    notifications_channel_id: int | None
