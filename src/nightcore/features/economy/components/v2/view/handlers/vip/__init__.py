"""Unified handler for all VIP interactions."""

from typing import TYPE_CHECKING

from discord.interactions import Interaction

from .activate import handle_vip_activate_button

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


async def handle_vip_interaction(
    interaction: Interaction["Nightcore"],
    custom_id: str,
) -> None:
    """Route vip: interactions to the appropriate handler."""

    match custom_id:
        case str() if custom_id.startswith(
            "vip:activate:"
        ) and custom_id not in {
            "vip:activate:prev",
            "vip:activate:next",
        }:
            vip_id = custom_id.rsplit(":", maxsplit=1)[-1]

            if vip_id.isdigit():
                await handle_vip_activate_button(
                    interaction=interaction,
                    vip_id=int(vip_id),
                )
        case _:
            pass
