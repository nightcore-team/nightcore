"""Command to kick a member from a clan."""

import asyncio
import logging
from collections.abc import Awaitable
from typing import TYPE_CHECKING, Any, cast

from discord import Guild, User, app_commands
from discord.interactions import Interaction

from src.infra.db.models._enums import (
    ChannelType,
    ClanManageActionEnum,
    ClanMemberRoleEnum,
)
from src.infra.db.models.guild import GuildLoggingConfig
from src.infra.db.operations import get_clan_member, get_specified_channel
from src.nightcore.components.embed import (
    ErrorEmbed,
    MissingPermissionsEmbed,
    SuccessMoveEmbed,
)
from src.nightcore.features.clans._groups import manage as clan_manage_group
from src.nightcore.features.clans.events.dto.clan_manage_notify import (
    ClanManageAction,
    ClanManageNotifyDTO,
)
from src.nightcore.utils import ensure_member_exists, ensure_role_exists
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


@clan_manage_group.command(  # type: ignore
    name="kick", description="Кикнуть участника из клана."
)
@app_commands.describe(user="Пользователь, которого хотите кикнуть")
@check_required_permissions(PermissionsFlagEnum.NONE)
async def kick(
    interaction: Interaction["Nightcore"],
    user: User,
):
    """Kick member from your clan."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)

    async with bot.uow.start() as session:
        # get clanmember
        interaction_clan_member = await get_clan_member(
            session,
            guild_id=guild.id,
            user_id=interaction.user.id,
            with_relations=True,
        )

        kicked_user_clan_member = await get_clan_member(
            session, guild_id=guild.id, user_id=user.id
        )

    if not interaction_clan_member:
        await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка кика пользователя",
                "Вы не состоите в клане.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )
        return

    if not kicked_user_clan_member:
        await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка кика пользователя",
                f"{user.mention} не состоит ни в одном из кланов.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )
        return

    if (
        interaction_clan_member.role != ClanMemberRoleEnum.LEADER
        and interaction_clan_member.role != ClanMemberRoleEnum.DEPUTY
    ):
        await interaction.response.send_message(
            embed=MissingPermissionsEmbed(
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )
        return

    if interaction_clan_member.clan_id != kicked_user_clan_member.clan_id:
        await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка кика пользователя",
                f"{user.mention} не состоит в вашем клане.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )
        return

    async with bot.uow.start() as session:
        try:
            await session.delete(kicked_user_clan_member)
        except Exception as e:
            logger.exception(
                "[clans] Failed to delete clanmember in guild %s: %s",
                guild.id,
                e,
            )
            await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка кика пользователя",
                    "Ошибка удаления пользователя в базе данных.",
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                )
            )

    embed = SuccessMoveEmbed(
        "Кик пользователя из клана",
        "Пользователь был успешно кикнут из клана.",
        bot.user.display_name,  # type: ignore
        bot.user.display_avatar.url,  # type: ignore
    )

    to_gather: list[Awaitable[Any]] = [
        interaction.response.send_message(embed=embed, ephemeral=True),
    ]

    if member := await ensure_member_exists(guild, user.id):
        role = await ensure_role_exists(
            guild=guild, role_id=interaction_clan_member.clan.role_id
        )

        if not role:
            await interaction.response.send_message(
                embed=embed, ephemeral=True
            )
            logger.error(
                "[clans] Clan role %s not found in guild %s",
                interaction_clan_member.clan.role_id,
                guild.id,
            )
            return

        to_gather.append(
            member.remove_roles(role, reason="Кик из клана."),
        )

    await asyncio.gather(
        *to_gather,
    )

    async with bot.uow.start() as session:
        clans_logging_channel = await get_specified_channel(
            session,
            guild_id=guild.id,
            config_type=GuildLoggingConfig,
            channel_type=ChannelType.LOGGING_CLANS,
        )

    clan_kick_member_action = ClanManageAction(
        type=ClanManageActionEnum.KICK_MEMBER, after=user.mention
    )

    dto = ClanManageNotifyDTO(
        guild=guild,
        event_type="clan_manage_notify",
        actor_id=interaction.user.id,
        clan_name=interaction_clan_member.clan.name,
        actions=[clan_kick_member_action],
        logging_channel_id=clans_logging_channel,
    )

    bot.dispatch("clan_manage_notify", dto)

    logger.info(
        "[command] - invoked user=%s guild=%s clan_name=%s kicked_user=%s",
        interaction.user.id,
        guild.id,
        interaction_clan_member.clan.name,
        user.id,
    )
