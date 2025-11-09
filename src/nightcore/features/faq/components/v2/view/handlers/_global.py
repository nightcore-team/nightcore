"""Handlers for FAQ global button interactions."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from discord import Guild
from discord.interactions import Interaction

from src.infra.db.models import MainGuildConfig
from src.nightcore.components.embed import ErrorEmbed
from src.nightcore.features.faq.utils.pages import build_faq_page_components
from src.nightcore.services.config import specified_guild_config

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

    from ..faq import FAQViewV2


async def handle_faq_global_button_callback(
    interaction: Interaction[Nightcore],
    view_class: type[FAQViewV2],
) -> None:
    """Send a view with FAQ pages."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)

    outcome = ""
    async with specified_guild_config(
        bot, guild.id, MainGuildConfig, _create=True
    ) as (
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
            embed=ErrorEmbed(
                "Ошибка отправки FAQ",
                "В FAQ этого сервера нет страниц для отображения.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
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
