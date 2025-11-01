"""Add a new FAQ page command."""

from typing import TYPE_CHECKING

from discord import app_commands
from discord.interactions import Interaction

from src.nightcore.features.faq._groups import faq as faq_group
from src.nightcore.features.faq.components.modal import NewFAQPageModal

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


@faq_group.command(
    name="add_page",
    description="Добавить новую страницу в FAQ",
)
@app_commands.checks.has_permissions(administrator=True)
async def add_faq_page(
    interaction: Interaction["Nightcore"],
) -> None:
    """Add a new FAQ page to the guild's FAQ configuration."""

    modal = NewFAQPageModal(bot=interaction.client)
    await interaction.response.send_modal(modal)
