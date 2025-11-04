"""Command to check user infractions."""

import logging
from typing import cast

import discord
from discord import Guild, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.infra.db.models import GuildNotificationsConfig
from src.infra.db.models._enums import ChannelType
from src.infra.db.operations import (
    count_user_infractions_last_7_days,
    get_moderation_access_roles,
    get_specified_channel,
    get_user_infractions,
)
from src.nightcore.bot import Nightcore
from src.nightcore.components.embed import (
    ErrorEmbed,
    MissingPermissionsEmbed,
)
from src.nightcore.exceptions import FieldNotConfiguredError
from src.nightcore.features.moderation.components.v2 import (
    InfractionsViewV2,
)
from src.nightcore.features.moderation.utils import build_infraction_pages
from src.nightcore.utils import has_any_role_from_sequence

logger = logging.getLogger(__name__)


class Infractions(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @app_commands.command(
        name="infractions",
        description="Посмотреть список нарушений пользователя",
    )
    @app_commands.describe(
        user="Пользователь для проверки нарушений",
        ephemeral="Скрыть ответ от других пользователей. По умолчанию: True",
    )
    async def infractions(
        self,
        interaction: Interaction,
        user: discord.User,
        ephemeral: bool = True,
    ):
        """Check user infractions."""
        guild = cast(Guild, interaction.guild)

        async with self.bot.uow.start() as session:
            # check moderation access
            if not (
                moderation_access_roles := await get_moderation_access_roles(
                    session, guild_id=guild.id
                )
            ):
                raise FieldNotConfiguredError("доступ к модерации")

            # get user infractions
            infractions = await get_user_infractions(
                session,
                guild_id=guild.id,
                user_id=user.id,
            )

            last_7_days_infractions = await count_user_infractions_last_7_days(
                session,
                guild_id=guild.id,
                user_id=user.id,
            )

            # get notifications channel
            notify_channel_id = await get_specified_channel(
                session,
                guild_id=guild.id,
                config_type=GuildNotificationsConfig,
                channel_type=ChannelType.NOTIFICATIONS,
            )

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

        # get user infractions from db
        pages = build_infraction_pages(
            infractions, guild.id, notify_channel_id, is_v2=True
        )

        view = InfractionsViewV2(
            interaction.user.id, pages, user, self.bot, last_7_days_infractions
        )

        await interaction.response.defer(thinking=True, ephemeral=ephemeral)

        try:
            await interaction.followup.send(view=view.make_component())
        except Exception as e:
            logger.exception(
                "[command] - Failed to send infractions view: %s", e
            )
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Ошибка отправки нарушений",
                    "Не удалось отправить компонент нарушений.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
            )

        logger.info(
            "[command] - invoked user=%s guild=%s target=%s",
            interaction.user.id,
            guild.id,
            user.id,
        )


async def setup(bot: Nightcore):
    """Setup the Infractions cog."""
    await bot.add_cog(Infractions(bot))
