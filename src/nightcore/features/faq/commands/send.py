"""Send a view with FAQ pages command."""

from typing import TYPE_CHECKING, cast

from discord import Guild
from discord.interactions import Interaction

from src.infra.db.models import MainGuildConfig
from src.nightcore.components.embed import ErrorEmbed
from src.nightcore.features.faq._groups import faq as faq_group
from src.nightcore.features.faq.components.v2 import FAQGlobalViewV2
from src.nightcore.services.config import specified_guild_config

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)


@faq_group.command(  # type: ignore
    name="send",
    description="Отправить представление с страницами FAQ",
)
@check_required_permissions(PermissionsFlagEnum.ADMINISTRATOR)
async def send_faq_pages(
    interaction: Interaction["Nightcore"],
    text: str | None = None,
    image_url: str | None = None,
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
        view = FAQGlobalViewV2(bot, text, image_url)

        await interaction.response.send_message(view=view)
