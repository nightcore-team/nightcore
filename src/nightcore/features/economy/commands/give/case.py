"""Command to give a case to a user."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, User, app_commands
from discord.interactions import Interaction
from sqlalchemy.orm import attributes

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

from src.nightcore.utils.permissions import PermissionsFlagEnum, check_required_permissions

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


@give_group.command(name="case", description="Выдать пользователю кейс") # type: ignore
@app_commands.describe(
    user="Пользователь, которому выдается кейс.",
    case="Кейс для выдачи.",
    amount="Количество кейсов для выдачи.",
)
@app_commands.choices(
    case=[
        app_commands.Choice(name="Кейс с монетами", value="coins_case"),
        app_commands.Choice(name="Кейс с цветами", value="colors_case"),
    ]
)
@check_required_permissions(PermissionsFlagEnum.ECONOMY_ACCESS)
async def give_case(
    interaction: Interaction["Nightcore"],
    user: User,
    case: app_commands.Choice[str],
    amount: int,
):
    """Give a case to user."""

    guild = cast(Guild, interaction.guild)
    bot = interaction.client


    if user == bot.user:
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка выдачи кейса",
                "Невозможно выдать кейс боту.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    outcome = ""
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
                    session,
                    guild_id=guild.id,
                    user_id=user.id,
                )

                if case.value in user_record.inventory["cases"]:
                    user_record.inventory["cases"][case.value] += amount
                else:
                    user_record.inventory["cases"][case.value] = amount

                attributes.flag_modified(user_record, "inventory")

                outcome = "success"

            except Exception as e:
                logger.exception(
                    "[give/case] Error giving case %s to user %s in guild %s: %s",  # noqa: E501
                    case,
                    user.id,
                    guild.id,
                    e,
                )
                outcome = "give_case_error"

    if outcome == "give_case_error":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка выдачи кейса",
                "Не удалось выдать кейс пользователю.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "success":
        await interaction.response.send_message(
            embed=SuccessMoveEmbed(
                "Выдача кейса успешна",
                f"Вы успешно выдали пользователю <@{user.id}> "
                f"**{case.name}** в количестве **{amount}**.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

        bot.dispatch(
            "user_items_changed",
            dto=AwardNotificationEventDTO(
                guild=guild,
                event_type="give/case",
                logging_channel_id=logging_channel_id,
                user_id=user.id,
                moderator_id=interaction.user.id,
                item_name=case.name,
                amount=amount,
            ),
        )
