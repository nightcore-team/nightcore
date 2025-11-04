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
    name="delete", description="Удалить существующий клан."
)
@app_commands.describe(
    clan="Клан, который вы хотите удалить.",
)
@app_commands.autocomplete(clan=clans_autocomplete)
async def delete(interaction: Interaction["Nightcore"], clan: str):
    """Delete an existing clan."""
    bot = interaction.client
    guild = cast(Guild, interaction.guild)

    member = cast(Member, interaction.user)

    await interaction.response.defer(ephemeral=True, thinking=True)

    # check user permissions
    # Змінні для винесення з context manager
    outcome = ""
    clan_name = ""
    clan_role_id = 0

    async with bot.uow.start() as session:
        clans_access_roles_ids = await get_specified_field(
            session,
            guild_id=guild.id,
            config_type=GuildClansConfig,
            field_name="clans_access_roles_ids",
        )

        if not clans_access_roles_ids:
            outcome = "clans_not_configured"
        elif not has_any_role_from_sequence(member, clans_access_roles_ids):
            outcome = "no_permissions"
        else:
            try:
                dbclan = await get_clan_by_id(
                    session, guild_id=guild.id, clan_id=int(clan)
                )

                if not dbclan:
                    outcome = "clan_not_found"
                else:
                    clan_name = dbclan.name
                    clan_role_id = dbclan.role_id

                    await session.delete(dbclan)
                    await session.flush()

                    outcome = "success"

            except Exception as e:
                logger.exception(
                    "[clans] Failed to delete clan %s in guild %s: %s",
                    clan,
                    guild.id,
                    e,
                )
                outcome = "database_error"

    if outcome == "clans_not_configured":
        raise FieldNotConfiguredError("clans access")

    if outcome == "no_permissions":
        return await interaction.followup.send(
            embed=MissingPermissionsEmbed(
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            )
        )

    if outcome == "clan_not_found":
        return await interaction.followup.send(
            embed=ErrorEmbed(
                "Ошибка удаления клана",
                "Не удалось найти данный клан в базе данных.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            )
        )

    if outcome == "database_error":
        return await interaction.followup.send(
            embed=ErrorEmbed(
                "Ошибка удаления клана",
                "Не удалось удалить клан из-за внутренней ошибки.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            )
        )

    if outcome == "success":
        role = await ensure_role_exists(guild, clan_role_id)
        if role:
            asyncio.create_task(safe_delete_role(role, "Удаление роли клана"))  # noqa: RUF006

        await interaction.followup.send(
            embed=SuccessMoveEmbed(
                "Удаление клана",
                f"Клан **{clan_name}** был успешно удален вместе с его участниками.",  # noqa: E501
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            )
        )

    logger.info(
        "[command] - invoked user=%s guild=%s clan_name=%s deleted_clan=%s",
        interaction.user.id,
        guild.id,
        clan_name,
        clan,
        True,
    )
