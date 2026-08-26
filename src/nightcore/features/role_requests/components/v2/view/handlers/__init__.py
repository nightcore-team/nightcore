"""Unified handler for role_request interactions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .approve import handle_approve
from .cancel import handle_cancel
from .decline import handle_decline
from .remove_roles import handle_remove_roles
from .select_role import handle_role_select_button_callback

if TYPE_CHECKING:
    from discord.interactions import Interaction

    from src.nightcore.bot import Nightcore


async def handle_role_request_interaction(
    interaction: Interaction[Nightcore],
    custom_id: str,
) -> None:
    """Route role_request: interactions to the appropriate handler."""

    from ..check_role_request import CheckRoleRequestView
    from ..send_role_request import SendRoleRequestView

    bot = interaction.client

    match custom_id:
        case "role_request:approve":
            view = CheckRoleRequestView(bot)
            await handle_approve(interaction=interaction, view=view)
        case "role_request:decline":
            view = CheckRoleRequestView(bot)
            await handle_decline(interaction=interaction, view=view)
        case "role_request:cancel":
            view = SendRoleRequestView(bot)
            await handle_cancel(interaction=interaction, view=view)
        case "role_request:remove_roles":
            view = SendRoleRequestView(bot)
            await handle_remove_roles(interaction=interaction, view=view)
        case str() if custom_id.startswith("role_request:select_"):
            await handle_role_select_button_callback(
                interaction=interaction,
            )
        case _:
            pass
