"""Unified handler for all coins shop interactions."""

from typing import TYPE_CHECKING

from discord.interactions import Interaction

from .approve import handle_approve_coins_shop_order_button
from .decline import handle_decline_coins_shop_order_button

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


async def handle_coins_shop_interaction(
    interaction: Interaction["Nightcore"],
    custom_id: str,
) -> None:
    """Route coins_shop: interactions to the appropriate handler."""

    match custom_id:
        case "coins_shop:approve":
            await handle_approve_coins_shop_order_button(
                interaction=interaction,
            )
        case "coins_shop:decline":
            await handle_decline_coins_shop_order_button(
                interaction=interaction,
            )
        case _:
            pass
