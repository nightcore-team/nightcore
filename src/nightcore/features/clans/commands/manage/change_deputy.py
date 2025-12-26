"""Command to change clan deputy."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, Member, app_commands
from discord.interactions import Interaction

from src.infra.db.models._enums import (
    ChannelType,
    ClanManageActionEnum,
    ClanMemberRoleEnum,
)
from src.infra.db.models.guild import GuildLoggingConfig
from src.infra.db.operations import (
    get_clan_member,
    get_specified_channel,
)
from src.nightcore.components.embed import (
    ErrorEmbed,
    MissingPermissionsEmbed,
    SuccessMoveEmbed,
)
from src.nightcore.features.clans._groups import manage as manage_clan_group
from src.nightcore.features.clans.events.dto.clan_manage_notify import (
    ClanManageAction,
    ClanManageNotifyDTO,
)
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


@manage_clan_group.command(  # type: ignore
    name="change_deputy", description="Изменить заместителя клана."
)
@app_commands.choices(
    option=[
        app_commands.Choice(name="Назначить", value="add"),
        app_commands.Choice(name="Снять", value="remove"),
    ]
)
@app_commands.describe(
    member="Участник, которого вы хотите назначить/снять с должности заместителя.",  # noqa: E501
    option="Выберите, хотите ли вы назначить или снять заместителя.",
)
@check_required_permissions(PermissionsFlagEnum.NONE)
async def change_deputy(
    interaction: Interaction["Nightcore"],
    member: Member,
    option: str,
):
    """Change the clan deputy."""
    bot = interaction.client
    guild = cast(Guild, interaction.guild)
    user = cast(Member, interaction.user)

    if user == member:
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка изменения заместителя",
                "Вы не можете изменить свою собственную роль.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    # Змінні для винесення з context manager
    outcome = ""
    clan_name = ""
    member_name = ""
    current_deputies_count = 0
    max_deputies = 0

    async with bot.uow.start() as session:
        leader = await get_clan_member(
            session,
            guild_id=guild.id,
            user_id=user.id,
            with_relations=True,
        )

        if not leader:
            outcome = "not_in_clan"
        elif leader.role != ClanMemberRoleEnum.LEADER:
            outcome = "not_leader"
        else:
            clan_member = await get_clan_member(
                session,
                guild_id=guild.id,
                user_id=member.id,
            )

            if not clan_member or clan_member.clan_id != leader.clan_id:
                outcome = "member_not_in_clan"
            else:
                clan_name = leader.clan.name
                member_name = member.display_name
                current_deputies_count = len(leader.clan.deputies)
                max_deputies = leader.clan.max_deputies

                match option:
                    case "add":
                        if current_deputies_count >= max_deputies:
                            outcome = "max_deputies_reached"
                        elif clan_member.role == ClanMemberRoleEnum.DEPUTY:
                            outcome = "already_deputy"
                        else:
                            clan_member.role = ClanMemberRoleEnum.DEPUTY
                            await session.flush()
                            outcome = "deputy_added"

                    case "remove":
                        if clan_member.role != ClanMemberRoleEnum.DEPUTY:
                            outcome = "not_deputy"
                        else:
                            clan_member.role = ClanMemberRoleEnum.MEMBER
                            await session.flush()
                            outcome = "deputy_removed"

                    case _:
                        outcome = "invalid_option"

    if outcome == "not_in_clan":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка изменения заместителя",
                "Вы не состоите в клане.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "not_leader":
        return await interaction.response.send_message(
            embed=MissingPermissionsEmbed(
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "member_not_in_clan":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка изменения заместителя",
                "Указанный пользователь не состоит в вашем клане.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "max_deputies_reached":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка изменения заместителя",
                f"Превышено максимальное количество заместителей в клане ({current_deputies_count}/{max_deputies}).",  # noqa: E501
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "already_deputy":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка изменения заместителя",
                "Указанный пользователь уже является заместителем.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "not_deputy":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка изменения заместителя",
                "Указанный пользователь не является заместителем.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "invalid_option":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка изменения заместителя",
                "Неверная опция. Используйте 'add' или 'remove'.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    async with bot.uow.start() as session:
        clans_logging_channel = await get_specified_channel(
            session,
            guild_id=guild.id,
            config_type=GuildLoggingConfig,
            channel_type=ChannelType.LOGGING_CLANS,
        )

    if option == "add":
        action_type = ClanManageActionEnum.ADD_DEPUTY

    if option == "remove":
        action_type = ClanManageActionEnum.REMOVE_DEPUTY

    clan_deputy_change_action = ClanManageAction(
        type=action_type,  # type: ignore one of the ifs on 215 or 218 will always work, because the option is required for selection
        after=member.mention,
    )

    dto = ClanManageNotifyDTO(
        guild=guild,
        event_type="clan_manage_notify",
        actor_id=interaction.user.id,
        clan_name=leader.clan.name,  # type: ignore The clan will always exist here because of the checks on lines 91 and 132
        actions=[clan_deputy_change_action],
        logging_channel_id=clans_logging_channel,
    )

    bot.dispatch("clan_manage_notify", dto)

    if outcome == "deputy_added":
        await interaction.response.send_message(
            embed=SuccessMoveEmbed(
                "Заместитель назначен",
                f"Пользователь **{member_name}** был назначен заместителем клана **{clan_name}**.",  # noqa: E501
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "deputy_removed":
        await interaction.response.send_message(
            embed=SuccessMoveEmbed(
                "Заместитель снят",
                f"Пользователь **{member_name}** был снят с заместителя клана **{clan_name}**.",  # noqa: E501
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    logger.info(
        "[command] - invoked user=%s guild=%s clan_name=%s member=%s option=%s outcome=%s",  # noqa: E501
        interaction.user.id,
        guild.id,
        clan_name,
        member.id,
        option,
        outcome,
    )
