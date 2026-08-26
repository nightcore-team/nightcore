"""Unified handler for all battlepass interactions."""

from typing import TYPE_CHECKING

from discord.interactions import Interaction

from ...battlepass.claim import BattlepassClaimViewV2
from ...battlepass.info import BattlepassInfoViewV2
from .claim import handle_battlepass_claim_reward_button
from .info import handle_battlepass_info_button
from .show import handle_battlepass_show_button

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


async def handle_battlepass_interaction(
    interaction: Interaction["Nightcore"],
    custom_id: str,
) -> None:
    """Route battlepass: interactions to the appropriate handler."""

    match custom_id:
        case "battlepass:claim_reward":
            await handle_battlepass_claim_reward_button(
                interaction=interaction,
                view_to_update=BattlepassClaimViewV2,
            )
        case "battlepass:info":
            await handle_battlepass_info_button(
                interaction=interaction,
                view=BattlepassInfoViewV2,
            )
        case str() if custom_id.endswith(":show"):
            await handle_battlepass_show_button(
                interaction=interaction,
            )
        case _:
            pass
