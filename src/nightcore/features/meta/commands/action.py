"""Command to perform actions with users."""

import logging

from discord import Member, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.nightcore.bot import Nightcore
from src.nightcore.components.embed import (
    ValidationErrorEmbed,
)
from src.nightcore.features.meta.utils import (
    ACTION_CHOICES,
    DUO_ACTIONS,
    build_action_embed,
)
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

logger = logging.getLogger(__name__)


class Action(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @app_commands.command(  # type: ignore
        name="action",
        description="Сделать действие с пользователем",
    )
    @app_commands.checks.cooldown(
        1, 5.0, key=lambda i: i.user.id
    )  # 1 use every 5 seconds
    @app_commands.choices(action=[*ACTION_CHOICES])
    @app_commands.describe(
        action="Выберите действие",
        user="Выберите пользователя для действия",
    )
    @app_commands.guild_only()
    @check_required_permissions(PermissionsFlagEnum.NONE)  # type: ignore
    async def action(
        self, interaction: Interaction, action: str, user: Member | None = None
    ):
        """Send a message performing an action."""
        # If the action requires a target user, validate user first
        if action in DUO_ACTIONS:
            if user is None:
                await interaction.response.send_message(
                    embed=ValidationErrorEmbed(
                        "Вы должны указать пользователя для этого действия!",
                        self.bot.user.name,  # type: ignore
                        self.bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )
                return

            # Prevent acting on yourself
            if user.id == interaction.user.id:
                await interaction.response.send_message(
                    embed=ValidationErrorEmbed(
                        "Вы не можете выполнить это действие на себе.",
                        self.bot.user.name,  # type: ignore
                        self.bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )
                return

        else:
            user = None

        embed = build_action_embed(action, interaction.user, user)
        await interaction.response.send_message(embed=embed)

        logger.info(
            "[command] - invoked user=%s guild=%s target=%s",
            interaction.user.id,
            interaction.guild.id if interaction.guild else None,
            user.id if user else None,
        )


async def setup(bot: Nightcore):
    """Setup the Action cog."""
    await bot.add_cog(Action(bot))
