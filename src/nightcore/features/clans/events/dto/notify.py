"""DTO for notifying about clan shop purchases."""

from dataclasses import dataclass

from src.infra.db.models._enums import ShopOrderStateEnum


@dataclass
class ClanShopPurchaseNotifyDTO:
    guild_id: int
    user_id: int
    moderator_id: int
    clan_name: str
    clan_role_id: int
    clan_balance_before: float
    item_name: str
    item_price: float
    custom_id: str
    state: ShopOrderStateEnum
