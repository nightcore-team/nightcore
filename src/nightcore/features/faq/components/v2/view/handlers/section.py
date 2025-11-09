"""Handlers for FAQ page button interactions."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from discord import Guild
from discord.interactions import Interaction

from src.infra.db.models import MainGuildConfig
from src.infra.db.models._annot import FAQPageAnnot
from src.nightcore.components.embed import ErrorEmbed
from src.nightcore.services.config import specified_guild_config

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

    from ..faq import FAQPageViewV2


async def handle_faq_button_callback(
    interaction: Interaction[Nightcore],
    view: type[FAQPageViewV2],
    page_title: str,
) -> None:
    """Handle FAQ page button clicks and return page content."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)

    faq_page: FAQPageAnnot | None = None
    outcome = ""
    async with specified_guild_config(bot, guild.id, MainGuildConfig) as (
        guild_config,
        _,
    ):
        faq_pages = guild_config.faq or []

        for page in faq_pages:
            if page["title"] == page_title:
                faq_page = page
                break
        else:
            outcome = "page_not_found"

        if not outcome:
            outcome = "success"

    if outcome == "page_not_found":
        await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка получения страницы FAQ",
                f"Страница с названием '{page_title}' не найдена в FAQ этого сервера.",  # noqa: E501
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )
        return

    if outcome == "success" and faq_page:
        await interaction.response.send_message(
            view=view(bot, faq_page), ephemeral=True
        )
