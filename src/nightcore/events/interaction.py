"""Interaction events module."""

import logging
from typing import TYPE_CHECKING

from discord.interactions import Interaction

from src.nightcore.features.battlepass.components.v2.view.claim import (
    BattlepassClaimViewV2,
)
from src.nightcore.features.battlepass.components.v2.view.handlers.claim import (  # noqa: E501
    handle_battlepass_claim_reward_button,
)
from src.nightcore.features.battlepass.components.v2.view.handlers.info import (  # noqa: E501
    handle_battlepass_info_button,
)
from src.nightcore.features.battlepass.components.v2.view.info import (
    BattlepassInfoViewV2,
)
from src.nightcore.features.faq.components.v2.view.faq import (
    FAQPageViewV2,
    FAQViewV2,
)
from src.nightcore.features.faq.components.v2.view.handlers import (
    handle_faq_button_callback,
    handle_faq_global_button_callback,
)
from src.nightcore.features.meta.components.v2.view.handlers.roleselector import (  # noqa: E501
    handle_role_selector_select,
)
from src.nightcore.features.role_requests.components.v2 import (
    SendRoleRequestView,
)
from src.nightcore.features.role_requests.components.v2.view.handlers import (
    handle_role_select_button_callback,
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
                case str() if custom_id.startswith("faq_page"):
                    await handle_faq_button_callback(
                        interaction=interaction,
                        view=FAQPageViewV2,
                        page_title=custom_id.split(":")[1],
                    )
                case str() if custom_id.startswith("faq:open_faq"):
                    await handle_faq_global_button_callback(
                        interaction=interaction,
                        view_class=FAQViewV2,
                    )
                case str() if custom_id.startswith("battlepass"):
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
                        case _:
                            ...
                case str() if custom_id.startswith("role_request:select_"):
                    await handle_role_select_button_callback(
                        interaction=interaction,
                        view=SendRoleRequestView,
                    )
                case str() if custom_id.startswith("role_selector:"):
                    await handle_role_selector_select(interaction=interaction)

                case _:  # type: ignore
                    logger.error(
                        "[interaction] Could not found custom id in interaction, possible slash command used: %s",  # noqa: E501
                        interaction.type,
                    )

        logger.info(
            "[interaction] Handle interaction: %s from user: %s, custom_id: %s",  # noqa: E501
            interaction.type,
            interaction.user.id,
            interaction.data["custom_id"],  # type: ignore
        )
