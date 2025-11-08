"""Get single moderator stats view v2 component."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Self

import discord
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
    from src.nightcore.features.moderation.utils.getmoderstats import (
        ModerationScores,
    )
    from src.nightcore.features.moderation.utils.getmoderstats._types import (
        ModeratorStats,
    )

from src.nightcore.utils import discord_ts


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

        container = Container[Self](accent_color=Color.from_str("#9300d2"))
        container.add_item(
            Section[Self](
                TextDisplay[Self](
                    "## <:96965manager:1436470131034427423> Статистика модератора\n"  # noqa: E501
                    f"**Модератор:** {moderator.mention} (`{moderator.id}`)\n"
                    f"**Количество баллов:** {stats.calculate_total_points(mod_score)}\n"  # noqa: E501
                    f"> **Количество снятых баллов:** {stats.deducted_points}\n"  # noqa: E501
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
                f"### Изменение статистики\n{stats.format_changestat_history()}"  # noqa: E501
            )
        )
        container.add_item(Separator[Self]())

        now = discord.utils.utcnow()

        container.add_item(
            TextDisplay[Self](
                f"-# From {discord_ts(from_dt)} to {discord_ts(to_dt)}\n"
                f"-# Powered by {self.bot.user.name} in {discord_ts(now)}"  # type: ignore
            )
        )

        self.add_item(container)
