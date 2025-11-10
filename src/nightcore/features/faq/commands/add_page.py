"""Add a new FAQ page command."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild
from discord.interactions import Interaction

from src.infra.db.models.guild import MainGuildConfig
from src.nightcore.features.faq._groups import faq as faq_group
from src.nightcore.features.faq.components.modal import NewFAQPageModal
from src.nightcore.services.config import specified_guild_config

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

logger = logging.getLogger(__name__)


@faq_group.command(  # type: ignore
    name="add_page",
    description="Добавить новую страницу в FAQ",
)
@check_required_permissions(PermissionsFlagEnum.ADMINISTRATOR)
async def add_faq_page(
    interaction: Interaction["Nightcore"],
) -> None:
    """Add a new FAQ page to the guild's FAQ configuration."""

    guild = cast(Guild, interaction.guild)

    async with specified_guild_config(
        interaction.client,
        guild_id=guild.id,
        config_type=MainGuildConfig,
    ) as (_, _):
        pass

    modal = NewFAQPageModal(bot=interaction.client)
    await interaction.response.send_modal(modal)

    logger.info(
        "[command] - invoked user=%s guild=%s",
        interaction.user.id,
        interaction.guild.id,  # type: ignore
    )
