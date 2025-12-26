"""Modal for bug report submission."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self, cast

from discord import Color, Guild, Member, Role
from discord.interactions import Interaction
from discord.ui import Label, Modal, RoleSelect

from src.nightcore.components.embed import ErrorEmbed
from src.nightcore.features.meta.components.v2 import RoleSelectorViewV2
from src.nightcore.utils import compare_top_roles

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

        guild = cast(Guild, interaction.guild)
        member = cast(Member, interaction.user)

        values = cast(list[Role], self.select.component.values)  # type: ignore

        for role in values:
            if role.permissions.administrator:
                await interaction.followup.send(
                    embed=ErrorEmbed(
                        "Ошибка создания селектора ролей",
                        f"Роль {role.mention} имеет права администратора и не может быть добавлена в селектор ролей.",  # noqa: E501
                        self.bot.user.display_name,  # type: ignore
                        self.bot.user.avatar.url,  # type: ignore
                    )
                )

            if not compare_top_roles(
                guild,
                member,
            ):
                await interaction.followup.send(
                    embed=ErrorEmbed(
                        "Ошибка создания селектора ролей",
                        f"Роль {role.mention} выше роли бота, поэтому вы не можете добавить её в селектор ролей.",  # noqa: E501
                        self.bot.user.display_name,  # type: ignore
                        self.bot.user.avatar.url,  # type: ignore
                    )
                )
                return

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
            "Ваш селектор ролей был отправлен.",
            ephemeral=True,
        )
