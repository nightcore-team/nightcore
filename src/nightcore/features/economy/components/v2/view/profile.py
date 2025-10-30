"""User profile view v2 component."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Self

from discord import Color
from discord.ui import (
    Container,
    LayoutView,
    Section,
    Separator,
    TextDisplay,
    Thumbnail,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.infra.db.models._annot import CasesAnnot
from src.nightcore.features.economy.utils.case import CASES_NAMES
from src.nightcore.utils import discord_ts


class UserProfileViewV2(LayoutView):
    def __init__(
        self,
        bot: "Nightcore",
        user_id: int,
        lvl: int,
        current_exp: int,
        exp_to_lvl: int,
        balance: int,
        coin_name: str | None,
        voice_activity: str,
        messages_count: int,
        joined_at: datetime | None,
        avatar_url: str,
        cases: CasesAnnot,
        colors: list[int],
    ):
        super().__init__(timeout=10)

        container = Container[Self](accent_color=Color.from_str("#9e5bcb"))

        container.add_item(
            TextDisplay[Self](
                f"### <:6213astralbutterfly:1432749438778085427> Профиль пользователя <@{user_id}>",  # noqa: E501
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
                ),
                accessory=Thumbnail[Self](avatar_url),
            )
        )
        container.add_item(Separator[Self]())

        if cases:
            container.add_item(TextDisplay[Self]("### Кейсы: "))
            container.add_item(
                TextDisplay[Self](
                    "\n".join(
                        f"> {CASES_NAMES.get(case_name, case_name)}, количество: {count}"  # noqa: E501
                        for case_name, count in cases.items()
                    )
                )
            )
            container.add_item(Separator[Self]())

        if colors:
            container.add_item(TextDisplay[Self]("### Цвета: "))
            container.add_item(
                TextDisplay[Self](
                    "\n".join(f"> <@&{role_id}>" for role_id in colors)
                )
            )
            container.add_item(Separator[Self]())

        now = datetime.now(timezone.utc)
        joined_ts = discord_ts(joined_at, "R") if joined_at else "N/A"

        container.add_item(
            TextDisplay[Self](
                f"-# Joined at: {joined_ts}\n-# Powered by {bot.user.name} in {discord_ts(now)}"  # noqa: E501 # type: ignore
            )
        )

        self.add_item(container)
