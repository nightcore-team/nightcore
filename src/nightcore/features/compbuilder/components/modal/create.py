"""Modal component for creating a component."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Self, cast

from discord import Guild, Interaction, SelectOption, TextStyle
from discord.ui import Label, Modal, Select, TextInput

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.infra.db.models import CustomComponent
from src.nightcore.components.embed import ErrorEmbed, SuccessMoveEmbed

# from src.nightcore.utils.content import is_image_url

logger = logging.getLogger(__name__)


class CreateComponentModal(Modal, title="Создание компонента"):
    name = TextInput[Self](
        label="Название компонента",
        placeholder="Пример: новости",
        style=TextStyle.short,
        required=True,
        max_length=50,
    )

    type = Label[Self](
        text="Выберите тип компонента",
        component=Select[Self](
            placeholder="Embed/V2 Component",
            options=[
                SelectOption(label="Embed", value="embed"),
                SelectOption(label="V2 Component", value="v2_component"),
            ],
            required=True,
        ),
    )

    text = TextInput[Self](
        label="Текст компонента",
        placeholder="Пример: Добро пожаловать на сервер!",
        required=False,
        style=TextStyle.long,
        max_length=2800,
    )

    author_text = TextInput[Self](
        label="Авторство",
        placeholder="Пример: Новости от Администрации",
        required=False,
        style=TextStyle.short,
        max_length=100,
    )

    def __init__(self, bot: Nightcore):
        self.bot = bot
        super().__init__()

    async def on_submit(self, interaction: Interaction) -> None:
        """Handles the submission of the ban form modal."""

        guild = cast(Guild, interaction.guild)

        name = self.name.value
        text = self.text.value
        component_type: str = self.type.component.values[0]  # type: ignore
        author_text = self.author_text.value or None

        outcome = ""

        async with self.bot.uow.start() as session:
            component = CustomComponent(
                guild_id=guild.id,
                moderator_id=interaction.user.id,
                type=component_type,
                name=name,
                text=text,
                author_text=author_text,
                # image_url=image_url,
            )

            session.add(component)

            try:
                await session.flush()
                outcome = "success"

            except Exception as e:
                logger.error(
                    "[compbuilder/create] Failed to create component: %s", e
                )
                outcome = "failure"

        if outcome == "failure":
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка создания компонента",
                    "Произошла ошибка при создании компонента. ",
                    self.bot.user.display_name,  # type: ignore
                    self.bot.user.avatar.url,  # type: ignore
                )
            )

        if outcome == "success":
            return await interaction.response.send_message(
                embed=SuccessMoveEmbed(
                    "Компонент создан",
                    f"Компонент **{name}** успешно создан.",
                    self.bot.user.display_name,  # type: ignore
                    self.bot.user.avatar.url,  # type: ignore
                )
            )
