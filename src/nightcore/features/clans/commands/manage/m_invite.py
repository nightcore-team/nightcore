"""Command to invite user to your clan."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, Member, app_commands
from discord.interactions import Interaction

from src.infra.db.operations import get_clan_by_id, get_clan_member
from src.nightcore.components.embed.error import ErrorEmbed
from src.nightcore.features.clans._groups import manage as clan_manage_group
from src.nightcore.features.clans.components.v2 import ClanInviteViewV2
from src.nightcore.features.clans.utils.autocomplete import clans_autocomplete
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


@clan_manage_group.command(  # type: ignore
    name="m_invite", description="Пригласить участника в клан."
)
@app_commands.autocomplete(clan=clans_autocomplete)
@app_commands.describe(
    user="Пользователь, которого хотите пригласить.",
    clan="Клан, в который вы хотите пригласить пользователя.",
)
@check_required_permissions(PermissionsFlagEnum.CLANS_ACCESS)
async def moder_invite(
    interaction: Interaction["Nightcore"],
    clan: str,
    user: Member,
):
    """Invite a member to your clan."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)
    member = cast(Member, interaction.user)

    try:
        clan_id = int(clan)
    except ValueError:
        await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка получения информации о клане",
                "Не удалось найти данный клан в базе данных.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )
        return

    outcome = ""
    async with bot.uow.start() as session:
        # get clanmember
        dbclan = await get_clan_by_id(
            session, guild_id=guild.id, clan_id=clan_id
        )

        if dbclan is None:
            outcome = "clan_not_found"
        else:
            if len(dbclan.members) >= dbclan.max_members:
                outcome = "limit_reached"
            else:
                invited_user_clan_member = await get_clan_member(
                    session, guild_id=guild.id, user_id=user.id
                )
                if invited_user_clan_member:
                    outcome = "invited_already_in_clan"
                else:
                    outcome = "success"

    if outcome == "clan_not_found":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка приглашения в клан",
                "Выбранный клан не найден.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "limit_reached":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка приглашения в клан",
                "В выбранном клане достигнуто максимальное количество участников.",  # noqa: E501
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "invited_already_in_clan":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка приглашения в клан",
                f"Пользователь {user.mention} уже состоит в клане.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "success":
        view = ClanInviteViewV2(
            bot=bot,
            inviter=member,
            invited_member=user,
            clan=dbclan,  # type: ignore
        )

        await interaction.response.send_message(view=view)

    logger.info(
        "[command] - invoked user=%s guild=%s clan_id=%s invited_user=%s",
        interaction.user.id,
        guild.id,
        clan_id,
        user.id,
    )
