"""Clan deletion command."""

import asyncio
import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, Member, app_commands
from discord.interactions import Interaction

from src.infra.db.operations import get_clan_by_id, get_specified_field

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.infra.db.models import GuildClansConfig
from src.nightcore.components.embed import (
    ErrorEmbed,
    MissingPermissionsEmbed,
    SuccessMoveEmbed,
)
from src.nightcore.exceptions import FieldNotConfiguredError
from src.nightcore.features.clans._groups import manage as manage_clan_group
from src.nightcore.features.clans.utils import clans_autocomplete
from src.nightcore.utils import (
    ensure_role_exists,
    has_any_role_from_sequence,
    safe_delete_role,
)

logger = logging.getLogger(__name__)


@manage_clan_group.command(
    name="delete", description="Delete an existing clan."
)
@app_commands.describe()
@app_commands.autocomplete(clan=clans_autocomplete)
async def delete(interaction: Interaction["Nightcore"], clan: str):
    """Delete an existing clan."""
    bot = interaction.client
    guild = cast(Guild, interaction.guild)

    member = cast(Member, interaction.user)

    await interaction.response.defer(ephemeral=True, thinking=True)

    # check user permissions
    async with bot.uow.start() as session:
        clans_access_roles_ids = await get_specified_field(
            session,
            guild_id=guild.id,
            config_type=GuildClansConfig,
            field_name="clans_access_roles_ids",
        )
        if not clans_access_roles_ids:
            raise FieldNotConfiguredError("clans access")

        if not has_any_role_from_sequence(member, clans_access_roles_ids):
            await interaction.followup.send(
                embed=MissingPermissionsEmbed(
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                )
            )
            return

        try:
            # get clan
            dbclan = await get_clan_by_id(
                session, guild_id=guild.id, clan_id=int(clan)
            )
            if not dbclan:
                await interaction.followup.send(
                    embed=ErrorEmbed(
                        "Ошибка удаления клана",
                        "Не удалось найти данный клан в базе данных.",  # noqa: RUF001
                        bot.user.display_name,  # type: ignore
                        bot.user.display_avatar.url,  # type: ignore
                    )
                )
                return
            # try to delete
            await session.delete(clan)

        except Exception as e:
            logger.exception(
                "[clans] Failed to delete clan in guild %s: %s", guild.id, e
            )

    role = await ensure_role_exists(guild, dbclan.role_id)  # type: ignore
    if role:
        asyncio.create_task(safe_delete_role(role, "Удаление роли клана"))  # noqa: RUF006

    await interaction.followup.send(
        embed=SuccessMoveEmbed(
            "Удаление клана",
            "Клан был успешно удален вместе с его участниками.",  # noqa: RUF001
            bot.user.display_name,  # type: ignore
            bot.user.display_avatar.url,  # type: ignore
        )
    )

    logger.info("[clans] Clan was successfully deleted in guild %s", guild.id)
