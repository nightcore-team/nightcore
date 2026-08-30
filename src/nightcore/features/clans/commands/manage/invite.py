"""Command to invite user to your clan."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, Member, app_commands
from discord.interactions import Interaction

from src.infra.db.models.clan import ClanMember
from src.infra.db.operations import get_clan_member
from src.nightcore.components.view.v2 import (
    ErrorViewV2,
    MissingPermissionsViewV2,
)
from src.nightcore.features.clans._groups import manage as clan_manage_group
from src.nightcore.features.clans.components.v2 import ClanInviteViewV2
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)
from src.utils._enums import ClanMemberRoleEnum

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


@clan_manage_group.command(  # type: ignore
    name="invite", description="Пригласить участника в ваш клан."
)
@app_commands.describe(user="Пользователь, которого хотите пригласить.")
@check_required_permissions(PermissionsFlagEnum.NONE)
async def invite(
    interaction: Interaction["Nightcore"],
    user: Member,
):
    """Invite a member to your clan."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)
    member = cast(Member, interaction.user)

    outcome = ""
    async with bot.uow.start() as session:
        # get clanmember
        interaction_clan_member = await get_clan_member(
            session,
            guild_id=guild.id,
            user_id=interaction.user.id,
            with_clan_members=True,
            for_update=True,
        )

        if not interaction_clan_member:
            outcome = "inviter_no_clan"
        else:
            clan = interaction_clan_member.clan
            if len(clan.members) >= clan.max_members:
                outcome = "limit_reached"
            else:
                invited_user_clan_member = await get_clan_member(
                    session,
                    guild_id=guild.id,
                    user_id=user.id,
                    for_update=True,
                )
                if invited_user_clan_member:
                    outcome = "invited_already_in_clan"
                else:
                    if (
                        interaction_clan_member.role
                        != ClanMemberRoleEnum.LEADER
                        and interaction_clan_member.role
                        != ClanMemberRoleEnum.DEPUTY
                    ):
                        outcome = "missing_permissions"
                    else:
                        outcome = "success"

    if outcome == "inviter_no_clan":
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка приглашения в клан",
                "Вы не состоите в клане.",
            ),
            ephemeral=True,
        )
        return

    if outcome == "limit_reached":
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка приглашения в клан",
                "В вашем клане достигнуто максимальное количество участников.",
            ),
            ephemeral=True,
        )
        return

    if outcome == "invited_already_in_clan":
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка приглашения в клан",
                f"Пользователь {user.mention} уже состоит в клане.",
            ),
            ephemeral=True,
        )
        return

    if outcome == "missing_permissions":
        await interaction.response.send_message(
            view=MissingPermissionsViewV2(),
            ephemeral=True,
        )
        return

    interaction_clan_member = cast(ClanMember, interaction_clan_member)

    if outcome == "success":
        view = ClanInviteViewV2(
            bot=bot,
            inviter=member,
            invited_member=user,
            clan=interaction_clan_member.clan,
        )

        await interaction.response.send_message(view=view)

    logger.info(
        "[command] - invoked user=%s guild=%s clan_name=%s invited_user=%s",
        interaction.user.id,
        guild.id,
        interaction_clan_member.clan.name,
        user.id,
    )
