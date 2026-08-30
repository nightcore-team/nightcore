"""Modal component for changing a component."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Self

from discord import Interaction, SelectOption, TextStyle
from discord.ui import Label, Modal, Select, TextInput

if TYPE_CHECKING:
    from src.infra.db.models import CustomComponent
    from src.nightcore.bot import Nightcore

from src.nightcore.components.view.v2 import (
    ErrorViewV2,
    NoOptionsSuppliedViewV2,
    SuccessViewV2,
)

# from src.nightcore.utils.content import is_image_url

logger = logging.getLogger(__name__)


class ChangeComponentModal(Modal, title="Изменение компонента"):
    name = TextInput[Self](
        label="Название компонента",
        placeholder="Пример: новости",
        style=TextStyle.short,
        required=False,
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
            required=False,
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

    def __init__(self, bot: Nightcore, component: CustomComponent):
        self.bot = bot
        self.component = component
        super().__init__()

    async def on_submit(self, interaction: Interaction) -> None:
        """Handles the submission of the ban form modal."""

        name = self.name.value or None
        text = self.text.value or None

        component_type: str | None = None
        if self.type.component.values:  # type: ignore
            component_type: str | None = self.type.component.values[0] or None  # type: ignore

        author_text = self.author_text.value or None

        if not any([name, text, component_type, author_text]):  # type: ignore
            await interaction.response.send_message(
                view=NoOptionsSuppliedViewV2()
            )
            return

        changed_fields: list[str] = []
        if name:
            changed_fields.append("name")
        if text:
            changed_fields.append("text")
        if component_type:
            changed_fields.append("type")
        if author_text:
            changed_fields.append("author_text")

        try:
            async with self.bot.uow.start() as session:
                from src.infra.db.operations import get_custom_component_by_id

                locked = await get_custom_component_by_id(
                    session,
                    guild_id=self.component.guild_id,
                    id=self.component.id,
                    for_update=True,
                )
                if locked is None:
                    await interaction.response.send_message(
                        view=ErrorViewV2(
                            "Ошибка изменения компонента",
                            "Компонент не найден.",
                        ),
                        ephemeral=True,
                    )
                    return
                # apply changes to locked row (inside same transaction)
                if name:
                    locked.name = name
                if text:
                    locked.text = text
                if component_type:
                    locked.type = component_type
                if author_text:
                    locked.author_text = author_text
                _ = locked
        except Exception as e:
            logger.error(
                "[compbuilder/change] Failed to change component %s: %s",
                self.component.id,
                e,
            )
            await interaction.response.send_message(
                view=ErrorViewV2(
                    "Ошибка изменения компонента",
                    "Произошла ошибка при изменении компонента.",
                )
            )
            return

        await interaction.response.send_message(
            view=SuccessViewV2(
                "Изменение компонента.",
                f"Компонент успешно изменен. Измененные поля: {', '.join(changed_fields)}",  # noqa: E501
            ),
            ephemeral=True,
        )
