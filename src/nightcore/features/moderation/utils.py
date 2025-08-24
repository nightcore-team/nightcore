"""Utility functions for moderation commands."""

from collections.abc import Sequence
import logging
from datetime import datetime, timedelta, timezone
from typing import cast

import discord
from discord import Guild, Member, User, app_commands
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.db.models.punish import Punish
from src.infra.db.operations import get_fraction_roles
from src.nightcore.bot import Nightcore
from src.nightcore.features.moderation.components.embed.punish import (
    generate_dm_punish_embed,
    generate_log_punish_embed,
)

from src.config.config import config

logger = logging.getLogger(__name__)


_TIME_UNITS = {
    "s": 1,
    "m": 60,
    "h": 60 * 60,
    "d": 24 * 60 * 60,
    "w": 7 * 24 * 60 * 60,
}


def parse_duration(text: str) -> int | None:
    """Parse a duration string into total seconds."""
    if not text:
        return None

    text = text.strip().lower()

    if not text:
        return None

    if text.isdigit():
        return int(text)

    total = 0
    number_buf = ""
    for ch in text:
        if ch.isdigit():
            number_buf += ch
            continue
        if ch in _TIME_UNITS and number_buf:
            total += int(number_buf) * _TIME_UNITS[ch]
            number_buf = ""
        else:
            return None
    if number_buf:
        total += int(number_buf)

    return total if total > 0 else None


def calculate_end_time(s: str) -> datetime | None:
    """Calculate the end time based on the current time and duration in seconds."""  # noqa: E501

    duration = parse_duration(s)

    if not duration or duration <= 0:
        return None

    try:
        seconds = float(duration)
    except (ValueError, TypeError):
        return None

    return datetime.now(timezone.utc) + timedelta(seconds=seconds)


def compare_top_roles(guild: Guild, member: Member) -> bool:
    """Compares the top roles of the bot and a member to determine if the bot can kick the member."""  # noqa: E501
    if guild.owner_id == member.id:
        return False

    if not guild.me.roles:
        return False

    if not member.roles:
        return True

    bot_top_role = guild.me.top_role.position
    member_top_role = member.top_role.position

    return bot_top_role > member_top_role


async def send_punish_dm_message(
    bot: Nightcore,
    *,
    moderator: Member,
    user: User,
    punish_type: str,
    reason: str,
    end_time: datetime | None = None,
) -> None:
    """Send a DM to the user about their punishment."""
    embed = generate_dm_punish_embed(
        punish_type=punish_type,
        guild_name=moderator.guild.name,
        moderator=moderator,
        reason=reason,
        end_time=end_time,
        bot=bot,
    )
    try:
        await user.send(embed=embed)
        logger.info(
            "[event] - on_user_punish - %s: DM sent to %s",
            punish_type,
            user.id,
        )
    except Exception as e:
        logger.exception(
            "[event] - on_user_punish - %s: Failed to send DM to %s: %s",
            punish_type,
            user.id,
            e,
        )


async def send_punish_log(
    bot: Nightcore,
    *,
    channel_id: int,
    duration: str | None = None,
    punish_info: Punish,
) -> None:
    """Send a punishment log message to the specified logging channel."""

    channel = bot.get_channel(channel_id)

    if channel is None:
        try:
            channel = await bot.fetch_channel(channel_id)
        except discord.NotFound:
            logger.warning(
                "[event] on_user_punish - %s: logging channel %s not found",
                punish_info.category,
                channel_id,
            )
            return
        except discord.Forbidden:
            logger.warning(
                "[event] on_user_punish - %s: no permission for channel %s",
                channel_id,
            )
            return
        except discord.HTTPException as e:
            logger.error(
                "[event] on_user_punish - %s: HTTP error fetching channel %s: %s",  # noqa: E501
                punish_info.category,
                channel_id,
                e,
            )
            return

    if isinstance(channel, discord.ForumChannel):
        logger.info(
            "[event] on_user_punish - %s: forum channel %s, creating thread",
            punish_info.category,
            channel.id,
        )
        try:
            await channel.create_thread(
                name=f"Punish ({punish_info.category}): {punish_info.user_id}",
                content=f"User punished: {punish_info.user_id}\nReason: {punish_info.reason}",  # noqa: E501
            )
        except discord.DiscordException as e:
            logger.error(
                "[event] on_user_punish - %s: failed to create forum thread in %s: %s",  # noqa: E501
                punish_info.category,
                channel.id,
                e,
            )
        return

    if not isinstance(channel, discord.TextChannel | discord.Thread):
        logger.warning(
            "[event] on_user_punish - %s: channel %s not messageable (%s)",
            punish_info.category,
            channel.id,
            type(channel).__name__,
        )
        return

    try:
        await channel.send(
            embed=generate_log_punish_embed(
                bot=bot,
                punish_type=punish_info.category,
                moderator_id=punish_info.moderator_id,
                user_id=punish_info.user_id,
                reason=punish_info.reason,
                duration=duration,
                end_time=punish_info.end_time,
            )
        )
    except discord.HTTPException as e:
        logger.error(
            "[event] on_user_punish - %s: failed to send message to %s: %s",
            punish_info.category,
            channel.id,
            e,
        )


async def fraction_roles_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    """Autocomplete function to get fraction roles for the guild."""
    guild = cast(Guild, interaction.guild)

    async with cast(Nightcore, interaction.client).uow.start() as uow:
        roles = await get_fraction_roles(
            cast(AsyncSession, uow.session), guild_id=guild.id
        )

    result: list[app_commands.Choice[str]] = []
    for role_id in roles:
        role = guild.get_role(role_id)
        if role is None:
            logger.warning(
                "[event] fraction_roles_autocomplete - %s: role %s not found",
                guild.id,
                role_id,
            )
            continue

        result.append(app_commands.Choice(name=role.name, value=str(role.id)))

    return result


def build_pages(
    punishments: Sequence[Punish],
    guild_id: int,
    notify_channel_id: int | None = None,
) -> list[str]:
    """Build paginated description pages for infractions."""
    pages: list[str] = []
    current = ""

    for p in punishments:
        time_now = int(p.time_now.timestamp())
        line = f"**`[{p.category.upper()}]` | <t:{time_now}:F> "

        if p.duration:
            line += f"| {p.duration} "

        if p.reason:
            if p.category == "notify" and notify_channel_id:
                line += f"| [notify](https://discord.com/channels/{guild_id}/{notify_channel_id}"
            else:
                line += f"| {p.reason} "
        line += f"||**<@{p.moderator_id}>\n"

        # Перевірка ліміту
        if len(current) + len(line) > config.bot.EMBED_DESCRIPTION_LIMIT:
            pages.append(current)
            current = ""
        current += line

    if current:
        pages.append(current)

    if not pages:
        pages = ["No infractions."]

    return pages
