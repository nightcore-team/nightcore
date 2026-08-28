"""Unified handler for all clan shop interactions."""

from typing import TYPE_CHECKING

from discord.interactions import Interaction

from .approve import handle_approve_clan_shop_button
from .decline import handle_decline_clan_shop_button

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


async def handle_clan_shop_interaction(
    interaction: Interaction["Nightcore"],
    custom_id: str,
) -> None:
    """Route battlepass: interactions to the appropriate handler."""

    match custom_id:
        case "clan_shop:approve":
            await handle_approve_clan_shop_button(interaction=interaction)
        case "clan_shop:decline":
            await handle_decline_clan_shop_button(interaction=interaction)
        case _:
            pass
