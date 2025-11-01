"""Change FAQ Page Modal Component."""

from typing import TYPE_CHECKING, Self, cast

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

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


class ChangeFAQPageModal(Modal, title="Настроить страницу"):
    page_title = TextInput[Self](
        label="Новый заголовок страницы",
        style=TextStyle.short,
        placeholder="Введите заголовок страницы",
        required=False,
        max_length=100,
    )

    little_description = TextInput[Self](
        label="Новое краткое описание",
        style=TextStyle.paragraph,
        placeholder="Введите краткое описание страницы",
        required=False,
        max_length=200,
    )

    content = TextInput[Self](
        label="Новое содержание страницы",
        style=TextStyle.paragraph,
        placeholder="Введите содержание страницы",
        required=False,
        max_length=3000,
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
                    elif description:
                        faq_page["description"] = description
                    elif content:
                        faq_page["content"] = content
                    else:
                        outcome = "nothing_to_change"
                    break

            if not outcome:
                attributes.flag_modified(guild_config, "faq")
                outcome = "success"

        if outcome == "nothing_to_change":
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
                    f"Страница FAQ с названием '{self.page['title']}' успешно изменена.",  # noqa: E501, RUF001
                    self.bot.user.display_name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )
            return
