"""
User profile view v2 component.

Used for displaying a user's profile with their stats, cases, and colors.
"""

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

from .transfer import TransferHistoryActionRow


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
        cases: CasesAnnot,
        colors: list[int],
    ):
        super().__init__(timeout=10)

        container = Container[Self](accent_color=Color.from_str("#515cff"))

        container.add_item(
            TextDisplay[Self](
                f"## <:butterflies:1442916105508360446> Профиль пользователя <@{user_id}>",  # noqa: E501
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
                    f"\n**Уровень баттлпаса:** {battlepass_level}",
                ),
                accessory=Thumbnail[Self](avatar_url),
            )
        )
        container.add_item(Separator[Self]())

        cases_with_items = {
            case_name: count
            for case_name, count in cases.items()
            if isinstance(count, int) and count > 0
        }

        if cases_with_items:
            container.add_item(
                TextDisplay[Self](
                    "### <a:68842universebox:1442920870996742275> Кейсы: "
                )
            )
            container.add_item(
                TextDisplay[Self](
                    "\n".join(
                        f"> {CASES_NAMES.get(case_name, case_name)}, количество: {count}"  # noqa: E501
                        for case_name, count in cases_with_items.items()
                    )
                )
            )
            container.add_item(Separator[Self]())

        if colors:
            container.add_item(
                TextDisplay[Self]("###<:palette:1442915900666679527> Цвета: ")
            )
            container.add_item(
                TextDisplay[Self](
                    "\n".join(f"> <@&{role_id}>" for role_id in colors)
                )
            )
            container.add_item(Separator[Self]())

        container.add_item(TransferHistoryActionRow(guild_id, user_id))
        container.add_item(Separator[Self]())

        now = datetime.now(timezone.utc)

        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {bot.user.name} in {discord_ts(now)}"  # type: ignore
            )
        )

        self.add_item(container)
