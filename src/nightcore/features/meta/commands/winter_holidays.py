"""Command to check days until winter holidays (NewYear and Christmas)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from discord import app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)


class WinterHolidays(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @app_commands.command(
        name="winter_holidays",
        description="Новогодние и рождественские праздники",
    )  # type: ignore
    @app_commands.describe(
        calendar="Календарь, по которому считать дни до праздников (Григорианский или Юлианский)",  # noqa: E501
        timezone="Часовой пояс для расчёта дат праздников",
    )
    @app_commands.choices(
        calendar=[
            app_commands.Choice(name="Григорианский", value="gregorian"),
            app_commands.Choice(name="Юлианский", value="julian"),
        ]
    )
    @check_required_permissions(PermissionsFlagEnum.NONE)  # type: ignore
    async def winter_holidays(
        self,
        interaction: Interaction[Nightcore],
        calendar: str = "gregorian",
        timezone: str | None = None,
    ):
        """Send a message displaying the bot's current latency."""

        ...


async def setup(bot: Nightcore):
    """Setup the WinterHolidays cog."""
    await bot.add_cog(WinterHolidays(bot))
