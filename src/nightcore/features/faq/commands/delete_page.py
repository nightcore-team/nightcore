"""Delete an existing FAQ page command."""

from typing import TYPE_CHECKING, cast

from discord import Guild, app_commands
from discord.interactions import Interaction
from sqlalchemy.orm import attributes

from src.infra.db.models import MainGuildConfig
from src.infra.db.models._annot import FAQPageAnnot
from src.nightcore.components.embed import ErrorEmbed, SuccessMoveEmbed
from src.nightcore.features.faq._groups import faq as faq_group
from src.nightcore.features.faq.utils import faq_autocomplete
from src.nightcore.services.config import specified_guild_config

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


@faq_group.command(
    name="delete_page",
    description="Удалить существующую страницу в FAQ",
)
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(page="Страница FAQ для удаления")
@app_commands.autocomplete(page=faq_autocomplete)
async def delete_faq_page(
    interaction: Interaction["Nightcore"],
    page: str,
) -> None:
    """Delete an existing FAQ page in the guild's FAQ configuration."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)

    outcome = ""
    page_to_delete: FAQPageAnnot | None = None

    async with specified_guild_config(bot, guild.id, MainGuildConfig) as (
        guild_config,
        _,
    ):
        for faq_page in guild_config.faq or []:
            if faq_page["title"] == page:
                page_to_delete = faq_page
                break
        else:
            outcome = "page_not_found"

        if not outcome:
            guild_config.faq.remove(page_to_delete)  # type: ignore
            attributes.flag_modified(guild_config, "faq")

            outcome = "success"

    if outcome == "page_not_found":
        await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка удаления страницы FAQ",
                f"Страница с названием '{page}' не найдена в FAQ этого сервера.",  # noqa: E501, RUF001
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )
        return

    if outcome == "success":
        await interaction.response.send_message(
            embed=SuccessMoveEmbed(
                "Удаление страницы FAQ",
                f"Страница FAQ с названием '{page}' успешно удалена.",  # noqa: RUF001
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )
