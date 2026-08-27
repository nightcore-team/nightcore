"""Handlers for FAQ global button interactions."""

from typing import TYPE_CHECKING, cast

from discord import Guild
from discord.interactions import Interaction

from src.infra.db.models import GuildFaqConfig
from src.nightcore.components.view.v2 import ErrorViewV2
from src.nightcore.features.faq.utils.pages import build_faq_page_components
from src.nightcore.services.config import specified_guild_config

from ..faq import FAQPageViewV2, FAQViewV2
from .section import handle_faq_button_callback

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


async def handle_faq_interaction(
    interaction: Interaction["Nightcore"],
    custom_id: str,
) -> None:
    """Route faq: interactions to the appropriate handler."""

    match custom_id:
        case "faq:open_faq":
            await _handle_faq_open(
                interaction=interaction,
                view_class=FAQViewV2,
            )
        case str() if custom_id.startswith("faq:page:"):
            page_title = custom_id.split(":", 2)[2]
            await handle_faq_button_callback(
                interaction=interaction,
                view=FAQPageViewV2,
                page_title=page_title,
            )
        case _:
            pass


async def _handle_faq_open(
    interaction: Interaction["Nightcore"],
    view_class: type[FAQViewV2],
) -> None:
    """Send a view with FAQ pages."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)

    outcome = ""
    async with specified_guild_config(bot, guild.id, GuildFaqConfig) as (
        guild_config,
        _,
    ):
        faq_pages = guild_config.faq or []
        if not faq_pages:
            outcome = "no_pages"

        if not outcome:
            outcome = "success"

    if outcome == "no_pages":
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка отправки FAQ",
                "В FAQ этого сервера нет страниц для отображения.",
            ),
            ephemeral=True,
        )
        return

    if outcome == "success":
        pages = build_faq_page_components(pages=faq_pages)

        faq_view = view_class(
            bot=bot,
            pages=pages,
            _build=True,
        )

        await interaction.response.send_message(view=faq_view, ephemeral=True)
