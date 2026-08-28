"""Interaction events module."""

import logging
from typing import TYPE_CHECKING

from discord import app_commands
from discord.interactions import Interaction

from src.nightcore.components.view.v2 import MissingPermissionsViewV2
from src.nightcore.features.clans.components.v2.view.handlers import (
    handle_clan_shop_interaction,
)
from src.nightcore.features.clans.components.v2.view.handlers.info import (
    handle_clan_info_button,
)
from src.nightcore.features.economy.components.v2.view.handlers import (
    handle_battlepass_interaction,
    handle_roulette_multiplayer_join_button_callback,
)
from src.nightcore.features.faq.components.v2.view.handlers import (
    handle_faq_interaction,
)
from src.nightcore.features.meta.components.v2.view.handlers.roleselector import (  # noqa: E501
    handle_role_selector_select,
)
from src.nightcore.features.moderation.components.modal.handlers import (
    handle_inactive_reject_modal_submit,
)
from src.nightcore.features.moderation.components.v2.view.handlers import (
    handle_inactive_request_button_callback,
    handle_notify_revoke_button,
)
from src.nightcore.features.role_requests.components.v2.view.handlers import (
    handle_role_request_interaction,
)
from src.nightcore.features.tickets.components.v2.view.handlers import (
    handle_ticket_interaction,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


async def setup(bot: "Nightcore") -> None:
    """Setup interaction events for the Nightcore bot."""

    @bot.event
    async def on_interaction(interaction: Interaction["Nightcore"]) -> None:  # type: ignore
        """Handle interactions."""

        custom_id = interaction.data.get("custom_id", None)  # type: ignore

        if custom_id:
            match custom_id:
                case str() if custom_id.startswith("faq:"):
                    await handle_faq_interaction(
                        interaction=interaction,
                        custom_id=custom_id,
                    )
                case str() if custom_id.startswith("battlepass"):
                    await handle_battlepass_interaction(
                        interaction=interaction,
                        custom_id=custom_id,
                    )

                case str() if custom_id.startswith("clan:"):
                    await handle_clan_info_button(interaction=interaction)

                case str() if custom_id.startswith("clan_shop:"):
                    await handle_clan_shop_interaction(
                        interaction=interaction, custom_id=custom_id
                    )

                case str() if custom_id.startswith("role_request:"):
                    await handle_role_request_interaction(
                        interaction=interaction,
                        custom_id=custom_id,
                    )

                case str() if custom_id.startswith("role_selector:"):
                    await handle_role_selector_select(interaction=interaction)

                case str() if custom_id.startswith("ticket:"):
                    await handle_ticket_interaction(
                        interaction=interaction,
                        custom_id=custom_id,
                    )

                case str() if custom_id.startswith("casino:"):
                    match custom_id:
                        case "casino:roulette:multiplayer":
                            await handle_roulette_multiplayer_join_button_callback(  # noqa: E501
                                interaction=interaction,
                            )
                        case _:
                            ...

                case str() if custom_id.startswith("inactive:"):
                    try:
                        await handle_inactive_request_button_callback(
                            interaction, custom_id=custom_id
                        )

                    except app_commands.MissingPermissions as e:
                        missing_perms = getattr(e, "missing_permissions", [])

                        if not interaction.response.is_done():
                            await interaction.response.send_message(
                                view=MissingPermissionsViewV2(
                                    "Вам не хватает следующих прав для "
                                    f"использования этой команды: {', '.join(missing_perms)}.",  # noqa: E501
                                ),
                                ephemeral=True,
                            )
                        else:
                            await interaction.followup.send(
                                view=MissingPermissionsViewV2(
                                    "Вам не хватает следующих прав для "
                                    f"использования этой команды: {missing_perms}.",  # noqa: E501
                                ),
                                ephemeral=True,
                            )

                case str() if custom_id.startswith("inactive_modal:"):
                    try:
                        await handle_inactive_reject_modal_submit(interaction)
                    except app_commands.MissingPermissions as e:
                        missing_perms = getattr(e, "missing_permissions", [])

                        if not interaction.response.is_done():
                            await interaction.response.send_message(
                                view=MissingPermissionsViewV2(
                                    "Вам не хватает следующих прав для "
                                    f"использования этой команды: {', '.join(missing_perms)}.",  # noqa: E501
                                ),
                                ephemeral=True,
                            )
                        else:
                            await interaction.followup.send(
                                view=MissingPermissionsViewV2(
                                    "Вам не хватает следующих прав для "
                                    f"использования этой команды: {missing_perms}.",  # noqa: E501
                                ),
                                ephemeral=True,
                            )

                case "notify:revoke":
                    try:
                        await handle_notify_revoke_button(interaction)
                    except app_commands.MissingPermissions as e:
                        missing_perms = getattr(e, "missing_permissions", [])

                        if not interaction.response.is_done():
                            await interaction.response.send_message(
                                view=MissingPermissionsViewV2(
                                    "Вам не хватает следующих прав для "
                                    f"использования этой команды: {', '.join(missing_perms)}.",  # noqa: E501
                                ),
                                ephemeral=True,
                            )
                        else:
                            await interaction.followup.send(
                                view=MissingPermissionsViewV2(
                                    "Вам не хватает следующих прав для "
                                    f"использования этой команды: {missing_perms}.",  # noqa: E501
                                ),
                                ephemeral=True,
                            )

                case _:  # type: ignore
                    logger.info(
                        "[interaction] Unknown custom_id (likely slash command): %s",  # noqa: E501
                        interaction.type,
                    )

        logger.info(
            "[interaction] Handle interaction: %s from user: %s, custom_id: %s",  # noqa: E501
            interaction.type,
            interaction.user.id,
            custom_id,
        )
