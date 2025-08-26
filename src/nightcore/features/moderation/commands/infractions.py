"""Infractions command for the Nightcore bot."""

import logging
from typing import cast

import discord
from discord import Guild, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.infra.db.models import GuildNotificationsConfig
from src.infra.db.models._enums import ChannelType
from src.infra.db.operations import (
    get_moderation_access_roles,
    get_specified_channel,
    get_user_infractions,
)
from src.nightcore.bot import Nightcore
from src.nightcore.components import (
    ErrorEmbed,
    MissingPermissionsEmbed,
)
from src.nightcore.features.moderation.components import (
    InfractionsView,
)
from src.nightcore.features.moderation.utils import build_pages

logger = logging.getLogger(__name__)


# TODO: refactoring / separate utils / components


class Infractions(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @app_commands.command(
        name="infractions", description="Check user infractions"
    )
    @app_commands.describe(user="The user to check infractions for")
    async def infractions(
        self,
        interaction: Interaction,
        user: discord.User,
    ):
        """Check user infractions."""
        guild = cast(Guild, interaction.guild)

        async with self.bot.uow.start() as session:
            # check moderation access
            moderation_access_roles = await get_moderation_access_roles(
                session, guild_id=guild.id
            )

            # get user infractions
            infractions = await get_user_infractions(
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

        has_moder_role = any(
            interaction.user.get_role(role_id)  # type: ignore
            for role_id in moderation_access_roles
        )
        if not has_moder_role:
            await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )
            return

        # get user infractions from db
        pages = build_pages(infractions, guild.id, notify_channel_id)
        embed = discord.Embed(
            description=pages[0], color=discord.Color.blurple()
        )
        embed.set_author(
            name=f"{user} ➤ Infractions", icon_url=user.display_avatar.url
        )
        embed.set_footer(
            text=f"Page 1 / {len(pages)}",
            icon_url=self.bot.user.display_avatar.url,  # type: ignore
        )

        await interaction.response.defer()

        if len(pages) == 1:
            await interaction.followup.send(embed=embed)
            return

        try:
            await interaction.followup.send(
                embed=embed,
                view=InfractionsView(
                    interaction.user.id, pages, user, self.bot
                ),
            )
        except Exception as e:
            logger.exception(
                "[command] - Failed to send infractions view: %s", e
            )
            await interaction.followup.send(
                embed=ErrorEmbed(
                    "Infractions Error",
                    "Failed to send infractions view.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                )
            )


async def setup(bot: Nightcore):
    """Setup the Infractions cog."""
    await bot.add_cog(Infractions(bot))
