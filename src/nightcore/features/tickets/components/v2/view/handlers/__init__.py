"""Unified handler for all ticket interactions."""

from typing import TYPE_CHECKING

from discord import app_commands
from discord.interactions import Interaction

from src.nightcore.components.view.v2 import MissingPermissionsViewV2

from .create import handle_ticket_create_button
from .manage import (
    handle_ticket_close_button,
    handle_ticket_pin_button,
    handle_ticket_reopen_button,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


async def handle_ticket_interaction(
    interaction: Interaction["Nightcore"],
    custom_id: str,
) -> None:
    """Route ticket: interactions to the appropriate handler."""

    try:
        match custom_id:
            case "ticket:create":
                await handle_ticket_create_button(interaction)
            case "ticket:pin":
                await handle_ticket_pin_button(interaction)
            case "ticket:reopen":
                await handle_ticket_reopen_button(interaction)
            case "ticket:close":
                await handle_ticket_close_button(interaction)
            case _:
                pass

    except app_commands.MissingPermissions as e:
        missing_perms = getattr(e, "missing_permissions", [])

        if not interaction.response.is_done():
            await interaction.response.send_message(
                view=MissingPermissionsViewV2(
                    "Вам не хватает следующих прав для "
                    f"использования этой команды: {', '.join(missing_perms)}.",
                ),
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                view=MissingPermissionsViewV2(
                    "Вам не хватает следующих прав для "
                    f"использования этой команды: {missing_perms}.",
                ),
                ephemeral=True,
            )
