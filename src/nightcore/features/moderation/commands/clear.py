"""Command to clear messages in text channel."""

import logging
from datetime import UTC
from typing import TYPE_CHECKING, cast

import discord
from discord import Guild, User, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.nightcore.components.embed import (
    ErrorEmbed,
    MissingPermissionsEmbed,
    SuccessMoveEmbed,
)
from src.nightcore.features.moderation.events import MessageClearEventData

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

logger = logging.getLogger(__name__)


class Clear(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

    @app_commands.command(  # type: ignore
        name="clear", description="Очистить сообщения в канале"
    )
    @app_commands.describe(
        amount="Количество сообщений для очистки (1-100)",
        user="Пользователь, чьи сообщения нужно очистить (необязательно)",
    )
    @app_commands.guild_only()
    @check_required_permissions(PermissionsFlagEnum.MODERATION_ACCESS)  # type: ignore
    async def clear(
        self,
        interaction: Interaction,
        amount: app_commands.Range[int, 1, 100],
        user: User | None = None,
    ):
        """Clear messages from a channel."""
        guild = cast(Guild, interaction.guild)

        if not guild.me.guild_permissions.manage_messages:
            return await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                    "У меня нет разрешения на управление сообщениями.",
                ),
                ephemeral=True,
            )

        await interaction.response.defer(thinking=True, ephemeral=True)

        channel = interaction.channel

        try:
            self.bot.dispatch(
                "message_clear",
                data=MessageClearEventData(
                    moderator=interaction.user,  # type: ignore
                    category=self.__class__.__name__.lower(),
                    channel_cleared_id=channel.id,  # type: ignore
                    amount=amount,
                    created_at=discord.utils.utcnow().astimezone(tz=UTC),
                ),
            )
        except Exception as e:
            logger.exception(
                "[event] - Failed to dispatch user_punish event: %s", e
            )
            return

        try:
            await channel.purge(  # type: ignore
                limit=amount,
                check=lambda m: m.author == user if user else True,  # type: ignore
            )
        except Exception as e:
            logger.exception("[command] - Failed to clear messages: %s", e)
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Ошибка очистки сообщений",
                    "Не удалось очистить сообщения в текущем канале.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        await interaction.followup.send(
            embed=SuccessMoveEmbed(
                "Сообщения очищены",
                f"Успешно очищено {amount} сообщений из канала {'от ' + user.mention if user else ''}",  # noqa: E501
                self.bot.user.name,  # type: ignore
                self.bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )
        logger.info(
            "[command] - invoked user=%s guild=%s channel=%s cleared_messages=%s",  # noqa: E501
            interaction.user.id,
            guild.id,
            channel.id,  # type: ignore
            amount,
        )


async def setup(bot: "Nightcore"):
    """Setup the Clear cog."""
    await bot.add_cog(Clear(bot))
