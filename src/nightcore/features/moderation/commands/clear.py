"""Clear command for the Nightcore bot."""

import logging
from datetime import timezone
from typing import cast

import discord
from discord import Guild, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.db.operations import get_moderation_access_roles
from src.nightcore.bot import Nightcore
from src.nightcore.components import (
    MissingPermissionsEmbed,
    SuccessMoveEmbed,
    ValidationErrorEmbed,
)
from src.nightcore.features.moderation.events import MessageClearEventData

logger = logging.getLogger(__name__)


class Clear(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @app_commands.command(
        name="clear", description="Clear messages from a channel"
    )
    @app_commands.describe(number="The number of messages to clear (1-20)")
    async def clear(
        self,
        interaction: Interaction,
        number: int,
    ):
        """Clear messages from a channel."""
        guild = cast(Guild, interaction.guild)

        async with self.bot.uow.start() as uow:
            moderation_access_roles = await get_moderation_access_roles(
                cast(AsyncSession, uow.session), guild_id=guild.id
            )
        has_moder_role = any(
            interaction.user.get_role(role_id)  # type: ignore
            for role_id in moderation_access_roles
        )
        if not has_moder_role:
            await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )
            return

        if not guild.me.guild_permissions.manage_messages:
            await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                    "I do not have permission to manage messages.",
                ),
                ephemeral=True,
            )
            return

        await interaction.response.defer(thinking=True, ephemeral=True)

        if number < 1 or number > 20:
            await interaction.followup.send(
                embed=ValidationErrorEmbed(
                    "Please provide a number between 1 and 20.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )
            return

        try:
            channel = interaction.channel
            if issubclass(channel.__class__, discord.abc.Messageable):
                await channel.purge(limit=number)  # type: ignore
            else:
                await interaction.followup.send(
                    embed=ValidationErrorEmbed(
                        "Cannot clear messages in this type of channel.",
                        self.bot.user.name,  # type: ignore
                        self.bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )
                return
        except Exception as e:
            logger.exception("[command] - Failed to clear messages: %s", e)

        try:
            self.bot.dispatch(
                "message_clear",
                data=MessageClearEventData(
                    moderator=interaction.user,  # type: ignore
                    category=self.__class__.__name__.lower(),
                    channel_cleared_id=channel.id,  # type: ignore
                    amount=number,
                    created_at=discord.utils.utcnow().astimezone(
                        tz=timezone.utc
                    ),
                ),
            )
        except Exception as e:
            logger.exception(
                "[event] - Failed to dispatch user_punish event: %s", e
            )

        await interaction.followup.send(
            embed=SuccessMoveEmbed(
                "Messages Cleared",
                f"Successfully cleared {number} messages from the channel.",
                self.bot.user.name,  # type: ignore
                self.bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )


async def setup(bot: Nightcore):
    """Setup the Clear cog."""
    await bot.add_cog(Clear(bot))
