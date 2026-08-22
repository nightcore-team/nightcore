"""
User list view v2 component.

Used for displaying a list of users with their stats by chosen criteria.
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING, Self

from discord import Color
from discord.ui import (
    Container,
    LayoutView,
    Separator,
    TextDisplay,
)

if TYPE_CHECKING:
    from src.infra.db.models import User

from src.nightcore.utils import format_voice_time


# TODO: change medals to one color
class UsersListViewV2(LayoutView):
    def __init__(
        self,
        coin_name: str | None,
        users: Sequence["User"],
        sort_by: str | None = None,
    ) -> None:
        super().__init__(timeout=None)

        medals = {
            1: "<:4210goldmedal:1442921281443069972>",
            2: "<:4823silvermedal:1442921153172607107>",
            3: "<:4210bronzemedal:1442921220172419194>",
        }

        container = Container[Self](accent_color=Color.from_str("#5EC9B3"))
        container.add_item(
            TextDisplay[Self](
                "## <:nightcoreInfo:1540439225877528626> Список пользователей"
            )
        )
        container.add_item(Separator[Self]())

        for index, user in enumerate(users, start=1):
            prefix = medals.get(index, f"`{index}.`")
            voice_activity_str = format_voice_time(user.voice_activity)

            match sort_by:
                case "sent":
                    container.add_item(
                        TextDisplay[Self](
                            f"{prefix} <@{user.user_id}> — "
                            f"**{user.sended_valentines}** отправленных валентинок"  # noqa: E501
                        )
                    )
                case "received":
                    container.add_item(
                        TextDisplay[Self](
                            f"{prefix} <@{user.user_id}> — "
                            f"**{user.received_valentines}** полученных валентинок"  # noqa: E501
                        )
                    )
                case "voice":
                    container.add_item(
                        TextDisplay[Self](
                            f"{prefix} <@{user.user_id}> — "
                            f"<:audiolines:1540403938782748693> **{voice_activity_str}**"  # noqa: E501
                        )
                    )
                case "coins":
                    container.add_item(
                        TextDisplay[Self](
                            f"{prefix} <@{user.user_id}> — "
                            f"<:nightcoreBanknote:1540403146072002624> **{user.coins:,}** {coin_name or 'коинов'}"  # noqa: E501
                        )
                    )
                case "level":
                    container.add_item(
                        TextDisplay[Self](
                            f"{prefix} <@{user.user_id}> — "
                            f"<:nightcoreLevelUp:1540402294275969024> **Уровень {user.level}** ({user.current_exp}/{user.exp_to_level} XP)"  # noqa: E501
                        )
                    )
                case "messages":
                    container.add_item(
                        TextDisplay[Self](
                            f"{prefix} <@{user.user_id}> — "
                            f"<:nightcoreMessage:1540403723342192810> **{user.messages_count:,}** сообщений"  # noqa: E501
                        )
                    )
                case "battlepass":
                    container.add_item(
                        TextDisplay[Self](
                            f"{prefix} <@{user.user_id}> — "
                            f"<:nightcoreBattlepass:1540406661146091590> **Уровень {user.battle_pass_level}** "  # noqa: E501
                        )
                    )
                case _:
                    container.add_item(
                        TextDisplay[Self](
                            f"<:42920arrowrightalt:1442924551880314921> <@{user.user_id}>\n"  # noqa: E501
                            f"> <:nightcoreLevelUp:1540402294275969024> **Уровень:** {user.level}\n"  # noqa: E501
                            f"> <:nightcoreBanknote:1540403146072002624> **Валюта:** {user.coins:,} {coin_name or 'коинов'}\n"  # noqa: E501
                            f"> <:nightcoreMessage:1540403723342192810> **Сообщения:** {user.messages_count:,}\n"  # noqa: E501
                            f"> <:audiolines:1540403938782748693> **Голосовая активность:** {voice_activity_str}"  # noqa: E501
                        )
                    )

        container.add_item(Separator[Self]())

        self.add_item(container)
