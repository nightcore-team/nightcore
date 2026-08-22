"""Get single moderator stats view v2 component."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Self, cast

import discord
from discord import ButtonStyle, Color
from discord.interactions import Interaction
from discord.ui import (
    ActionRow,
    Button,
    Container,
    LayoutView,
    Section,
    Separator,
    TextDisplay,
    Thumbnail,
    button,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore
    from src.nightcore.features.moderation.utils.getmoderstats import (
        ModerationScores,
    )
    from src.nightcore.features.moderation.utils.getmoderstats._types import (
        ModeratorStats,
    )

from src.nightcore.utils import discord_ts


class ChangeStatDetailsActionRow(ActionRow["SingleGetModerStatsViewV2"]):
    def __init__(self) -> None:
        super().__init__()

    @button(
        label="История изменений статистики",
        custom_id="change_stat_details:get",
        style=ButtonStyle.grey,
        emoji="<:nightcoreChangeStat:1540741425539321977>",
    )
    async def get_change_stat_details(
        self,
        interaction: Interaction[Nightcore],
        button: Button[SingleGetModerStatsViewV2],
    ) -> None:
        """Handle get change stat details button click."""
        view = cast(SingleGetModerStatsViewV2, self.view)
        stats = view.stats
        if not stats.changestat_details:
            await interaction.response.send_message(
                "Деталей изменений статистики нет.", ephemeral=True
            )
            return

        details = stats.format_changestats_history()
        await interaction.response.send_message(
            view=ChangeStatDetailsViewV2(
                bot=view.bot,
                moderator=view.moderator,
                stats=stats,
                details=details,
            ),
            ephemeral=True,
        )


class ChangeStatDetailsViewV2(LayoutView):
    def __init__(
        self,
        bot: Nightcore,
        moderator: discord.Member,
        stats: ModeratorStats,
        details: str,
    ):
        super().__init__(timeout=None)

        container = Container[Self](accent_color=Color.from_str("#C0577A"))
        container.add_item(
            Section[Self](
                TextDisplay[Self](
                    f"## <:nightcoreChangeStat:1540741425539321977> Изменения статистики\n**Модератор:** {moderator.mention}\n**Количество изменений:** {len(stats.changestat_details)}"  # noqa: E501
                ),
                accessory=Thumbnail[Self](moderator.display_avatar.url),
            )
        )
        container.add_item(Separator[Self]())

        container.add_item(TextDisplay[Self](f"{details}"))

        self.add_item(container)


class SingleGetModerStatsViewV2(LayoutView):
    def __init__(
        self,
        bot: Nightcore,
        from_dt: datetime,
        to_dt: datetime,
        moderator: discord.Member,
        mod_score: ModerationScores,
        stats: ModeratorStats,
    ):
        super().__init__(timeout=None)
        self.bot = bot
        self.moderator = moderator
        self.mod_score = mod_score
        self.stats = stats

        container = Container[Self](accent_color=Color.from_str("#C0577A"))
        container.add_item(
            Section[Self](
                TextDisplay[Self](
                    "## <:nightcoreModerator:1540734534423805952> Статистика модератора\n"  # noqa: E501
                    f"**Модератор:** {moderator.mention} (`{moderator.id}`)\n"
                    f"**Количество баллов:** {stats.calculate_total_points(mod_score)}\n"  # noqa: E501
                    f"> **Количество {'добавленных' if stats.deducted_points >= 0 else 'снятых'} баллов:** {stats.deducted_points}\n"  # noqa: E501
                ),
                accessory=Thumbnail[Self](moderator.display_avatar.url),
            )
        )
        container.add_item(Separator[Self]())

        container.add_item(
            TextDisplay[Self](
                "### Количество выданных наказаний:\n" + stats.format_stats()
            )
        )
        container.add_item(Separator[Self]())

        container.add_item(
            TextDisplay[Self](
                f"### Изменения статистики\n{stats.format_changestat_history_first_5()}\n"  # noqa: E501
            )
        )
        if stats.changestat_details and len(stats.changestat_details) > 5:
            container.add_item(
                TextDisplay[Self](
                    "<:nightcoreArrowRightRed:1540735601089847296> *Остальные записи доступны по кнопке ниже*"  # noqa: E501
                )
            )
            container.add_item(Separator[Self]())
            container.add_item(ChangeStatDetailsActionRow())
            container.add_item(Separator[Self]())
        else:
            container.add_item(Separator[Self]())

        container.add_item(
            TextDisplay[Self](
                f"-# From {discord_ts(from_dt)} to {discord_ts(to_dt)}"
            )
        )

        self.add_item(container)
