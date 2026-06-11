"""Send a view with FAQ pages command."""

from typing import TYPE_CHECKING, cast

from discord import Guild
from discord.interactions import Interaction

from src.infra.db.models import GuildFaqConfig
from src.nightcore.components.embed import ErrorEmbed
from src.nightcore.components.embed.success import SuccessMoveEmbed
from src.nightcore.features.faq._groups import faq as faq_group
from src.nightcore.features.faq.components.v2 import FAQGlobalViewV2
from src.nightcore.services.config import specified_guild_config

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.decorators.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)


from src.nightcore.decorators.time_executing import time_executing


@faq_group.command(
    name="send",
    description="Отправить представление с страницами FAQ",
)
@check_required_permissions(PermissionsFlagEnum.ADMINISTRATOR)
@time_executing
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
        bot, guild.id, GuildFaqConfig, _create=True
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

        await interaction.channel.send(view=view)  # type: ignore

        await interaction.response.send_message(
            embed=SuccessMoveEmbed(
                "Отправка FAQ",
                "Сообщение FAQ успешно отправлено.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )
