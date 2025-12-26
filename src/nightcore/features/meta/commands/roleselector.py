"""Command to send custom role selector."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from discord import Color, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.components.embed import ErrorEmbed
from src.nightcore.features.meta.components.modal import RoleSelectorModal
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

logger = logging.getLogger(__name__)


class RoleSelector(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @app_commands.command(
        name="role_selector",
        description="Отправить селект компонент с указанными ролями",
    )  # type: ignore
    @app_commands.describe(
        title="Заголовок селектора ролей (необязательно)",
        description="Описание селектора ролей (необязательно)",
        image_url="URL изображения для селектора ролей (необязательно)",
        color="Цвет акцента для селектора ролей в формате HEX (необязательно)",
    )
    @check_required_permissions(PermissionsFlagEnum.HEAD_MODERATION_ACCESS)  # type: ignore
    async def ping(
        self,
        interaction: Interaction[Nightcore],
        title: str | None = None,
        description: str | None = None,
        image_url: str | None = None,
        color: str | None = None,
    ):
        """Send a role selector modal."""

        c = Color.default()
        try:
            if color:
                c = Color.from_str(color)
        except Exception as e:
            logger.error("[compbuilder/preview] Invalid color provided: %s", e)
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка предпросмотра компонента",
                    "Указанный цвет недействителен. Пожалуйста, используйте правильный HEX формат.",  # noqa: E501
                    self.bot.user.display_name,  # type: ignore
                    self.bot.user.avatar.url,  # type: ignore
                )
            )

        await interaction.response.send_modal(
            RoleSelectorModal(
                bot=self.bot,
                color=c,
                title=title,
                description=description,
                image_url=image_url,
            )
        )


async def setup(bot: Nightcore):
    """Setup the RoleSelector cog."""
    await bot.add_cog(RoleSelector(bot))
