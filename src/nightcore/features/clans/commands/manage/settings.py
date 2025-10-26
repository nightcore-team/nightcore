"""Clan creation command."""

import logging
from typing import TYPE_CHECKING, cast

import discord
from discord import Guild, app_commands
from discord.interactions import Interaction

from src.infra.db.models import GuildClansConfig
from src.infra.db.models._enums import ClanMemberRoleEnum
from src.infra.db.operations import (
    get_clan_by_id,
    get_clan_member,
    get_specified_field,
)
from src.nightcore.components.embed import (
    EntityNotFoundEmbed,
    ErrorEmbed,
    MissingPermissionsEmbed,
    NoOptionsSuppliedEmbed,
    SuccessMoveEmbed,
)
from src.nightcore.exceptions import FieldNotConfiguredError
from src.nightcore.features.clans._groups import manage as manage_clan_group
from src.nightcore.features.clans.utils import clans_autocomplete
from src.nightcore.utils import (
    compare_top_roles,
    has_any_role_from_sequence,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


@manage_clan_group.command(
    name="settings", description="Manage clan settings."
)
@app_commands.describe(
    clan="The clan to manage.",
    new_leader="The new leader of the clan.",
    new_role="The new role associated with the clan.",
)
@app_commands.autocomplete(clan=clans_autocomplete)
async def settings(
    interaction: Interaction["Nightcore"],
    clan: str,
    new_leader: discord.Member | None = None,
    new_role: discord.Role | None = None,
):
    """Manage clan settings."""
    bot = interaction.client
    guild = cast(Guild, interaction.guild)

    if not new_leader and not new_role:
        return await interaction.followup.send(
            embed=NoOptionsSuppliedEmbed(
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    outcome: str | None = None
    clan_name: str | None = None
    changed_leader_to: int | None = None
    changed_role_to: int | None = None

    async with bot.uow.start() as session:
        clans_access_roles_ids = await get_specified_field(
            session,
            guild_id=guild.id,
            config_type=GuildClansConfig,
            field_name="clans_access_roles_ids",
        )

        if not clans_access_roles_ids:
            outcome = "config_missing"
        else:
            if not has_any_role_from_sequence(
                cast(discord.Member, interaction.user), clans_access_roles_ids
            ):
                outcome = "no_permissions"

        if outcome is None:
            clan_entity = await get_clan_by_id(
                session, guild_id=guild.id, clan_id=int(clan)
            )
            if not clan_entity:
                outcome = "clan_not_found"
            else:
                clan_name = clan_entity.name  # DTO field

                # change leader
                if new_leader:
                    clan_member = await get_clan_member(
                        session, guild_id=guild.id, user_id=new_leader.id
                    )

                    if (
                        not clan_member
                        or clan_member.clan_id != clan_entity.id
                    ):
                        outcome = "new_leader_not_in_clan"
                    elif clan_member.role == ClanMemberRoleEnum.LEADER:
                        outcome = "already_leader"
                    else:
                        try:
                            # Make old leader a member
                            clan_entity.leader.role = ClanMemberRoleEnum.MEMBER
                            # Make new one the leader
                            await session.flush()
                            clan_member.role = ClanMemberRoleEnum.LEADER
                            changed_leader_to = new_leader.id
                        except Exception as e:
                            logger.error(
                                "[clans] Error changing clan leader in guild %s: %s",  # noqa: E501
                                guild.id,
                                e,
                            )
                            outcome = "leader_change_internal_error"

                # change clan role
                if outcome is None and new_role:
                    if not compare_top_roles(guild, new_role):
                        outcome = "role_high_than_bot"
                    else:
                        if new_role.permissions.administrator:
                            outcome = "role_has_administrator_permissions"
                        else:
                            try:
                                clan_entity.role_id = new_role.id
                                changed_role_to = new_role.id
                            except Exception as e:
                                logger.error(
                                    "[clans] Error changing clan role in guild %s: %s",  # noqa: E501
                                    guild.id,
                                    e,
                                )
                                outcome = "role_change_internal_error"

    if outcome == "config_missing":
        raise FieldNotConfiguredError("clans access")

    if outcome == "no_permissions":
        return await interaction.response.send_message(
            embed=MissingPermissionsEmbed(
                bot.user.name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "clan_not_found":
        return await interaction.response.send_message(
            embed=EntityNotFoundEmbed(
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
                "clan",
            ),
            ephemeral=True,
        )

    if outcome == "new_leader_not_in_clan":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка назначения лидера",
                f"{new_leader.mention} не состоит в вашем клане.",  # type: ignore[union-attr]
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "already_leader":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка назначения лидера",
                f"{new_leader.mention} уже является лидером клана.",  # type: ignore[union-attr]
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "role_has_administrator_permissions":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка изменения роли клана",
                "Роль клана не может иметь права администратора.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "role_high_than_bot":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка изменения роли клана",
                "Роль клана должна быть ниже верхней роли бота.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "leader_change_internal_error":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка назначения лидера",
                "Произошла ошибка при изменении лидера клана.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "role_change_internal_error":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка изменения роли клана",
                "Произошла ошибка при изменении роли клана.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    summary_lines: list[str] = []
    if changed_leader_to:
        summary_lines.append(
            f"Новый лидер: {new_leader.mention}"  # type: ignore
        )
    if changed_role_to:
        summary_lines.append(f"Роль клана обновлена: <@&{changed_role_to}>")
    details = (
        "\n".join(summary_lines)
        if summary_lines
        else "Настройки клана успешно обновлены."
    )

    return await interaction.response.send_message(
        embed=SuccessMoveEmbed(
            "Настройки клана обновлены",
            details
            if clan_name is None
            else f"Клан: **{clan_name}**\n{details}",
            bot.user.display_name,  # type: ignore
            bot.user.display_avatar.url,  # type: ignore
        ),
        ephemeral=True,
    )
