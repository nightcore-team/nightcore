"""Clan info view v2."""

from collections.abc import Sequence
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Self

from discord.ui import (
    Container,
    LayoutView,
    Separator,
    TextDisplay,
)

from src.infra.db.models import User

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.utils import discord_ts, format_voice_time


class UsersListViewV2(LayoutView):
    def __init__(
        self,
        bot: "Nightcore",
        coin_name: str,
        users: Sequence[User],
        sort_by: str | None = None,
    ) -> None:
        super().__init__(timeout=180)

        medals = {
            1: "<:4210goldmedal:1433144436744785992>",
            2: "<:4823silvermedal:1433144438846259412>",
            3: "<:4210bronzemedal:1433144435201544203>",
        }

        container = Container[Self]()
        container.add_item(
            TextDisplay[Self](
                "## <:32451information:1430231400208011428> Список пользователей"  # noqa: E501
            )
        )
        container.add_item(Separator[Self]())

        for index, user in enumerate(users, start=1):
            prefix = medals.get(index, f"`{index}.`")
            voice_activity_str = format_voice_time(user.voice_activity)

            match sort_by:
                case "voice":
                    container.add_item(
                        TextDisplay[Self](
                            f"{prefix} <@{user.user_id}> — "
                            f"**{voice_activity_str}**"
                        )
                    )
                case "coins":
                    container.add_item(
                        TextDisplay[Self](
                            f"{prefix} <@{user.user_id}> — "
                            f"**{user.coins:,}** {coin_name}"
                        )
                    )
                case "level":
                    container.add_item(
                        TextDisplay[Self](
                            f"{prefix} <@{user.user_id}> — "
                            f"**Уровень {user.level}** ({user.current_exp}/{user.exp_to_level} XP)"  # noqa: E501
                        )
                    )
                case "messages":
                    container.add_item(
                        TextDisplay[Self](
                            f"{prefix} <@{user.user_id}> — "
                            f"**{user.messages_count:,}** сообщений"
                        )
                    )
                case _:
                    container.add_item(
                        TextDisplay[Self](
                            f"<:42920arrowrightalt:1421170550759489616> <@{user.user_id}>\n"  # noqa: E501
                            f"> **Уровень:** {user.level}\n"
                            f"> **Баланс:** {user.coins:,} {coin_name}\n"
                            f"> **Сообщения:** {user.messages_count:,}\n"
                            f"> **Голосовая активность:** {voice_activity_str}"
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
