"""Modal for bug report submission."""

import asyncio
from typing import TYPE_CHECKING, cast

from discord import Attachment, Guild, Member, TextStyle
from discord.interactions import Interaction
from discord.ui import FileUpload, Label, Modal, TextInput

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.config.config import config as project_config
from src.nightcore.components.embed import ErrorEmbed, ValidationErrorEmbed
from src.nightcore.features.meta.components.v2.view.bugreport import (
    BugReportViewV2,
)


class BugReportModal(Modal, title="Отправить отчёт об ошибке"):
    long = TextInput["BugReportModal"](
        label="Полное описание проблемы",
        style=TextStyle.long,
        placeholder="Пример: При использовании команды /profile данные не загружаются корректно.",  # noqa: E501
        required=True,
        max_length=500,
    )

    screenshot = Label["BugReportModal"](
        text="Прикрепите скриншот с ошибкой",
        component=FileUpload(required=False, min_values=1, max_values=1),
    )

    def __init__(
        self,
        bot: "Nightcore",
    ):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: Interaction) -> None:
        """Handles the submission of the ban form modal."""
        guild = cast(Guild, interaction.guild)
        user = cast(Member, interaction.user)

        await interaction.response.defer()

        attachment: Attachment | None = None  # type: ignore
        if self.screenshot.component.values:  # type: ignore
            attachment: Attachment = self.screenshot.component.values[0]  # type: ignore
            if not attachment or not attachment.filename.lower().endswith(  # type: ignore
                (  # type: ignore
                    ".png",
                    ".jpg",
                    ".jpeg",
                    ".webp",
                )
            ):
                return await interaction.followup.send(
                    embed=ValidationErrorEmbed(
                        "Пожалуйста отправьте валидный файл изображения (png, jpg, jpeg, webp).",  # noqa: E501
                        self.bot.user.name,  # type: ignore
                        self.bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )

        view = BugReportViewV2(
            bot=self.bot,
            guild_id=guild.id,
            user_id=user.id,
            long_desc=self.long.value,
            screenshot=attachment,  # type: ignore
        )

        channel = self.bot.get_channel(
            project_config.bot.BUG_REPORT_CHANNEL_ID
        )
        if not channel:
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Ошибка отправки отчёта об ошибке.",
                    "Канал для  отправки отчётов об ошибках не найден.",
                    self.bot.user.display_name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                )
            )

        asyncio.create_task(channel.send(view=view))  # type: ignore

        await interaction.followup.send(
            "Ваш отчет об ошибке был отправлен. Спасибо за помощь в улучшении бота!",  # noqa: E501
            ephemeral=True,
        )
