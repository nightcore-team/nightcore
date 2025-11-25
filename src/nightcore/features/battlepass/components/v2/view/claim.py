"""
Battlepass claim view v2 component.

Used for displaying user's battlepass information with info/claim buttons.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Self

from discord import ButtonStyle, Color
from discord.ui import (
    Button,
    Container,
    LayoutView,
    Section,
    Separator,
    TextDisplay,
    Thumbnail,
)

from src.nightcore.utils import discord_ts

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


class BattlepassClaimViewV2(LayoutView):
    def __init__(
        self,
        bot: "Nightcore",
        level: int,
        total_levels: int,
        current_points: int,
        required_points: int,
        reward_type: str,
        reward_amount: int,
        avatar_url: str,
        disable_button: bool = False,
    ) -> None:
        super().__init__(timeout=180)

        container = Container[Self](accent_color=Color.from_str("#b777a6"))

        container.add_item(
            Section[Self](
                TextDisplay[Self](
                    "## <:9057saturn:1442919302587093072> Battlepass\n"
                    f"**Общее количество уровней**: {total_levels}\n"
                    "> Для повышения уровня активно общайтесь на нашем сервере <:heartt:1442919985004544011>"  # noqa: E501
                ),
                accessory=Thumbnail[Self](media=f"{avatar_url}"),
            )
        )
        container.add_item(Separator[Self]())

        info_button = Button[Self](
            label="Информация",
            style=ButtonStyle.secondary,
            emoji="<:5730galaxy:1442918999036793045>",
            custom_id="battlepass:info",
        )

        container.add_item(
            Section[Self](
                TextDisplay[Self](
                    f"Ваш текущий уровень: **{level}**\n"
                    f"Прогресс: **`{current_points} / {required_points}` BP points**\n\n"  # noqa: E501
                ),
                accessory=info_button,
            )
        )

        claim_reward_button = Button[Self](
            label="Забрать награду",
            style=ButtonStyle.secondary,
            # emoji="<:5730galaxy:1442918999036793045>",
            custom_id="battlepass:claim_reward",
            disabled=disable_button,
        )
        container.add_item(
            Section[Self](
                TextDisplay[Self](
                    f"<:48765whitearrow:1442918703367983225> **Награда за уровень: {reward_type}, {reward_amount}**"  # noqa: E501
                ),
                accessory=claim_reward_button,
            )
        )
        container.add_item(Separator[Self]())

        now = datetime.now(timezone.utc)
        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {bot.user.name} in {discord_ts(now)}\n"  # type: ignore
            )
        )

        self.add_item(container)
