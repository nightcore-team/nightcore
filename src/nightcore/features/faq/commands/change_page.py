"""Change an existing FAQ page command."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, app_commands
from discord.interactions import Interaction

from src.infra.db.models import MainGuildConfig
from src.infra.db.models._annot import FAQPageAnnot
from src.nightcore.components.embed import ErrorEmbed
from src.nightcore.features.faq._groups import faq as faq_group
from src.nightcore.features.faq.components.modal import ChangeFAQPageModal
from src.nightcore.features.faq.utils import faq_autocomplete
from src.nightcore.services.config import specified_guild_config

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

logger = logging.getLogger(__name__)


@faq_group.command(  # type: ignore
    name="change_page",
    description="Изменить существующую страницу в FAQ",
)
@app_commands.describe(page="Страница FAQ для изменения")
@app_commands.autocomplete(page=faq_autocomplete)
@check_required_permissions(PermissionsFlagEnum.ADMINISTRATOR)
async def change_faq_page(
    interaction: Interaction["Nightcore"],
    page: str,
) -> None:
    """Change an existing FAQ page in the guild's FAQ configuration."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)

    outcome = ""
    page_to_change: FAQPageAnnot | None = None

    async with specified_guild_config(bot, guild.id, MainGuildConfig) as (
        guild_config,
        _,
    ):
        for faq_page in guild_config.faq or []:
            if faq_page["title"] == page:
                page_to_change = faq_page
                break
        else:
            outcome = "page_not_found"

        if not outcome:
            outcome = "success"

    if outcome == "page_not_found":
        await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка изменения страницы FAQ",
                f"Страница с названием '{page}' не найдена в FAQ этого сервера.",  # noqa: E501
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )
        return

    if outcome == "success":
        modal = ChangeFAQPageModal(bot=interaction.client, page=page_to_change)  # type: ignore
        await interaction.response.send_modal(modal)

    logger.info(
        "[command] - invoked user=%s guild=%s page=%s",
        interaction.user.id,
        guild.id,
        page,
    )
