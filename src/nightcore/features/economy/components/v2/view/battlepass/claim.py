"""
Battlepass claim view v2 component.

Used for displaying user's battlepass information with info/claim buttons.
"""

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
        additional_reward_type: str | None = None,
        additional_reward_amount: int | None = None,
        additional_reward_access_vip_id: int | None = None,
        user_vip_ids: list[int] | None = None,
        additional_reward_claimed: bool = False,
    ) -> None:
        super().__init__(timeout=None)

        container = Container[Self](accent_color=Color.from_str("#5EC9B3"))

        container.add_item(
            Section[Self](
                TextDisplay[Self](
                    "## <:nightcoreBattlepass:1540406661146091590> Battlepass\n"  # noqa: E501
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
            emoji="<:nightcoreGem:1540406663377453097>",
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
            style=ButtonStyle.grey,
            # emoji="<:5730galaxy:1442918999036793045>",
            custom_id="battlepass:claim_reward",
            disabled=disable_button,
        )
        container.add_item(
            Section[Self](
                TextDisplay[Self](
                    f"<:nightcoreArrowRightCyan:1540434390780477551> **Награда за уровень: {reward_type}, {reward_amount}**"  # noqa: E501
                ),
                accessory=claim_reward_button,
            )
        )
        container.add_item(Separator[Self]())

        if (
            additional_reward_access_vip_id is not None
            and user_vip_ids is not None
            and additional_reward_access_vip_id in user_vip_ids
            and additional_reward_type
            and additional_reward_amount
        ):
            claim_additional_reward_button = Button[Self](
                label="Награда получена"
                if additional_reward_claimed
                else "Забрать награду",
                style=ButtonStyle.success
                if additional_reward_claimed
                else ButtonStyle.grey,
                # emoji="<:5730galaxy:1442918999036793045>",
                custom_id="battlepass:claim_additional_reward",
                disabled=disable_button or additional_reward_claimed,
            )
            container.add_item(
                Section[Self](
                    TextDisplay[Self](
                        f"<:nightcoreArrowRightCyan:1540434390780477551> **Дополнительная награда за уровень: {additional_reward_type}, {additional_reward_amount}**"  # noqa: E501
                    ),
                    accessory=claim_additional_reward_button,
                )
            )

        self.add_item(container)
