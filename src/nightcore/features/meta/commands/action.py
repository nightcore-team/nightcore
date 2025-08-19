"""Action command for the Nightcore bot."""

import logging

import discord
from discord import app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.nightcore.bot import Nightcore
from src.nightcore.features.meta.utils import (
    ACTION_CHOICES,
    DUO_ACTIONS,
    build_action_embed,
)

logger = logging.getLogger(__name__)


class Action(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @app_commands.command(name="action", description="Perform an action")
    @app_commands.checks.cooldown(
        1, 5.0, key=lambda i: i.user.id
    )  # 1 use every 5 seconds
    @app_commands.choices(action=[*ACTION_CHOICES])
    @app_commands.describe(
        action="Choose an action",
        user="Choose a member for the action",
    )
    async def action(
        self,
        interaction: Interaction,
        action: str,
        user: discord.Member | None = None,
    ):
        """Send a message performing an action."""
        if action in DUO_ACTIONS:
            if user is None:
                await interaction.response.send_message(
                    "Вы должны указать пользователя для этого действия!",
                    ephemeral=True,
                )
                return
            if user.id == interaction.user.id:
                await interaction.response.send_message(
                    "Вы не можете выполнить это действие на себе!",  # noqa: RUF001
                    ephemeral=True,
                )
                return
        else:
            user = None

        embed = build_action_embed(action, interaction.user, user)

        await interaction.response.send_message(embed=embed)


async def setup(bot: Nightcore):
    """Setup the Action cog."""
    await bot.add_cog(Action(bot))
