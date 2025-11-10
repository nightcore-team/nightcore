"""Clan info view v2."""

import asyncio
import logging
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Self, cast

from discord import ButtonStyle, Member
from discord.interactions import Interaction
from discord.ui import (
    ActionRow,
    Button,
    Container,
    LayoutView,
    Separator,
    TextDisplay,
    button,
)
from sqlalchemy.exc import IntegrityError

from src.infra.db.models import Clan, ClanMember
from src.infra.db.models._enums import ClanMemberRoleEnum
from src.infra.db.operations import create_clan_member

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.components.embed import ErrorEmbed
from src.nightcore.utils import discord_ts, ensure_role_exists

logger = logging.getLogger(__name__)


class ClanInviteActionRow(ActionRow["ClanInviteViewV2"]):
    @button(
        label="Принять приглашение",
        style=ButtonStyle.green,
        emoji="<:52104checkmark:1414732973005340672>",
        custom_id="clan_invite:accept",
    )
    async def accept(
        self,
        interaction: Interaction["Nightcore"],
        button: Button["ClanInviteViewV2"],
    ) -> None:
        """Accept clan invite."""

        view = cast("ClanInviteViewV2", self.view)

        await interaction.response.defer(ephemeral=True)

        if interaction.user.id != view.invited_member.id:
            await interaction.followup.send(
                "Это приглашение не для вас.", ephemeral=True
            )
            return

        async with view.bot.uow.start() as session:
            try:
                await create_clan_member(
                    session,
                    guild_id=view.inviter.guild_id,
                    clan_id=view.inviter.clan_id,
                    user_id=view.invited_member.id,
                    role=ClanMemberRoleEnum.MEMBER,
                )
                await session.flush()
            except IntegrityError:
                await interaction.followup.send(
                    embed=ErrorEmbed(
                        "Ошибка принятия приглашения в клан",
                        "Вы уже состоите в клане.",
                        view.bot.user.display_name,  # type: ignore
                        view.bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )
                return
            except Exception as e:
                logger.exception(
                    "[clans] Error occurred while accepting clan invite in guild %s for user %s: %s",  # noqa: E501
                    view.inviter.guild_id,
                    view.invited_member.id,
                    e,
                )
                await interaction.followup.send(
                    embed=ErrorEmbed(
                        "Ошибка принятия приглашения в клан",
                        "Произошла ошибка при обработке вашего запроса.",
                        view.bot.user.display_name,  # type: ignore
                        view.bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )
                return

        role = await ensure_role_exists(
            guild=view.invited_member.guild, role_id=view.inviter.clan.role_id
        )
        if not role:
            logger.error(
                "[clans] Clan role %s not found in guild %s",
                view.inviter.clan.role_id,
                view.invited_member.guild.id,
            )
            await interaction.followup.send(
                "Вы успешно приняли приглашение в клан.",
                ephemeral=True,
            )
            return

        await asyncio.gather(
            interaction.followup.send(
                "Вы успешно приняли приглашение в клан.", ephemeral=True
            ),
            view.invited_member.add_roles(
                role, reason="Принятие приглашения в клан"
            ),
        )

        await interaction.message.delete()  # type: ignore

    @button(
        label="Отклонить приглашение",
        style=ButtonStyle.red,
        emoji="<:9349_nope:1414732960841859182>",
        custom_id="clan_invite:decline",
    )
    async def decline(
        self,
        interaction: Interaction["Nightcore"],
        button: Button["ClanInviteViewV2"],
    ) -> None:
        """Decline clan invite."""

        view = cast("ClanInviteViewV2", self.view)
        await interaction.response.defer(ephemeral=True)

        if interaction.user.id != view.invited_member.id:
            await interaction.followup.send(
                "Это приглашение не для вас.", ephemeral=True
            )
            return

        await interaction.followup.send(
            "Вы отклонили приглашение в клан.", ephemeral=True
        )

        await interaction.message.delete()  # type: ignore


class ClanInviteViewV2(LayoutView):
    def __init__(
        self, bot: "Nightcore", inviter: ClanMember, invited_member: Member
    ) -> None:
        super().__init__(timeout=180)

        self.bot = bot
        self.inviter = inviter
        self.invited_member = invited_member

        container = Container[Self]()

        container.add_item(
            TextDisplay[Self](
                f"## <:32451information:1430231400208011428> | Приглашение в клан <:42920arrowrightalt:1421170550759489616> {invited_member.mention}"  # noqa: E501
            )
        )
        container.add_item(Separator[Self]())

        container.add_item(
            TextDisplay[Self](
                f"<:241508crown:1430227486545018961> **Лидер/заместитель** <@{inviter.user_id}>"  # noqa: E501
                f" приглашает Вас в свой клан **{inviter.clan.name}**\n"
            )
        )

        container.add_item(
            TextDisplay[Self](
                "Воспользуйтесь кнопками ниже, чтобы принять/отклонить приглашение."  # noqa: E501
            )
        )
        container.add_item(Separator[Self]())

        container.add_item(ClanInviteActionRow())
        container.add_item(Separator[Self]())

        now = datetime.now(timezone.utc)
        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {self.bot.user.name} in {discord_ts(now)}"  # type: ignore
            )
        )

        self.add_item(container)


class ClanListViewV2(LayoutView):
    def __init__(self, bot: "Nightcore", clans: Sequence[Clan]) -> None:
        super().__init__(timeout=180)

        container = Container[Self]()
        container.add_item(
            TextDisplay[Self](
                "## <:32451information:1430231400208011428> Список кланов"
            )
        )
        container.add_item(Separator[Self]())

        for clan in clans:
            container.add_item(
                TextDisplay[Self](
                    f"**{clan.name}**\n"
                    f"<:241508crown:1430227486545018961> Лидер: <@{clan.leader.user_id}>\n"  # noqa: E501
                    f"Дата создания: {discord_ts(clan.created_at)}\n"
                    f"Роль: <@&{clan.role_id}>\n"
                    f"Участники: {len(clan.members)}/{clan.max_members}\n\n"
                )
            )

        container.add_item(Separator[Self]())

        now = datetime.now(timezone.utc)
        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {bot.user.name} in {discord_ts(now)}"  # type: ignore
            )
        )

        self.add_item(container)
