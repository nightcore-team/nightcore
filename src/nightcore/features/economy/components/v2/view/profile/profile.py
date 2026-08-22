"""
User profile view v2 component.

Used for displaying a user's profile with their stats, cases, and colors.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Self

import discord
from discord.ui import (
    Button,
    Container,
    LayoutView,
    Section,
    Separator,
    TextDisplay,
    Thumbnail,
)

if TYPE_CHECKING:
    from src.infra.db.models.clan import Clan
    from src.nightcore.bot import Nightcore

from src.nightcore.utils import discord_ts

from .collection import UserProfileActionRow


class UserProfileViewV2(LayoutView):
    def __init__(
        self,
        bot: "Nightcore",
        guild_id: int,
        user_id: int,
        lvl: int,
        current_exp: int,
        exp_to_lvl: int,
        balance: int,
        battlepass_level: int,
        coin_name: str | None,
        voice_activity: str,
        messages_count: int,
        avatar_url: str,
        clan: "Clan | None" = None,
    ):
        super().__init__(timeout=None)

        self.bot = bot
        self.guild_id = guild_id
        self.user_id = user_id

        container = Container[Self](
            accent_color=discord.Color.from_str("#5EC9B3")
        )

        container.add_item(
            TextDisplay[Self](
                f"### <:nightcorePyramid:1540402041703239843> Профиль пользователя <@{user_id}>",  # noqa: E501
            )
        )
        container.add_item(Separator[Self]())

        container.add_item(
            Section[Self](
                TextDisplay[Self](
                    f"> <:nightcoreLevelUp:1540402294275969024> **Уровень:** **{lvl} | {current_exp}/{exp_to_lvl})**\n"  # noqa: E501
                    f"> <:nightcoreBanknote:1540403146072002624> **Валюта:** {balance} {coin_name if coin_name else ''}\n"  # noqa: E501
                    f"> <:nightcoreMessage:1540403723342192810> *Количество сообщений:** {messages_count}\n"  # noqa: E501
                    f"> <:audiolines:1540403938782748693> **Голосовая активность:** {voice_activity}\n"  # noqa: E501
                ),
                accessory=Thumbnail[Self](avatar_url),
            )
        )
        container.add_item(Separator[Self]())
        container.add_item(
            Section[Self](
                TextDisplay(
                    "### <:nightcoreBattlepass:1540406661146091590> Баттлпасс\n"  # noqa: E501
                    f"> Текущий уровень: {battlepass_level}"
                ),
                accessory=Button[Self](
                    label="/battlepass",
                    style=discord.ButtonStyle.secondary,
                    emoji="<:nightcoreGem:1540406663377453097>",
                    custom_id=f"battlepass:{user_id}:show",
                ),
            )
        )
        if clan:
            container.add_item(
                Section[Self](
                    TextDisplay(
                        "### <:nightcoreUserClan:1540407087648211045> Клан\n"
                        f"> {clan.name}"
                    ),
                    accessory=Button[Self](
                        label="/clan info",
                        style=discord.ButtonStyle.secondary,
                        emoji="<:nightcoreUsersGroup:1540426045029748737>",
                        custom_id=f"clan:{user_id}:info",
                    ),
                )
            )

        container.add_item(Separator())

        container.add_item(
            UserProfileActionRow(
                bot=bot,
                guild_id=guild_id,
                user_id=user_id,
            )
        )
        container.add_item(Separator[Self]())

        now = datetime.now(UTC)

        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {bot.user.name} in {discord_ts(now)}"  # type: ignore
            )
        )

        self.add_item(container)
