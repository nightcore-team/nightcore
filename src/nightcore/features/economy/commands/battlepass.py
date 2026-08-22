"""Command to check battlepass."""

from __future__ import annotations

from typing import TYPE_CHECKING

from discord import app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.nightcore.services.battlepass import send_battlepass_claim_view
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


class Battlepass(Cog):
    """Battlepass commands."""

    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @app_commands.command(  # type: ignore
        name="battlepass",
        description="Взаимодействие с баттлпасом сервера.",
    )
    @app_commands.guild_only()
    @check_required_permissions(PermissionsFlagEnum.NONE)  # type: ignore
    async def claim(self, interaction: Interaction[Nightcore]):
        """Claim your battlepass rewards."""

        await send_battlepass_claim_view(self.bot, interaction)


async def setup(bot: Nightcore) -> None:
    """Setup the Battlepass cog."""
    await bot.add_cog(Battlepass(bot))
