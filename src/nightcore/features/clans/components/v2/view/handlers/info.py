"""
Clan info button handler.

Handles displaying clan information from the user profile.
"""

from typing import TYPE_CHECKING

from discord.interactions import Interaction

from src.nightcore.services.clan import send_clan_info_view

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


async def handle_clan_info_button(
    interaction: Interaction["Nightcore"],
) -> None:
    """Handle clan info button on the user profile."""

    custom_id = interaction.data.get("custom_id", "")  # type: ignore
    # custom_id format: "clan:{user_id}:info"
    parts = custom_id.split(":")

    target_user_id: int | None = None
    if len(parts) == 3 and parts[1].isdigit():
        target_user_id = int(parts[1])

    await send_clan_info_view(
        interaction.client,
        interaction,
        user_id=target_user_id,
    )
