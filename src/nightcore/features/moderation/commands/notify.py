"""Command to notify a user about a rule violation."""

import logging
from typing import TYPE_CHECKING

from discord import Member, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.nightcore.features.moderation.utils.transformers import (
    StringToRuleTransformer,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.components.embed import (
    ValidationErrorEmbed,
)
from src.nightcore.features.moderation.components.v2 import PrepareNotifyViewV2
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)
from src.nightcore.utils.time_utils import calculate_end_time, parse_duration

logger = logging.getLogger(__name__)


class Notify(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

    @app_commands.command(  # type: ignore
        name="notify", description="Отправить оповещение пользователю"
    )
    @app_commands.guild_only()
    @app_commands.describe(
        user="Пользователь для оповещения",
        duration="Длительность оповещения",
        reason="Причина оповещения (номер правила или текст)",
    )
    @check_required_permissions(PermissionsFlagEnum.MODERATION_ACCESS)  # type: ignore
    async def notify(
        self,
        interaction: Interaction["Nightcore"],
        user: Member,
        duration: str,
        reason: app_commands.Transform[
            app_commands.Range[str, 1, 1000], StringToRuleTransformer
        ],
    ):
        """Sends a notification to a user."""

        member = user

        parsed_duration = parse_duration(duration)

        if not parsed_duration:
            return await interaction.response.send_message(
                embed=ValidationErrorEmbed(
                    "Неверная продолжительность. Используйте s/m/h/d (например, 1h, 1d, 7d).",  # noqa: E501
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        end_time = calculate_end_time(parsed_duration)

        await interaction.response.send_message(
            view=PrepareNotifyViewV2(
                bot=self.bot,
                user_id=member.id,
                end_time=end_time,
                content=reason,
            ),
            ephemeral=True,
        )


async def setup(bot: "Nightcore") -> None:
    """Setup the Notify cog."""
    await bot.add_cog(Notify(bot))
