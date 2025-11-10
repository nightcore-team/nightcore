"""Command to give battlepass experience to a user."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, User, app_commands
from discord.interactions import Interaction

from src.infra.db.models import GuildEconomyConfig, GuildLoggingConfig
from src.infra.db.models._enums import ChannelType
from src.infra.db.operations import get_or_create_user, get_specified_channel
from src.nightcore.components.embed import (
    ErrorEmbed,
    SuccessMoveEmbed,
)
from src.nightcore.features.economy._groups import give as give_group
from src.nightcore.features.economy.events.dto import (
    AwardNotificationEventDTO,
)
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


@give_group.command(  # type: ignore
    name="bp_exp", description="Выдать очки батлпасса пользователю"
)
@check_required_permissions(PermissionsFlagEnum.ECONOMY_ACCESS)
@app_commands.describe()
async def give_bp_exp(
    interaction: Interaction["Nightcore"],
    user: User,
    amount: app_commands.Range[int, -50000, 50000],
):
    """Give battlepass experience to a user."""

    guild = cast(Guild, interaction.guild)
    bot = interaction.client

    outcome = ""

    if user == bot.user:
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка выдачи очков батлпасса",
                "Невозможно выдать очки батлпасса боту.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    async with specified_guild_config(
        bot, guild_id=guild.id, config_type=GuildEconomyConfig
    ) as (_, session):
        logging_channel_id = await get_specified_channel(
            session,
            guild_id=guild.id,
            config_type=GuildLoggingConfig,
            channel_type=ChannelType.LOGGING_ECONOMY,
        )

        if not outcome:
            try:
                user_record, _ = await get_or_create_user(
                    session, guild_id=guild.id, user_id=user.id
                )
                user_record.battle_pass_points += amount
                outcome = "success"

            except Exception as e:
                logger.exception(
                    "[give/bp_coins] Failed to give battlepass points to user %s in guild %s: %s",  # noqa: E501
                    user.id,
                    guild.id,
                    e,
                )
                outcome = "give_bp_coins_error"

    if outcome == "give_bp_coins_error":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка выдачи очков батлпасса",
                "Не удалось выдать очки батлпасса пользователю.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "success":
        await interaction.response.send_message(
            embed=SuccessMoveEmbed(
                "Выдача очков батлпасса успешна",
                f"Вы успешно выдали пользователю <@{user.id}> "
                f"**{amount} очков батлпасса**.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

        bot.dispatch(
            "user_items_changed",
            dto=AwardNotificationEventDTO(
                guild=guild,
                event_type="give/bp_exp",
                logging_channel_id=logging_channel_id,
                user_id=user.id,
                moderator_id=interaction.user.id,
                item_name="очки батлпасса",
                amount=amount,
            ),
        )
