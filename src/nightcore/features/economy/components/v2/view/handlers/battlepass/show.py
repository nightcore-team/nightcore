"""
Battlepass show button handler.

Handles displaying the battlepass claim view from the user profile.
"""

from typing import TYPE_CHECKING

from discord.interactions import Interaction

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


async def handle_battlepass_show_button(
    interaction: Interaction["Nightcore"],
) -> None:
    """Handle battlepass show button on the user profile."""

    from src.nightcore.services.battlepass import (
        send_battlepass_claim_view,
    )

    custom_id = interaction.data.get("custom_id", "")  # type: ignore
    # custom_id format: "battlepass:{user_id}:show"
    parts = custom_id.split(":")

    target_user_id: int | None = None
    if len(parts) == 3 and parts[1].isdigit():
        target_user_id = int(parts[1])

    await send_battlepass_claim_view(
        interaction.client,
        interaction,
        user_id=target_user_id,
    )
