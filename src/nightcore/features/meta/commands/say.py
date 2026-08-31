"""Command to check bot latency."""

from typing import TYPE_CHECKING

import discord
from discord import Attachment, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)


class Say(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

    @app_commands.command(
        name="say", description="Отправить сообщение от бота"
    )  # type: ignore
    @check_required_permissions(PermissionsFlagEnum.BOT_ACCESS)  # type: ignore
    async def say(
        self,
        interaction: Interaction["Nightcore"],
        text: str,
        image: Attachment | None = None,
    ) -> None:
        """Send a message displaying the bot's current latency."""
        if interaction.channel is None:
            await interaction.response.send_message(
                "Канал не найден.", ephemeral=True
            )
            return

        if len(text) > 2000:
            await interaction.response.send_message(
                "Сообщение слишком длинное (максимум 2000 символов).",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        files: list[discord.File] = []
        if image is not None:
            try:
                files = [await image.to_file()]
            except Exception:
                await interaction.followup.send(
                    "Не удалось обработать изображение.",
                    ephemeral=True,
                )
                return

        try:
            await interaction.channel.send(  # type: ignore
                content=text,
                files=files,  # type: ignore
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except discord.Forbidden:
            await interaction.followup.send(
                "Недостаточно прав для отправки сообщения в этот канал.",
                ephemeral=True,
            )
            return
        except discord.HTTPException:
            await interaction.followup.send(
                "Не удалось отправить сообщение.",
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            "Сообщение отправлено!", ephemeral=True
        )


async def setup(bot: "Nightcore"):
    """Setup the Say cog."""
    await bot.add_cog(Say(bot))
