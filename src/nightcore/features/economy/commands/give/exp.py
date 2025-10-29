"""Give user experience command."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, Member, app_commands
from discord.interactions import Interaction

from src.infra.db.models import GuildEconomyConfig, GuildLoggingConfig
from src.infra.db.models._enums import ChannelType
from src.infra.db.operations import get_or_create_user, get_specified_channel
from src.nightcore.components.embed import (
    ErrorEmbed,
    MissingPermissionsEmbed,
    SuccessMoveEmbed,
)
from src.nightcore.exceptions import FieldNotConfiguredError
from src.nightcore.features.economy._groups import give as give_group
from src.nightcore.features.economy.events.dto import (
    AwardNotificationEventDTO,
)
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils import has_any_role_from_sequence

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


@give_group.command(name="exp", description="Give experience to user.")
@app_commands.describe()
async def give_exp(
    interaction: Interaction["Nightcore"],
    user: Member,
    amount: int,
):
    """Give experience to a user."""

    guild = cast(Guild, interaction.guild)
    bot = interaction.client

    outcome = ""

    if user == bot.user:
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка выдачи опыта",
                "Невозможно выдать опыт боту.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    async with specified_guild_config(
        bot, guild_id=guild.id, config_type=GuildEconomyConfig
    ) as (guild_config, session):
        economy_access_roles_ids = guild_config.economy_access_roles_ids

        logging_channel_id = await get_specified_channel(
            session,
            guild_id=guild.id,
            config_type=GuildLoggingConfig,
            channel_type=ChannelType.LOGGING_ECONOMY,
        )

        if not economy_access_roles_ids:
            raise FieldNotConfiguredError("economy access")

        if not has_any_role_from_sequence(
            cast(Member, interaction.user), economy_access_roles_ids
        ):
            outcome = "missing_permissions"

        if not outcome:
            try:
                user_record, _ = await get_or_create_user(
                    session, guild_id=guild.id, user_id=user.id
                )
                user_record.current_exp += amount
                outcome = "success"
            except Exception as e:
                logger.exception(
                    "[give/exp] Failed to give experience to user %s in guild %s: %s",  # noqa: E501
                    user.id,
                    guild.id,
                    e,
                )
                outcome = "give_exp_error"

    if outcome == "give_exp_error":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка выдачи опыта",
                "Не удалось выдать опыт пользователю.",  # noqa: RUF001
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "missing_permissions":
        return await interaction.response.send_message(
            embed=MissingPermissionsEmbed(
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "success":
        await interaction.response.send_message(
            embed=SuccessMoveEmbed(
                "Выдача опыта успешна",
                f"Вы успешно выдали пользователю <@{user.id}> "
                f"**{amount} опыта**.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

        bot.dispatch(
            "user_items_changed",
            dto=AwardNotificationEventDTO(
                guild=guild,
                event_type="give_exp",
                logging_channel_id=logging_channel_id,
                user_id=user.id,
                moderator_id=interaction.user.id,
                item_name="опыт",
                amount=amount,
            ),
        )
