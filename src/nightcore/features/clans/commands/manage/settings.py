"""Command to manage clan settings."""

import asyncio
import logging
from typing import TYPE_CHECKING, cast

from discord import (
    Guild,
    Member,
    PermissionOverwrite,
    Role,
    TextChannel,
    app_commands,
)
from discord.interactions import Interaction

from src.infra.db.models import GuildLoggingConfig
from src.infra.db.operations import (
    create_clan_member,
    get_clan_by_id,
    get_clan_member,
    get_specified_webhook,
)
from src.nightcore.components.view.v2 import (
    EntityNotFoundViewV2,
    ErrorViewV2,
    NoOptionsSuppliedViewV2,
    SuccessViewV2,
)
from src.nightcore.features.clans._groups import manage as manage_clan_group
from src.nightcore.features.clans.events.dto.clan_manage_notify import (
    ClanManageAction,
    ClanManageNotifyDTO,
)
from src.nightcore.features.clans.utils import clans_autocomplete
from src.nightcore.utils import (
    compare_top_roles,
    ensure_messageable_channel_exists,
    ensure_role_exists,
)
from src.nightcore.utils.object import safe_delete_channel
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)
from src.utils._enums import (
    ChannelType,
    ClanManageActionEnum,
    ClanMemberRoleEnum,
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
    new_name="Новое название клана",
    new_channel="Новый текстовый канал для клана",
)
@app_commands.autocomplete(clan=clans_autocomplete)
@check_required_permissions(PermissionsFlagEnum.CLANS_ACCESS)
async def settings(
    interaction: Interaction["Nightcore"],
    clan: str,
    new_leader: Member | None = None,
    new_role: Role | None = None,
    new_name: app_commands.Range[str, 1, 100] | None = None,
    new_channel: TextChannel | None = None,
):
    """Manage clan settings."""
    bot = interaction.client
    guild = cast(Guild, interaction.guild)

    try:
        clan_id = int(clan)
    except ValueError:
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка получения информации о клане",
                "Не удалось найти данный клан в базе данных.",
            ),
            ephemeral=True,
        )
        return

    if not new_leader and not new_role and not new_name and not new_channel:
        await interaction.response.send_message(
            view=NoOptionsSuppliedViewV2(),
            ephemeral=True,
        )
        return

    outcome: str | None = None
    clan_name: str | None = None
    changed_leader_to: int | None = None
    changed_role_to: int | None = None
    old_role_id: int | None = None
    old_name: str | None = None
    old_channel_id: int | None = None
    leader_in_clan: bool = True

    # Deferred Discord IO - captured inside transaction, executed after commit
    pending_old_channel_id: int | None = None
    pending_new_channel: TextChannel | None = None
    pending_role_id_for_channel: int | None = None
    before_leader_id: int | None = None
    dto_role_id: int | None = None
    dto_channel_id: int | None = None

    async with bot.uow.start() as session:
        if outcome is None:
            clan_entity = await get_clan_by_id(
                session, guild_id=guild.id, clan_id=clan_id, for_update=True
            )
            if not clan_entity:
                outcome = "clan_not_found"
            else:
                clan_name = clan_entity.name  # DTO field
                dto_role_id = clan_entity.role_id
                dto_channel_id = clan_entity.clan_channel_id
                if clan_entity.leader is not None:
                    before_leader_id = clan_entity.leader.id

                # change leader
                if new_leader:
                    clan_member = await get_clan_member(
                        session,
                        guild_id=guild.id,
                        user_id=new_leader.id,
                        for_update=True,
                    )

                    if clan_member is None:
                        if len(clan_entity.members) >= clan_entity.max_members:
                            outcome = "max_members_achieved"
                        else:
                            try:
                                # Make old leader a member
                                clan_entity.leader.role = (
                                    ClanMemberRoleEnum.MEMBER
                                )
                                # Make new one the leader
                                await session.flush()

                            except Exception as e:
                                logger.error(
                                    "[clans] Error changing clan leader in guild %s: %s",  # noqa: E501
                                    guild.id,
                                    e,
                                )
                                outcome = "leader_change_internal_error"

                            # Keep business logic: create member even if
                            # previous flush failed is original behavior;
                            # guard to avoid creating on outcome.
                            if outcome is None:
                                await create_clan_member(
                                    session,
                                    guild_id=guild.id,
                                    clan_id=clan_entity.id,
                                    user_id=new_leader.id,
                                    role=ClanMemberRoleEnum.LEADER,
                                )
                                leader_in_clan = False
                                changed_leader_to = new_leader.id
                    else:
                        if clan_member.clan_id != clan_entity.id:
                            outcome = "new_leader_not_in_clan"
                        elif clan_member.role == ClanMemberRoleEnum.LEADER:
                            outcome = "already_leader"
                        else:
                            try:
                                # Make old leader a member
                                clan_entity.leader.role = (
                                    ClanMemberRoleEnum.MEMBER
                                )
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
                                old_role_id = clan_entity.role_id
                                clan_entity.role_id = new_role.id
                                changed_role_to = new_role.id
                                dto_role_id = new_role.id
                            except Exception as e:
                                logger.error(
                                    "[clans] Error changing clan role in guild %s: %s",  # noqa: E501
                                    guild.id,
                                    e,
                                )
                                outcome = "role_change_internal_error"

                # change clan channel - DB mutation only, IO deferred
                if outcome is None and new_channel:
                    pending_old_channel_id = clan_entity.clan_channel_id
                    old_channel_id = pending_old_channel_id
                    pending_new_channel = new_channel
                    pending_role_id_for_channel = clan_entity.role_id
                    dto_channel_id = new_channel.id
                    clan_entity.clan_channel_id = new_channel.id

                # change clan name
                if outcome is None and new_name:
                    if new_name == clan_entity.name:
                        outcome = "name_equal_to_the_current"
                    else:
                        try:
                            old_name = clan_entity.name
                            clan_entity.name = new_name
                            # keep clan_name as original for success view?
                            # clan_name already holds original
                            dto_channel_id = clan_entity.clan_channel_id
                            # dto_role_id already captured
                        except Exception as e:
                            logger.error(
                                "[clans] Error changing clan name in guild %s: %s",  # noqa: E501
                                guild.id,
                                e,
                            )
                            outcome = "name_change_internal_error"

    # Discord IO outside transaction - channel overwrites & old channel cleanup
    if outcome is None and pending_new_channel is not None:
        # Use captured role id (after possible role change)
        try:
            if pending_old_channel_id is not None:
                channel = await ensure_messageable_channel_exists(
                    guild, pending_old_channel_id
                )
                if channel is not None:
                    asyncio.create_task(
                        safe_delete_channel(
                            channel, "Удаление старого канала клана"
                        )
                    )

            clan_role = await ensure_role_exists(
                guild,
                pending_role_id_for_channel,  # type: ignore[arg-type]
            )

            overwrites = {
                guild.default_role: PermissionOverwrite(
                    read_message_history=False,
                    read_messages=False,
                ),
            }

            if clan_role:
                overwrites[clan_role] = PermissionOverwrite(
                    read_message_history=True,
                    read_messages=True,
                    send_messages=True,
                    attach_files=True,
                    add_reactions=True,
                )

            try:
                await pending_new_channel.edit(overwrites=overwrites)
            except Exception as e:
                logger.error(
                    "[clans] Error editing clan channel overwrites in guild %s: %s",  # noqa: E501
                    guild.id,
                    e,
                )
        except Exception as e:
            logger.error(
                "[clans] Error handling clan channel IO in guild %s: %s",
                guild.id,
                e,
            )

    if outcome == "clan_not_found":
        await interaction.response.send_message(
            view=EntityNotFoundViewV2("clan"),
            ephemeral=True,
        )
        return

    if outcome == "new_leader_not_in_clan":
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка назначения лидера",
                f"{new_leader.mention} не состоит в вашем клане.",  # type: ignore[union-attr]
            ),
            ephemeral=True,
        )
        return

    if outcome == "max_members_achieved":
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка назначения лидера",
                "Достигнуто максимальное количество участников в клане.",
            ),
            ephemeral=True,
        )
        return

    if outcome == "already_leader":
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка назначения лидера",
                f"{new_leader.mention} уже является лидером клана.",  # type: ignore[union-attr]
            ),
            ephemeral=True,
        )
        return

    if outcome == "role_has_administrator_permissions":
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка изменения роли клана",
                "Роль клана не может иметь права администратора.",
            ),
            ephemeral=True,
        )
        return

    if outcome == "role_high_than_bot":
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка изменения роли клана",
                "Роль клана должна быть ниже верхней роли бота.",
            ),
            ephemeral=True,
        )
        return

    if outcome == "leader_change_internal_error":
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка назначения лидера",
                "Произошла ошибка при изменении лидера клана.",
            ),
            ephemeral=True,
        )
        return

    if outcome == "role_change_internal_error":
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка изменения роли клана",
                "Произошла ошибка при изменении роли клана.",
            ),
            ephemeral=True,
        )
        return

    if outcome == "name_change_internal_error":
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка изменения названии клана",
                "Произошла ошибка при изменении названия клана.",
            ),
            ephemeral=True,
        )
        return

    if outcome == "name_equal_to_the_current":
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка изменения названии клана",
                "Новое название не отличается от текущего.",
            ),
            ephemeral=True,
        )
        return

    summary_lines: list[str] = []
    if changed_leader_to:
        summary_lines.append(
            f"Новый лидер: {new_leader.mention}"  # type: ignore
        )
    if changed_role_to:
        summary_lines.append(f"Роль клана обновлена: <@&{changed_role_to}>")
    if new_name:
        summary_lines.append(f"Название клана обновлено: {new_name}")
    if new_channel is not None:
        summary_lines.append(f"Канал клана обновлен: <#{new_channel.id}>")
    details = (
        "\n".join(summary_lines)
        if summary_lines
        else "Настройки клана успешно обновлены."
    )

    async with bot.uow.start() as session:
        clans_logging_webhook = await get_specified_webhook(
            session,
            guild_id=guild.id,
            config_type=GuildLoggingConfig,
            channel_type=ChannelType.LOGGING_CLANS,
        )

    actions: list[ClanManageAction] = []

    if new_leader is not None:
        # before_leader_id captured under FOR UPDATE, fallback to 0
        before_mention = (
            f"<@{before_leader_id}>" if before_leader_id else "неизвестно"
        )
        clan_change_leader_action = ClanManageAction(
            type=ClanManageActionEnum.CHANGE_LEADER,
            before=before_mention,
            after=new_leader.mention,
        )

        actions.append(clan_change_leader_action)

    if new_role is not None and old_role_id is not None:
        # dto_role_id holds the new role id after commit
        clan_change_role_action = ClanManageAction(
            type=ClanManageActionEnum.CHANGE_ROLE,
            before=f"<@&{old_role_id}> ('{old_role_id}')",
            after=f"<@&{dto_role_id}> ('{dto_role_id}')",
        )

        actions.append(clan_change_role_action)

    if new_channel is not None and old_channel_id is not None:
        clan_change_channel_action = ClanManageAction(
            type=ClanManageActionEnum.CHANGE_CHANNEL,
            before=f"<#{old_channel_id}> ('{old_channel_id}')",
            after=f"<#{dto_channel_id}> ('{dto_channel_id}')",  # noqa: E501
        )

        actions.append(clan_change_channel_action)

    if new_name is not None and old_name is not None:
        clan_change_name_action = ClanManageAction(
            type=ClanManageActionEnum.CHANGE_NAME,
            before=old_name,
            after=new_name,
        )

        actions.append(clan_change_name_action)

    dto = ClanManageNotifyDTO(
        guild=guild,
        event_type="clan_manage_notify",
        actor_id=interaction.user.id,
        clan_name=clan,  # type: ignore[arg-type]
        actions=actions,
        logging_webhook=clans_logging_webhook,
    )

    bot.dispatch("clan_manage_notify", dto)

    await interaction.response.send_message(
        view=SuccessViewV2(
            "Настройки клана обновлены",
            details
            if clan_name is None
            else f"Клан: **{clan_name}**\n{details}",
        ),
        ephemeral=True,
    )

    if not leader_in_clan and changed_leader_to is not None:
        # Use dto_role_id which is the current role id
        role = await ensure_role_exists(
            guild=guild,
            role_id=dto_role_id,  # type: ignore[arg-type]
        )

        if role:
            try:
                await new_leader.add_roles(role)  # type: ignore[union-attr]
            except Exception:
                await interaction.followup.send(
                    view=ErrorViewV2(
                        "Ошибка выдачи роли лидеру",
                        "При выдаче роли клана лидеру произошла ошибка.",
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
