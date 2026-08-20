"""
User profile view v2 component.

Used for displaying a user's profile with their stats, cases, and colors.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Self

import discord
from discord.ui import (
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
            accent_color=discord.Color.from_str("#ffffff")
        )

        container.add_item(
            TextDisplay[Self](
                f"## <:snowflakesnightcore:1450559241365491723> Профиль пользователя <@{user_id}>",  # noqa: E501
            )
        )
        container.add_item(Separator[Self]())

        container.add_item(
            Section[Self](
                TextDisplay[Self](
                    f"**Уровень:** **`{lvl}`**\n"
                    f"**Опыт:** **`{current_exp} / {exp_to_lvl}`**\n"
                    f"**Баланс:** {balance} {coin_name if coin_name else ''}\n"
                    f"**Количество сообщений на сервере:** {messages_count}\n"
                    f"**Голосовая активность:** {voice_activity}"
                    f"\n**Уровень баттлпаса:** {battlepass_level}"
                    + (f"\n\n> **Клан:** {clan.name}" if clan else "")
                ),
                accessory=Thumbnail[Self](avatar_url),
            )
        )
        container.add_item(Separator[Self]())

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
