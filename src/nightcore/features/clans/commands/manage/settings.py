"""Command to manage clan settings."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, Member, Role, app_commands
from discord.interactions import Interaction

from src.infra.db.models._enums import (
    ChannelType,
    ClanManageActionEnum,
    ClanMemberRoleEnum,
)
from src.infra.db.models.guild import GuildLoggingConfig
from src.infra.db.operations import (
    get_clan_by_id,
    get_clan_member,
)
from src.nightcore.components.embed import (
    EntityNotFoundEmbed,
    ErrorEmbed,
    NoOptionsSuppliedEmbed,
    SuccessMoveEmbed,
)
from src.nightcore.features.clans._groups import manage as manage_clan_group
from src.nightcore.features.clans.utils import clans_autocomplete
from src.nightcore.utils import (
    compare_top_roles,
)
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


@manage_clan_group.command(  # type: ignore
    name="settings", description="Управление настройками клана."
)
@app_commands.describe(
    clan="Клан, настройки которого вы хотите изменить.",
    new_leader="Новый лидер клана.",
    new_role="Новая роль, связанная с кланом.",
)
@app_commands.autocomplete(clan=clans_autocomplete)
@check_required_permissions(PermissionsFlagEnum.CLANS_ACCESS)
async def settings(
    interaction: Interaction["Nightcore"],
    clan: str,
    new_leader: Member | None = None,
    new_role: Role | None = None,
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

    async with bot.uow.start() as session:
        clans_logging_channel = await get_specified_channel(
            session,
            guild_id=guild.id,
            config_type=GuildLoggingConfig,
            channel_type=ChannelType.LOGGING_CLANS,
        )

    actions: list[ClanManageAction] = []

    if new_leader is not None:
        clan_change_leader_action = ClanManageAction(
            type=ClanManageActionEnum.CHANGE_LEADER,
            before=f"<@{clan_entity.leader.id}>",  # type: ignore The clan will always exist here because of the checks on lines 86 and 139
            after=new_leader.mention,
        )

        actions.append(clan_change_leader_action)

    if new_role is not None and old_role_id is not None:
        clan_change_role_action = ClanManageAction(
            type=ClanManageActionEnum.CHANGE_ROLE,
            before=f"<@&{old_role_id}>",
            after=clan_entity.role_id,  # type: ignore The clan will always exist here because of the checks on lines 86 and 139
        )

        actions.append(clan_change_role_action)

    dto = ClanManageNotifyDTO(
        guild=guild,
        event_type="clan_manage_notify",
        actor_id=interaction.user.id,
        clan_name=clan,
        actions=actions,
        logging_channel_id=clans_logging_channel,
    )

    bot.dispatch("clan_manage_notify", dto)

    await interaction.response.send_message(
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

    logger.info(
        "[command] - invoked user=%s guild=%s clan=%s changed_leader_to=%s changed_role_to=%s",  # noqa: E501
        interaction.user.id,
        guild.id,
        clan,
        changed_leader_to,
        changed_role_to,
    )
