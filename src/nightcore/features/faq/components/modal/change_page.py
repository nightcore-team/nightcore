"""

Change FAQ Page Modal Component.

Used for changing FAQ page details in guilds.
"""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, TextStyle
from discord.interactions import Interaction
from discord.ui import Modal, TextInput
from sqlalchemy.orm import attributes

from src.infra.db.models import MainGuildConfig
from src.infra.db.models._annot import FAQPageAnnot
from src.nightcore.components.embed import (
    NoOptionsSuppliedEmbed,
    SuccessMoveEmbed,
)
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils.content import is_image_url

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


class ChangeFAQPageModal(Modal, title="Настроить страницу"):
    page_title = TextInput["ChangeFAQPageModal"](
        label="Новый заголовок страницы",
        style=TextStyle.short,
        placeholder="Введите заголовок страницы",
        required=False,
        max_length=100,
    )

    little_description = TextInput["ChangeFAQPageModal"](
        label="Новое краткое описание",
        style=TextStyle.paragraph,
        placeholder="Введите краткое описание страницы",
        required=False,
        max_length=200,
    )

    content = TextInput["ChangeFAQPageModal"](
        label="Новое содержание страницы",
        style=TextStyle.paragraph,
        placeholder="Введите содержание страницы",
        required=False,
        max_length=3000,
    )

    image_url = TextInput["ChangeFAQPageModal"](
        label="Ссылка на изображение",
        placeholder="Пример: https://example.com/image.png",
        required=False,
        style=TextStyle.short,
        max_length=300,
    )

    def __init__(self, bot: "Nightcore", page: FAQPageAnnot) -> None:
        super().__init__()
        self.bot = bot
        self.page = page

    async def on_submit(self, interaction: Interaction) -> None:
        """Handle the submission of the FAQ page modal."""

        guild = cast(Guild, interaction.guild)

        title = self.page_title.value
        description = self.little_description.value
        content = self.content.value
        image_url = self.image_url.value

        outcome = ""

        async with specified_guild_config(
            self.bot, guild.id, MainGuildConfig
        ) as (
            guild_config,
            _,
        ):
            for faq_page in guild_config.faq or []:
                if faq_page["title"] == self.page["title"]:
                    if title:
                        faq_page["title"] = title
                        outcome = "modified"
                    if description:
                        faq_page["description"] = description
                        outcome = "modified"
                    if content:
                        faq_page["content"] = content
                        outcome = "modified"

                    if image_url:
                        if not is_image_url(image_url):
                            image_url = None

                        faq_page["image_url"] = image_url
                        outcome = "modified"

            if outcome != "":
                attributes.flag_modified(guild_config, "faq")
                outcome = "success"

        if outcome == "":
            await interaction.response.send_message(
                embed=NoOptionsSuppliedEmbed(
                    self.bot.user.display_name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )
            return

        if outcome == "success":
            await interaction.response.send_message(
                embed=SuccessMoveEmbed(
                    "Изменение страницы FAQ",
                    f"Страница FAQ с названием '{self.page['title']}' успешно изменена.",  # noqa: E501
                    self.bot.user.display_name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        logger.info(
            "[modal] - FAQ page changed user=%s guild=%s title=%s",
            interaction.user.id,
            guild.id,
            title,
            description,
        )
