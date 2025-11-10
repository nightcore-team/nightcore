"""Command to get stats for a moderator."""

import logging
from typing import TYPE_CHECKING, cast

import discord
from discord import Guild, Member, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.infra.db.models import GuildModerationConfig
from src.infra.db.models._annot import ModerationInfractionsDataAnnot
from src.infra.db.operations import get_moderation_stats, get_moderstats_dict
from src.infra.db.utils import group_infractions_by_moderator
from src.nightcore.components.embed import (
    ErrorEmbed,
    ValidationErrorEmbed,
)
from src.nightcore.exceptions import FieldNotConfiguredError
from src.nightcore.features.moderation.components.v2.view.getmoderstats import (  # noqa: E501
    MultiplyGetModerStatsViewV2,
    SingleGetModerStatsViewV2,
)
from src.nightcore.features.moderation.utils.getmoderstats import (
    ModerationScores,
    build_moderstats_pages,
    calculate_all_moderators_stats,
)
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils import (
    get_all_members_with_specified_role,
    has_any_role,
)
from src.nightcore.utils.time_utils import compare_date_range

from src.nightcore.utils.permissions import check_required_permissions, PermissionsFlagEnum

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


class GetModerationStats(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

    @app_commands.command( # type: ignore
        name="getmoderstats", description="Получить статистику модерации"
    )
    @app_commands.describe(
        user="Пользователь для получения статистики",
        from_date="Дата начала.",
        to_date="Дата окончания.",
        ephemeral="Скрыть ответ от других пользователей. По умолчанию: True",
    )
    @check_required_permissions(PermissionsFlagEnum.MODERATION_ACCESS) # type: ignore
    async def getmoderstats(
        self,
        interaction: Interaction,
        user: Member | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        ephemeral: bool = True,
    ):
        """Get moderation stats for a user."""
        guild = cast(Guild, interaction.guild)

        member = None
        if user:
            member = user

        try:
            from_dt, to_dt = compare_date_range(from_date, to_date)
        except ValueError as e:
            return await interaction.response.send_message(
                embed=ValidationErrorEmbed(
                    str(e),
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        outcome = ""
        trackable_moderation_role: int = 0
        grouped: dict[int, ModerationInfractionsDataAnnot] = {}
        scores: dict[str, float] = {}

        async with specified_guild_config(
            self.bot,
            guild.id,
            GuildModerationConfig,
        ) as (guild_config, session):
            trackable_moderation_role = (
                guild_config.trackable_moderation_role_id
            )  # type: ignore

            if not trackable_moderation_role:
                outcome = "no_trackable_moderation_role"
            else:
                scores = await get_moderstats_dict(session, guild_id=guild.id)

        if outcome == "no_trackable_moderation_role":
            raise FieldNotConfiguredError("отслеживаемая роль модерации")

        moderators: list[discord.Member] = []
        if member:
            is_member_moderator = has_any_role(
                member, trackable_moderation_role
            )
            if is_member_moderator:
                moderators.append(member)
            else:
                return await interaction.response.send_message(
                    embed=ValidationErrorEmbed(
                        "Этот пользователь не является модератором для получения статистики.",  # noqa: E501
                        self.bot.user.name,  # type: ignore
                        self.bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )
        else:
            moderators = await get_all_members_with_specified_role(  # type: ignore
                guild, trackable_moderation_role
            )

        if not moderators:
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка получения статистики.",
                    "Не удалось найти модераторов с отслеживаемой ролью.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        await interaction.response.defer(ephemeral=ephemeral)

        data_range_diff = (to_dt - from_dt).days

        async with self.bot.uow.start() as session:
            if data_range_diff > 60:
                clear_stats = await get_moderation_stats(
                    session,
                    guild_id=guild.id,
                    moderators={m.id: m.nick for m in moderators},  # type: ignore
                    from_date=from_dt,
                    to_date=to_dt,
                )
            else:
                clear_stats = await get_moderation_stats(
                    session,
                    guild_id=guild.id,
                    moderators={m.id: m.nick for m in moderators},  # type: ignore
                    from_date=from_dt,
                    to_date=to_dt,
                    with_messages=True,
                )

        grouped = group_infractions_by_moderator(
            moderators=clear_stats["moderators"],
            punishments=clear_stats["punishments"],
            tickets=clear_stats["tickets"],
            role_requests=clear_stats["role_requests"],
            changestats=clear_stats["changestats"],
            messages=clear_stats["messages"],
        )

        mod_scores = ModerationScores.from_dict(scores)
        stats = calculate_all_moderators_stats(grouped)

        view: SingleGetModerStatsViewV2 | MultiplyGetModerStatsViewV2

        match len(stats):
            case 0:
                return await interaction.followup.send(
                    embed=ErrorEmbed(
                        "Ошибка получения статистики.",
                        "Не удалось найти статистику модерации за указанный период.",  # noqa: E501
                        self.bot.user.name,  # type: ignore
                        self.bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )
            case 1:
                view = SingleGetModerStatsViewV2(
                    self.bot,
                    from_dt=from_dt,
                    to_dt=to_dt,
                    moderator=moderators[0],
                    mod_score=mod_scores,
                    stats=stats[moderators[0].id],
                )

            case _:
                pages = build_moderstats_pages(
                    stats, mod_scores, moderators_per_page=3
                )

                view = MultiplyGetModerStatsViewV2(
                    self.bot,
                    author_id=interaction.user.id,
                    pages=pages,
                    scores=mod_scores,
                    from_dt=from_dt,
                    to_dt=to_dt,
                )

        await interaction.followup.send(view=view)


async def setup(bot: "Nightcore"):
    """Setup the GetModerationStats cog."""
    await bot.add_cog(GetModerationStats(bot))
