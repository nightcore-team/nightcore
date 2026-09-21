"""Handlers for case opening interactions."""

from typing import TYPE_CHECKING

from discord.interactions import Interaction

from .claim import handle_case_open_claim
from .reroll import handle_case_open_reroll

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


async def handle_case_open_interaction(
    interaction: Interaction["Nightcore"],
    custom_id: str,
) -> None:
    """Route case opening reroll and claim actions."""

    parts = custom_id.split(":")
    if len(parts) < 4 or parts[:2] != ["case", "open"]:
        return

    session_id_text = parts[2]
    if not session_id_text.isdigit():
        return
    session_id = int(session_id_text)

    if parts[3] == "claim" and len(parts) == 4:
        await handle_case_open_claim(
            interaction,
            session_id=session_id,
        )
        return

    if parts[3] == "reroll" and len(parts) == 6:
        reward_id_text, page_text = parts[4], parts[5]
        if reward_id_text.isdigit() and page_text.isdigit():
            await handle_case_open_reroll(
                interaction,
                session_id=session_id,
                reward_id=int(reward_id_text),
                page=int(page_text),
            )
        return
