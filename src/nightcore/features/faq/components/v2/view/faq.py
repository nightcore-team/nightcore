"""FAQ view component v2."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Self, cast

from discord import ButtonStyle, Color, Guild, MediaGalleryItem
from discord.interactions import Interaction
from discord.ui import (
    Button,
    Container,
    LayoutView,
    MediaGallery,
    Section,
    Separator,
    TextDisplay,
)

from src.infra.db.models import MainGuildConfig
from src.infra.db.models._annot import FAQPageAnnot
from src.nightcore.components.embed import ErrorEmbed
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils import discord_ts

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


class FAQViewV2(LayoutView):
    def __init__(
        self,
        bot: "Nightcore",
        text: str | None = None,
        image_url: str | None = None,
        faq_pages: list[FAQPageAnnot] | None = None,
        _build: bool = False,
    ) -> None:
        super().__init__(timeout=None)

        self.bot = bot
        self.faq_pages = faq_pages
        self.text = text
        self.image_url = image_url

        if _build:
            self.make_component()

    def make_component(self) -> Self:
        """Build the FAQ view component."""
        self.clear_items()

        container = Container[Self](accent_color=Color.blurple())

        container.add_item(
            TextDisplay[Self](
                "## <:heartt:1434173700793434223> Часто задаваемые вопросы (FAQ)"  # noqa: E501
            )
        )
        container.add_item(Separator[Self]())

        # introductory text
        if self.text:
            container.add_item(TextDisplay[Self](f"{self.text}"))
            container.add_item(Separator())

        # sections for each FAQ page
        if self.faq_pages:
            for page in self.faq_pages:
                faqbutton = Button[Self](
                    label="Подробнее",
                    style=ButtonStyle.secondary,
                    custom_id=f"faq_page:{page['title']}",
                    row=2,
                )
                faqbutton.callback = self.button_callback
                container.add_item(
                    TextDisplay[Self](f"### {page['title']}"),
                )
                container.add_item(
                    Section[Self](
                        TextDisplay[Self](f"> {page['description']}"),
                        accessory=faqbutton,
                    )
                )
                container.add_item(Separator[Self]())
        else:
            container.add_item(
                TextDisplay[Self]("В FAQ этого сервера нет страниц.")  # noqa: RUF001
            )
            container.add_item(Separator[Self]())

        # media gallery for image
        if self.image_url:
            container.add_item(
                MediaGallery[Self](MediaGalleryItem(self.image_url))
            )
            container.add_item(Separator[Self]())

        now = datetime.now(timezone.utc)
        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {self.bot.user.name} in {discord_ts(now)}\n"  # type: ignore
            )
        )

        self.add_item(container)

        return self

    async def button_callback(self, interaction: Interaction["Nightcore"]):
        """Handle FAQ page button clicks and return page content."""

        page_title = interaction.data["custom_id"].split("faq_page:")[1]  # type: ignore
        guild = cast(Guild, interaction.guild)

        faq_page: FAQPageAnnot | None = None
        outcome = ""
        async with specified_guild_config(
            self.bot, guild.id, MainGuildConfig
        ) as (guild_config, _):
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
                    f"Страница с названием '{page_title}' не найдена в FAQ этого сервера.",  # noqa: E501, RUF001
                    self.bot.user.display_name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )
            return

        if outcome == "success" and faq_page:
            await interaction.response.send_message(
                view=FAQPageViewV2(self.bot, faq_page), ephemeral=True
            )


async def handle_faq_button_callback(
    interaction: Interaction["Nightcore"], page_title: str
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
                f"Страница с названием '{page_title}' не найдена в FAQ этого сервера.",  # noqa: E501, RUF001
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )
        return

    if outcome == "success" and faq_page:
        await interaction.response.send_message(
            view=FAQPageViewV2(bot, faq_page), ephemeral=True
        )


class FAQPageViewV2(LayoutView):
    def __init__(self, bot: "Nightcore", page: FAQPageAnnot) -> None:
        super().__init__(timeout=10)

        container = Container[Self](accent_color=Color.blurple())

        container.add_item(TextDisplay[Self](f"## {page['title']}"))
        container.add_item(Separator[Self]())

        container.add_item(TextDisplay[Self](f"{page['content']}"))
        container.add_item(Separator[Self]())

        now = datetime.now(timezone.utc)
        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {bot.user.name} in {discord_ts(now)}\n"  # type: ignore
            )
        )

        self.add_item(container)
