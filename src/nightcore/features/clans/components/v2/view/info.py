"""Clan info view v2."""

from collections.abc import Sequence
from datetime import datetime
from typing import TYPE_CHECKING, Self, cast

from discord import ButtonStyle, Color
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

from src.infra.db.models import Clan, ClanMember

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.utils import discord_ts


class ClanMembersActionRow(ActionRow["ClanInfoViewV2"]):
    @button(
        label="Список участников",
        style=ButtonStyle.grey,
        emoji="<:nightcoreClanMembers:1540713940110020629>",
        custom_id="clan_info:members",
        row=0,
    )
    async def get_members(
        self,
        interaction: Interaction["Nightcore"],
        button: Button["ClanInfoViewV2"],
    ) -> None:
        """Get clan members list."""
        v = cast("ClanInfoViewV2", self.view)

        await interaction.response.defer(ephemeral=True)

        view = ClanMemberListViewV2(bot=v.bot, members=v.members)

        await interaction.followup.send(
            view=view,
            ephemeral=True,
        )


class ClanMemberListViewV2(LayoutView):
    def __init__(self, bot: "Nightcore", members: list[ClanMember]) -> None:
        super().__init__(timeout=None)

        container = Container[Self](accent_color=Color.from_str("#9B7EDE"))
        container.add_item(
            TextDisplay[Self](
                "## <:nightcoreClanMembers:1540713940110020629> Список участников клана"  # noqa: E501
            )
        )
        container.add_item(Separator[Self]())

        container.add_item(
            TextDisplay[Self](f"### Общее количество: {len(members)}")
        )
        container.add_item(
            TextDisplay[Self](
                ", ".join(f"<@{member.user_id}>" for member in members)
            )
        )

        self.add_item(container)


class ClanInfoViewV2(LayoutView):
    def __init__(
        self,
        bot: "Nightcore",
        name: str,
        leader_id: int,
        created_at: datetime,
        deputies: list[int],
        lvl: int,
        current_exp: int,
        reputation: float,
        members: list[ClanMember],
        max_members: int,
        max_deputies: int,
        reputation_multiplier: float,
    ) -> None:
        super().__init__(timeout=None)

        self.bot = bot
        self.members = members

        container = Container[Self](accent_color=Color.from_str("#9B7EDE"))

        # header
        container.add_item(
            TextDisplay[Self](
                f"## <:nightcoreInfoPurple:1540714202778308709> Информация о клане `{name}`"  # noqa: E501
            )
        )
        container.add_item(Separator[Self]())

        container.add_item(
            TextDisplay[Self](
                "### <:nightcoreCrownPurple:1540714328209100923> Руководители клана:"  # noqa: E501
            )
        )
        text = ""
        if deputies:
            text = f"**Лидер**: <@{leader_id}>\n"
            text += "**Заместители**: "
            text += ", ".join(f"<@{deputy_id}>" for deputy_id in deputies)
        else:
            text = f"**Лидер**: <@{leader_id}>\n**Заместители**: Нет"

        container.add_item(TextDisplay[Self](text))
        container.add_item(Separator[Self]())

        container.add_item(
            TextDisplay[Self](
                f"### <:nightcoreStats:1540714551119454288> Статистика клана:\n"  # noqa: E501
                f"> Уровень: **{lvl}**\n"
                f"> Опыт: **{current_exp}**\n"
                f"> Репутация: **{reputation}** (x{reputation_multiplier})\n"
                f"> Участники: **{len(self.members)}/{max_members}**\n"
                f"> Максимальное количество заместителей: **{max_deputies}**"
            )
        )
        container.add_item(Separator[Self]())

        container.add_item(
            TextDisplay[Self]("**Дата создания:** " + discord_ts(created_at))
        )
        container.add_item(Separator[Self]())

        container.add_item(ClanMembersActionRow())

        self.add_item(container)


class ClanListViewV2(LayoutView):
    def __init__(
        self,
        bot: "Nightcore",
        clans: Sequence[Clan],
        sort_by: str | None = None,
    ) -> None:
        super().__init__(timeout=None)

        container = Container[Self](accent_color=Color.from_str("#9B7EDE"))
        container.add_item(
            TextDisplay[Self](
                "## <:nightcoreClanMembers:1540713940110020629> Список кланов"
            )
        )
        container.add_item(Separator[Self]())

        if clans:
            for clan in clans:
                match sort_by:
                    case "members":
                        container.add_item(
                            TextDisplay[Self](
                                f"**{clan.name}**\n"
                                f"<:nightcoreCrownPurple:1540714328209100923> Лидер: <@{clan.leader.user_id}>\n"  # noqa: E501
                                f"Роль: <@&{clan.role_id}>\n"
                                f"Участники: {len(clan.members)}/{clan.max_members}\n\n"  # noqa: E501
                            )
                        )
                    case "reputation":
                        container.add_item(
                            TextDisplay[Self](
                                f"**{clan.name}**\n"
                                f"<:nightcoreCrownPurple:1540714328209100923> Лидер: <@{clan.leader.user_id}>\n"  # noqa: E501
                                f"Роль: <@&{clan.role_id}>\n"
                                f"Репутация: {clan.coins}\n\n"
                            )
                        )
                    case "created_at":
                        container.add_item(
                            TextDisplay[Self](
                                f"**{clan.name}**\n"
                                f"<:nightcoreCrownPurple:1540714328209100923> Лидер: <@{clan.leader.user_id}>\n"  # noqa: E501
                                f"Роль: <@&{clan.role_id}>\n"
                                f"Дата создания: {discord_ts(clan.created_at)}\n\n"  # noqa: E501
                            )
                        )

                    case _:
                        container.add_item(
                            TextDisplay[Self](
                                f"**{clan.name}**\n"
                                f"<:nightcoreCrownPurple:1540714328209100923> Лидер: <@{clan.leader.user_id}>\n"  # noqa: E501
                                f"Роль: <@&{clan.role_id}>\n"
                                f"Участники: {len(clan.members)}/{clan.max_members}\n"  # noqa: E501
                                f"Репутация: {clan.coins}\n"
                                f"Дата создания: {discord_ts(clan.created_at)}\n\n"  # noqa: E501
                            )
                        )
        else:
            container.add_item(
                TextDisplay[Self]("> На этом сервере нет ни одного клана.")
            )

        self.add_item(container)
