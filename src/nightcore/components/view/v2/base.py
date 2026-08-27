"""Base handlers for v2 views."""

import logging
from typing import Any

from discord import app_commands
from discord.interactions import Interaction
from discord.ui import Item

from .error import MissingPermissionsViewV2

logger = logging.getLogger(__name__)


class BaseErrorViewV2:
    async def on_error(
        self,
        interaction: Interaction,
        error: Exception,
        item: Item[Any],
    ) -> None:
        """Handle errors for button interactions.

        Handles missing permissions and logs any other error.
        """

        original = getattr(error, "original", error)

        if not isinstance(original, app_commands.MissingPermissions):
            logger.error(
                f"Unknown error in {self.__class__.__name__} component",
                exc_info=error,
            )
            return

        missing_perms: list[str] = getattr(original, "missing_permissions", [])

        _missing_perms = ", ".join(missing_perms)

        if not interaction.response.is_done():
            await interaction.response.send_message(
                view=MissingPermissionsViewV2(
                    "Вам не хватает следующих прав для "
                    f"использования этой команды: {_missing_perms}.",
                ),
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                view=MissingPermissionsViewV2(
                    "Вам не хватает следующих прав для "
                    f"использования этой команды: {missing_perms}.",
                ),
                ephemeral=True,
            )
