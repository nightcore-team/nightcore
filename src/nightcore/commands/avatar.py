"""Ping command for the Nightcore bot."""

import discord
from discord import Embed, app_commands
from discord.ext.commands import Cog
from discord.interactions import InteractionCallbackResponse

from src.nightcore.bot import Nightcore


class Avatar(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @app_commands.command(name="avatar", description="Get user's avatar")
    async def avatar(
        self,
        interaction: discord.Interaction,
        member: discord.Member | discord.User | None = None,
    ) -> InteractionCallbackResponse:
        """Send a message displaying the user's avatar.

        Args:
            interaction : discord.Interaction
                The interaction that triggered the command.
            member :
                The member whose avatar to display. If None, defaults to the user who invoked the command.
        """  # noqa: E501

        if member is None:
            member = interaction.user

        return await interaction.response.send_message(
            embed=Embed(
                title=f"Аватар пользователя {member.display_name}",
                color=discord.Color.blurple(),
            ).set_image(
                url=member.avatar.url
                if member.avatar
                else member.default_avatar.url
            ),
            ephemeral=True,
        )
