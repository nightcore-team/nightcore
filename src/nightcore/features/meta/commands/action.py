"""Action command for the Nightcore bot."""

import logging
from typing import ClassVar

import discord
from discord import app_commands
from discord.ext.commands import Cog
from discord.interactions import Interaction, InteractionCallbackResponse

from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


class Action(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    actions: ClassVar[list[str]] = ["kiss", "hug"]

    @app_commands.command(name="action", description="Perform an action")
    @app_commands.checks.cooldown(
        1, 5.0, key=lambda i: i.user.id
    )  # 1 use every 5 seconds
    @app_commands.choices(
        action=[
            app_commands.Choice(name=action, value=action)
            for action in actions
        ]
    )
    async def action(
        self,
        interaction: Interaction,
        action: str,
        member: discord.Member,
    ) -> InteractionCallbackResponse:
        """Send a message performing an action.

        Args:
            interaction : discord.Interaction
                The interaction that triggered the command.
            action : str
                Выберите действие, которое вы хотите выполнить.
            member : discord.Member | None
                Выберите пользователя, к которому применить действие.
        """
        if member == interaction.user:
            logger.info(
                "action.command blocked self-target user=%s guild=%s action=%s",
                interaction.user.id,
                interaction.guild.id if interaction.guild else None,
                action,
            )
            return await interaction.response.send_message(
                "Вы не можете применить действие к себе."  # noqa: RUF001
            )

        logger.info(
            "action.command invoked user=%s guild=%s action=%s target=%s",
            interaction.user.id,
            interaction.guild.id if interaction.guild else None,
            action,
            member.id,
        )
        return await interaction.response.send_message(
            f"вы выбрали {action} для {member.display_name}"
        )


async def setup(bot: Nightcore):
    """Setup the Action cog."""
    await bot.add_cog(Action(bot))
