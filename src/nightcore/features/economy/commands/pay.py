"""Command to pay another user."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, User, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.infra.db.models import GuildEconomyConfig, GuildLoggingConfig
from src.infra.db.models._enums import ChannelType
from src.infra.db.operations import get_or_create_user, get_specified_channel
from src.nightcore.components.embed import (
    EntityNotFoundEmbed,
    ErrorEmbed,
    SuccessMoveEmbed,
    ValidationErrorEmbed,
)
from src.nightcore.features.economy.events.dto import TransferCoinsEventDTO
from src.nightcore.services.config import specified_guild_config

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.utils import ensure_member_exists
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

logger = logging.getLogger(__name__)


class Pay(Cog):
    def __init__(self, bot: "Nightcore"):
        self.bot = bot

    @app_commands.command(name="pay", description="Отправить перевод коинов")  # type: ignore
    @app_commands.describe(
        user="Пользователь, которому нужно отправить перевод",
        amount="Сумма коинов для перевода",
        comment="Комментарий к переводу",
    )
    @app_commands.guild_only()
    @check_required_permissions(PermissionsFlagEnum.NONE)  # type: ignore
    async def pay(
        self,
        interaction: Interaction,
        user: User,
        amount: int,
        comment: app_commands.Range[str, 0, 200] | None = None,
    ):
        """Check user's balance."""

        guild = cast(Guild, interaction.guild)

        if amount <= 0:
            return await interaction.response.send_message(
                embed=ValidationErrorEmbed(
                    "Сумма должна быть положительным числом.",
                    self.bot.user.display_name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )
        if user == self.bot.user:
            return await interaction.response.send_message(
                embed=ValidationErrorEmbed(
                    "Вы не можете перевести коинов боту.",
                    self.bot.user.display_name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if user == interaction.user:
            return await interaction.response.send_message(
                embed=ValidationErrorEmbed(
                    "Вы не можете перевести коинов самому себе.",
                    self.bot.user.display_name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        member = await ensure_member_exists(guild, user.id)
        if not member:
            return await interaction.response.send_message(
                embed=EntityNotFoundEmbed(
                    "пользователь",
                    self.bot.user.display_name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        outcome = ""
        async with specified_guild_config(
            self.bot, guild_id=guild.id, config_type=GuildEconomyConfig
        ) as (
            guild_config,
            session,
        ):
            logging_channel_id = await get_specified_channel(
                session,
                guild_id=guild.id,
                config_type=GuildLoggingConfig,
                channel_type=ChannelType.LOGGING_ECONOMY,
            )

            coin_name = guild_config.coin_name

            sender, created = await get_or_create_user(
                session,
                guild_id=guild.id,
                user_id=interaction.user.id,
            )
            if created:
                outcome = "user_dont_have_enough_coins"

            receiver, _ = await get_or_create_user(
                session,
                guild_id=guild.id,
                user_id=member.id,
            )

            if not coin_name:
                outcome = "coin_name_not_configured"

            if not outcome:
                if sender.coins < amount:
                    outcome = "user_dont_have_enough_coins"
                else:
                    sender.coins -= amount
                    receiver.coins += amount
                    outcome = "success"

        if outcome == "coin_name_not_configured":
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка перевода",
                    "Название коина не настроено на этом сервере.",
                    self.bot.user.display_name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if outcome == "user_dont_have_enough_coins":
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка перевода",
                    "У вас недостаточно коинов для перевода.",
                    self.bot.user.display_name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if outcome == "success":
            await interaction.response.send_message(
                embed=SuccessMoveEmbed(
                    "Успешный перевод",
                    f"Вы успешно перевели пользователю {member.mention} {amount} {coin_name}.",  # noqa: E501
                    self.bot.user.display_name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )
            self.bot.dispatch(
                "transfer_coins",
                dto=TransferCoinsEventDTO(
                    guild=guild,
                    event_type="transfer_coins",
                    logging_channel_id=logging_channel_id,
                    sender_id=interaction.user.id,
                    receiver=member,
                    item_name=cast(str, coin_name),
                    amount=amount,
                    comment=comment,
                ),
            )

        logger.info(
            "[command] - invoked user=%s guild=%s target_user=%s amount=%s",
            interaction.user.id,
            guild.id,
            member.id,
            amount,
        )


async def setup(bot: "Nightcore") -> None:
    """Setup the Pay cog."""
    await bot.add_cog(Pay(bot))
