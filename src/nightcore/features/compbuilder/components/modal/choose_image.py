"""Modal component for creating a component."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Self

from discord import (
    Attachment,
    Color,
    Embed,
    Interaction,
    Role,
    TextChannel,
    TextStyle,
)
from discord.ui import FileUpload, Label, LayoutView, Modal, TextInput

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.infra.db.models._enums import ComponentTypeEnum
from src.nightcore.components.embed import ErrorEmbed
from src.nightcore.features.compbuilder.components.embed import build_embed
from src.nightcore.features.compbuilder.components.v2 import (
    build_view as build_v2_component,
)
from src.nightcore.utils.content import is_image_url

logger = logging.getLogger(__name__)


class ChooseImageModal(Modal, title="Выберите изображение"):
    image_url = TextInput[Self](
        label="Ссылка на изображение",
        placeholder="Пример: https://example.com/image.png",
        required=False,
        style=TextStyle.short,
        max_length=300,
    )

    image = Label[Self](
        text="Изображение с устройства",
        component=FileUpload(required=False),
    )

    def __init__(
        self,
        bot: Nightcore,
        type: ComponentTypeEnum,
        name: str,
        text: str,
        channel: TextChannel | None = None,
        color: Color | None = None,
        author_text: str | None = None,
        role: Role | None = None,
    ):
        self.bot = bot
        super().__init__()

        self.type = type
        self.name = name
        self.text = text
        self.color = color
        self.author_text = author_text
        self.role = role
        self.channel = channel

    async def on_submit(self, interaction: Interaction) -> None:
        """Handles the submission of the ban form modal."""

        image_source: str | Attachment | None = None

        if self.image_url.value:
            if not is_image_url(self.image_url.value):
                return await interaction.response.send_message(
                    embed=ErrorEmbed(
                        "Ошибка компонента",
                        "Указанный URL изображения недействителен.",
                        self.bot.user.display_name,  # type: ignore
                        self.bot.user.avatar.url,  # type: ignore
                    )
                )
            image_source = self.image_url.value

        if not image_source:
            if not self.image.component.values:  # type: ignore
                image_source = None
            else:
                attachment: Attachment | None = self.image.component.values[0]  # type: ignore
                if attachment and attachment.filename.lower().endswith(  # type: ignore
                    (".png", ".jpg", ".jpeg", ".webp")
                ):
                    image_source = attachment  # type: ignore
                else:
                    return await interaction.response.send_message(
                        embed=ErrorEmbed(
                            "Ошибка компонента",
                            "Пожалуйста отправьте валидный файл изображения (png, jpg, jpeg, webp).",  # noqa: E501
                            self.bot.user.display_name,  # type: ignore
                            self.bot.user.avatar.url,  # type: ignore
                        ),
                        ephemeral=True,
                    )

        component: Embed | LayoutView | None = None

        match self.type:
            case ComponentTypeEnum.EMBED:
                component = build_embed(
                    name=self.name,
                    text=self.text,
                    color=self.color,
                    author_text=self.author_text,
                    image=image_source,  # type: ignore
                )
            case ComponentTypeEnum.V2_COMPONENT:
                component = build_v2_component(
                    name=self.name,
                    text=self.text,
                    color=self.color,
                    author_text=self.author_text,
                    image=image_source,  # type: ignore
                )
            case _:
                logger.error(
                    "[compbuilder/choose_image] Unsupported component type: %s",  # noqa: E501
                    self.type,
                )
                return await interaction.response.send_message(
                    embed=ErrorEmbed(
                        "Ошибка компонента",
                        "Указанный тип компонента не поддерживается.",
                        self.bot.user.display_name,  # type: ignore
                        self.bot.user.avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )

        if isinstance(component, Embed):
            content = self.role.mention if self.role and self.channel else None

            if self.channel:
                await self.channel.send(content=content, embed=component)
            else:
                await interaction.response.send_message(
                    content=content,
                    embed=component,
                    ephemeral=True,
                )
        else:
            if self.channel is None:
                await interaction.response.send_message(
                    view=component,
                    ephemeral=True,
                )
            else:
                if self.role:
                    await self.channel.send(self.role.mention)  # type: ignore

                await self.channel.send(view=component)  # type: ignore

        await interaction.response.send_message(
            content="Компонент отправлен.", ephemeral=True
        )
