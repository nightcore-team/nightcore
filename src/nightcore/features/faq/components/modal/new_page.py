"""
FAQ New Page Modal Component.

Used for creating new FAQ pages in guilds.
"""

import logging
from typing import TYPE_CHECKING, Self, cast

from discord import Guild, TextStyle
from discord.interactions import Interaction
from discord.ui import Modal, TextInput
from sqlalchemy.orm import attributes

from src.infra.db.models import MainGuildConfig
from src.nightcore.components.embed import ErrorEmbed, SuccessMoveEmbed
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils.content import is_image_url

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


class NewFAQPageModal(Modal, title="Настроить страницу"):
    page_title = TextInput[Self](
        label="Заголовок страницы",
        style=TextStyle.short,
        placeholder="Введите заголовок страницы",
        required=True,
        max_length=80,
    )

    little_description = TextInput[Self](
        label="Краткое описание",
        style=TextStyle.paragraph,
        placeholder="Введите краткое описание страницы",
        required=True,
        max_length=200,
    )

    content = TextInput[Self](
        label="Содержание страницы",
        style=TextStyle.paragraph,
        placeholder="Введите содержание страницы",
        required=True,
        max_length=3000,
    )

    image_url = TextInput[Self](
        label="Ссылка на изображение",
        placeholder="Пример: https://example.com/image.png",
        required=False,
        style=TextStyle.short,
        max_length=300,
    )

    def __init__(self, bot: "Nightcore") -> None:
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: Interaction) -> None:
        """Handle the submission of the FAQ page modal."""

        guild = cast(Guild, interaction.guild)

        title = self.page_title.value
        description = self.little_description.value
        content = self.content.value
        image_url = self.image_url.value or None

        if image_url and not is_image_url(image_url):
            image_url = None

        outcome = ""
        async with specified_guild_config(
            self.bot, guild.id, MainGuildConfig
        ) as (
            guild_config,
            _,
        ):
            for page in guild_config.faq:
                if page["title"] == title:
                    outcome = "title_already_exists"
                    break

                if page["description"] == description:
                    outcome = "description_already_exists"
                    break

            if not outcome:
                guild_config.faq.append(
                    {
                        "title": title,
                        "description": description,
                        "content": content,
                        "image_url": image_url,
                    }
                )

                attributes.flag_modified(guild_config, "faq")

                outcome = "success"

        if outcome == "title_already_exists":
            await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка создания страницы FAQ",
                    f"Страница с заголовком '{title}' уже существует.",
                    self.bot.user.display_name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )
            return

        if outcome == "description_already_exists":
            await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка создания страницы FAQ",
                    "Страница с таким описанием уже существует.",
                    self.bot.user.display_name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )
            return

        if outcome == "success":
            await interaction.response.send_message(
                embed=SuccessMoveEmbed(
                    "Страница FAQ создана",
                    f"Страница с заголовком '{title}' успешно создана.",
                    self.bot.user.display_name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        logger.info(
            "[modal] - FAQ page created user=%s guild=%s title=%s",
            interaction.user.id,
            guild.id,
            title,
        )
        return
