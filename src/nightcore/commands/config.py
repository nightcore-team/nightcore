"""Config command for the Nightcore bot."""

import discord
from discord import Embed, app_commands
from discord.ext.commands import Cog
from discord.interactions import InteractionCallbackResponse

from src.infra.db.operations import (
    apply_field_mapping_to_model,
    get_guild_config,
)
from src.nightcore.bot import Nightcore
from src.nightcore.utils import collect_provided_options


class Config(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    config = app_commands.Group(
        name="config",
        description="Configuration commands for the Nightcore bot.",
    )

    @app_commands.checks.has_permissions(administrator=True)
    @config.command(
        name="check",
        description="Check if the config is synced with the database.",
    )
    async def check(
        self, interaction: discord.Interaction
    ) -> InteractionCallbackResponse:
        """Check if the config is synced with the database."""
        async with self.bot.uow.start() as uow:
            config = await get_guild_config(
                uow.session,  # type: ignore
                guild_id=interaction.guild_id,  # type: ignore
            )
        if config:
            description = f"Config is synced with the database for guild ID: {interaction.guild_id}.\n"  # type: ignore
        else:
            description = "Your config will be added to the database."

        return await interaction.response.send_message(
            embed=Embed(
                title="Config Check",
                description=description,
                color=discord.Color.green(),
            )
        )

    @app_commands.checks.has_permissions(administrator=True)
    @config.command(name="logging", description="Configure logging settings.")
    async def logging(
        self,
        interaction: discord.Interaction,
        bans: str | None = None,
        voices: str | None = None,
        members: str | None = None,
        channels: str | None = None,
        roles: str | None = None,
        messages: str | None = None,
        moderation: str | None = None,
        reactions: str | None = None,
        ignoring_channels: str | None = None,
    ) -> InteractionCallbackResponse:
        """Configure logging settings for the guild."""
        provided_int = collect_provided_options(
            bans=bans,
            moderation=moderation,
            voices=voices,
            members=members,
            channels=channels,
            roles=roles,
            messages=messages,
            reactions=reactions,
        )
        provided_list = collect_provided_options(
            ignoring_channels=ignoring_channels
        )

        if not provided_int and not provided_list:
            return await interaction.response.send_message(
                embed=Embed(
                    title="Logging Configuration",
                    description="No options supplied. Nothing to change.",
                    color=discord.Color.yellow(),
                )
            )

        async with self.bot.uow.start() as uow:
            guild_config = await get_guild_config(
                uow.session,  # type: ignore
                guild_id=interaction.guild_id,  # type: ignore
            )

            if not guild_config:
                return await interaction.response.send_message(
                    embed=Embed(
                        title="Logging Configuration",
                        description="No config found for this guild, but it will be created now. Please run this command again.",
                        color=discord.Color.red(),
                    )
                )

            changed_int, skipped_int = apply_field_mapping_to_model(
                guild_config,
                provided=provided_int,
                attr_template="{field}_log_channel_id",
                cast_type=int,
            )
            changed_list, skipped_list = apply_field_mapping_to_model(
                guild_config,
                provided=provided_list,
                attr_template="message_log_{field}_ids",
                cast_type=list,
            )

        description_parts = []
        if changed_int + changed_list:
            description_parts.append(
                "Updated:\n"
                + "\n".join(f"- {c}" for c in changed_int + changed_list)
            )
        if skipped_int + skipped_list:
            description_parts.append(
                "Unchanged / skipped:\n"
                + "\n".join(f"- {s}" for s in skipped_int + skipped_list)
            )

        return await interaction.response.send_message(
            embed=Embed(
                title="Logging Configuration",
                description="\n\n".join(description_parts),
                color=discord.Color.green(),
            )
        )


async def setup(bot: Nightcore):
    """Setup the Config cog."""
    await bot.add_cog(Config(bot))
