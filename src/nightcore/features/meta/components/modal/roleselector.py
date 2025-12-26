"""Modal for bug report submission."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self, cast

from discord import Color, Role
from discord.interactions import Interaction
from discord.ui import Label, Modal, RoleSelect

from src.nightcore.features.meta.components.v2 import RoleSelectorViewV2

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


class RoleSelectorModal(Modal, title="Выбор ролей"):
    select = Label[Self](
        text="Выберите роли для селектора",
        component=RoleSelect[Self](
            placeholder="Максимум - 25 ролей",
            min_values=1,
            max_values=25,
            required=True,
        ),
    )

    def __init__(
        self,
        bot: Nightcore,
        color: Color,
        title: str | None = None,
        description: str | None = None,
        image_url: str | None = None,
    ):
        super().__init__()
        self.bot = bot
        self.color = color
        self._title = title
        self.description = description
        self.image_url = image_url

    async def on_submit(self, interaction: Interaction) -> None:
        """Handles the submission of the ban form modal."""

        await interaction.response.defer(ephemeral=True)

        values = cast(list[Role], self.select.component.values)  # type: ignore

        view = RoleSelectorViewV2(
            bot=self.bot,
            title=self._title,
            color=self.color,
            description=self.description,
            image_url=self.image_url,
            roles=values,
        )

        await interaction.channel.send(view=view)  # type: ignore

        await interaction.followup.send(
            "Ваш отчет об ошибке был отправлен. Спасибо за помощь в улучшении бота!",  # noqa: E501
            ephemeral=True,
        )
