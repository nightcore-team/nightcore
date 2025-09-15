"""Get moderation stats command for the Nightcore bot."""

import logging
from typing import cast

import discord
from discord import Guild, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.infra.db.models import GuildModerationConfig
from src.infra.db.operations import get_user_infractions_for_moderators
from src.nightcore.bot import Nightcore
from src.nightcore.components.embed import (
    EntityNotFoundEmbed,
    ErrorEmbed,
    MissingPermissionsEmbed,
    ValidationErrorEmbed,
)
from src.nightcore.exceptions import FieldNotConfiguredError
from src.nightcore.features.moderation.components.view import (
    GetModerationStatsView,
)
from src.nightcore.features.moderation.utils import (
    build_moderators_stats,
    build_moderstats_pages,
    compare_date_range,
)
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils import (
    ensure_member_exists,
    get_all_members_with_specified_role,
    has_any_role,
    has_any_role_from_sequence,
)

logger = logging.getLogger(__name__)


# TODO: add field if moderator fullfied the norm
class GetModerationStats(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @app_commands.command(
        name="getmoderstats", description="Get moderation stats for a user"
    )
    @app_commands.describe(
        user="The user to get stats for",
        from_date="The start date.",
        to_date="The end date.",
        ephemeral="Whether the response should be ephemeral",
    )
    async def getmoderstats(
        self,
        interaction: Interaction,
        user: discord.User | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        ephemeral: bool = True,
    ):
        """Get moderation stats for a user."""
        guild = cast(Guild, interaction.guild)

        # Ensure we have a guild Member object
        member = None
        if user:
            member = await ensure_member_exists(guild, user.id)

            if not member:
                return await interaction.response.send_message(
                    embed=EntityNotFoundEmbed(
                        "Member",
                        self.bot.user.name,  # type: ignore
                        self.bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )

        # Parse dates
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

        async with specified_guild_config(
            self.bot,
            guild.id,
            GuildModerationConfig,
            _create=False,
        ) as (guild_config, session):
            if not (
                moderation_access_roles
                := guild_config.moderation_access_roles_ids
            ):
                raise FieldNotConfiguredError("moderation access")

            if not (
                trackable_moderation_role
                := guild_config.trackable_moderation_role_id
            ):
                raise FieldNotConfiguredError("global moderation role")

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
                            "This user is not a moderator to get stats for.",
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
                        "Get Moderation Stats Error.",
                        "No moderators found.",
                        self.bot.user.name,  # type: ignore
                        self.bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )

            infractions = await get_user_infractions_for_moderators(
                session,
                guild_id=guild.id,
                moderators={m.id: m.nick for m in moderators},  # type: ignore
                from_date=from_dt,
                to_date=to_dt,
            )

            total_messages = None

        has_moder_role = has_any_role_from_sequence(
            cast(discord.Member, interaction.user), moderation_access_roles
        )
        if not has_moder_role:
            return await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if guild.me == member:
            return await interaction.response.send_message(
                embed=ValidationErrorEmbed(
                    "You cannot get stats for me.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        await interaction.response.defer(ephemeral=ephemeral)

        stats = build_moderators_stats(
            infractions=infractions,  # type: ignore
            mute_score=guild_config.mute_score or 0,
            ban_score=guild_config.ban_score or 0,
            kick_score=guild_config.kick_score or 0,
            vmute_score=guild_config.vmute_score or 0,
            mpmute_score=guild_config.mpmute_score or 0,
            ticketban_score=guild_config.ticket_ban_score or 0,
            tickets_score=guild_config.ticket_score or 0,
            approved_role_requests_score=(
                guild_config.role_request_score or 0
            ),
            changed_roles_score=guild_config.role_remove_score or 0,
            message_score=guild_config.message_score or 0,
            total_messages=total_messages or 0,
        )

        pages = build_moderstats_pages(stats)

        embed = discord.Embed(
            title=f"Moderation stats from {from_dt.date()} to {to_dt.date()}",
            color=discord.Color.blurple(),
        )

        for p in pages[0]:
            for v in p.values():
                embed.add_field(
                    name=v.get("nickname"),
                    value=v.get("stats"),
                    inline=True,
                )

        embed.set_footer(
            text=f"Page 1 / {len(pages)}",
            icon_url=self.bot.user.display_avatar.url,  # type: ignore
        )

        if len(pages) == 1:
            return await interaction.followup.send(embed=embed)

        view = GetModerationStatsView(
            interaction.user.id,
            pages=pages,
            from_date=from_dt,
            to_date=to_dt,
            bot=self.bot,
        )

        await interaction.followup.send(embed=embed, view=view)

        logger.info(
            "[command] - invoked user=%s guild=%s target=%s",
            interaction.user.id,
            guild.id,
            member.id if member else "all",
        )


async def setup(bot: Nightcore):
    """Setup the GetModerationStats cog."""
    await bot.add_cog(GetModerationStats(bot))
