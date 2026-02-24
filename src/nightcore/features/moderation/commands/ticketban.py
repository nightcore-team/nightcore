"""Ticket ban command for the Nightcore bot."""

import logging
from datetime import UTC
from typing import TYPE_CHECKING, cast

import discord
from discord import Guild, Member, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.infra.db.operations import (
    get_moderation_access_roles,
    get_or_create_user,
    is_user_ticketbanned,
)
from src.nightcore.components.embed import (
    ErrorEmbed,
    ValidationErrorEmbed,
)
from src.nightcore.features.moderation.components.v2 import PunishViewV2
from src.nightcore.features.moderation.events import UserMutedEventData
from src.nightcore.features.moderation.utils.transformers import (
    StringToRuleTransformer,
)
from src.nightcore.utils import (
    has_any_role_from_sequence,
)
from src.nightcore.utils.time_utils import parse_duration

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

logger = logging.getLogger(__name__)


class Ticketban(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

    @app_commands.command(  # type: ignore
        name="ticketban",
        description="Заблокировать пользователю создание тикетов",
    )
    @app_commands.describe(
        user="Пользователь для блокировки",
        reason="Причина блокировки",
        duration="Длительность блокировки",
    )
    @app_commands.guild_only()
    @check_required_permissions(PermissionsFlagEnum.MODERATION_ACCESS)  # type: ignore
    async def ticketban(
        self,
        interaction: Interaction,
        user: Member,
        duration: str,
        reason: app_commands.Transform[
            app_commands.Range[str, 1, 1000], StringToRuleTransformer
        ],
    ):
        """Ban a user from creating tickets."""
        guild = cast(Guild, interaction.guild)

        # Ensure we have a guild Member object
        member = user

        outcome = ""

        if guild.me == member:
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка блокировки",
                    "Вы не можете заблокировать меня.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        parsed_duration = parse_duration(duration)

        if not parsed_duration:
            return await interaction.response.send_message(
                embed=ValidationErrorEmbed(
                    "Неверная продолжительность. Используйте s/m/h/d (например, 1h, 1d, 7d).",  # noqa: E501
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        try:
            async with self.bot.uow.start() as session:
                moderation_access_roles = await get_moderation_access_roles(
                    session, guild_id=guild.id
                )

                is_member_moderator = has_any_role_from_sequence(
                    member, moderation_access_roles
                )
                if is_member_moderator:
                    outcome = "cannot_punish_moderator"
                else:
                    u, _ = await get_or_create_user(
                        session, guild_id=guild.id, user_id=member.id
                    )
                    if u.ticket_ban or await is_user_ticketbanned(
                        session, guild_id=guild.id, user_id=member.id
                    ):
                        outcome = "already_punisned"
                    else:
                        u.ticket_ban = True
        except Exception as e:
            logger.error(
                "Failed to ticketban user %s in guild %s: %s",
                user.id,
                guild.id,
                e,
            )

            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка блокировки тикетов",
                    "Не удалось заблокировать пользователя.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                )
            )

        if outcome == "cannot_punish_moderator":
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка блокировки",
                    "Вы не можете заблокировать модераторов.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if outcome == "already_punisned":
            return await interaction.response.send_message(
                embed=ValidationErrorEmbed(
                    "Этот пользователь уже имеет блокировку на создание тикетов.",  # noqa: E501
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        await interaction.response.defer()

        try:
            self.bot.dispatch(
                "user_ticketbanned",
                data=UserMutedEventData(
                    mode="dm",
                    category=self.__class__.__name__.lower(),
                    moderator=interaction.user,  # type: ignore
                    user=member,
                    reason=reason,
                    created_at=discord.utils.utcnow().astimezone(tz=UTC),
                    guild_name=guild.name,
                    duration=parsed_duration,
                    original_duration=duration,
                ),
            )
        except Exception as e:
            logger.exception(
                "[event] - Failed to dispatch user_muted event: %s", e
            )
            return

        await interaction.followup.send(
            view=PunishViewV2(
                bot=self.bot,
                user=member,
                punish_type="ticketban",
                moderator_id=interaction.user.id,  # type: ignore
                reason=reason,
                duration=duration,
                mode="server",
            )
        )

        logger.info(
            "[command] - invoked user=%s guild=%s target=%s reason=%s duration=%s",  # noqa: E501
            interaction.user.id,
            guild.id,
            user.id,
            reason,
            duration,
        )


async def setup(bot: "Nightcore"):
    """Setup the Ticketban cog."""
    await bot.add_cog(Ticketban(bot))
