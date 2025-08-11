"""Config command for the Nightcore bot."""

import logging

import discord
from discord import Embed, app_commands
from discord.ext.commands import Cog
from discord.interactions import Interaction, InteractionCallbackResponse

from src.infra.db.operations import (
    apply_field_mapping_to_model,
    get_guild_config,
)
from src.nightcore.bot import Nightcore
from src.nightcore.utils import collect_provided_options

logger = logging.getLogger(__name__)


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
        self, interaction: Interaction
    ) -> InteractionCallbackResponse:
        """Check if the config is synced with the database."""
        async with self.bot.uow.start() as uow:
            config = await get_guild_config(
                uow.session,  # type: ignore
                guild_id=interaction.guild_id,  # type: ignore
            )
        if config:
            description = f"Config is synced with the database for guild ID: {interaction.guild_id}.\n"  # type: ignore  # noqa: E501
        else:
            description = "Your config will be added to the database."

        logger.info(
            "config.check invoked user=%s guild=%s exists=%s",
            interaction.user.id,  # type: ignore
            interaction.guild.id,  # type: ignore
            bool(config),
        )
        return await interaction.response.send_message(
            embed=Embed(
                title="Config Check",
                description=description,
                color=discord.Color.green(),
            )
        )

    @app_commands.checks.has_permissions(administrator=True)
    @config.command(name="logging", description="Configure logging settings.")
    @app_commands.describe(
        bans="The channel to log bans.",
        voices="The channel to log voice state changes.",
        members="The channel to log member updates.",
        channels="The channel to log channel updates.",
        roles="The channel to log role updates.",
        messages="The channel to log message updates.",
        moderation="The channel to log moderation actions.",
        reactions="The channel to log reaction updates.",
        ignoring_channels="The channels to ignore for logging.",
    )
    async def logging(
        self,
        interaction: Interaction,
        bans: str | None = None,
        voices: str | None = None,
        members: str | None = None,
        channels: str | None = None,
        roles: str | None = None,
        messages: str | None = None,
        moderation: str | None = None,
        tickets: str | None = None,
        reactions: str | None = None,
        ignoring_channels: str | None = None,
    ) -> InteractionCallbackResponse:
        """Configure logging settings for the guild."""
        provided_int = collect_provided_options(
            bans_log_channel_id=bans,
            moderation_log_channel_id=moderation,
            voices_log_channel_id=voices,
            members_log_channel_id=members,
            channels_log_channel_id=channels,
            roles_log_channel_id=roles,
            tickets_log_channel_id=tickets,
            messages_log_channel_id=messages,
            reactions_log_channel_id=reactions,
        )
        provided_list = collect_provided_options(
            message_log_ignoring_channels_ids=ignoring_channels
        )

        if not any((provided_int, provided_list)):
            logger.info(
                "config.logging invoked user=%s guild=%s no_options_supplied",
                interaction.user.id,  # type: ignore
                interaction.guild.id,  # type: ignore
            )
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
                logger.info(
                    "config.logging invoked user=%s guild=%s config_missing_will_create",  # noqa: E501
                    interaction.user.id,  # type: ignore
                    interaction.guild.id,  # type: ignore
                )
                return await interaction.response.send_message(
                    embed=Embed(
                        title="Logging Configuration",
                        description="No config found for this guild, but it will be created now. Please run this command again.",  # noqa: E501
                        color=discord.Color.red(),
                    )
                )

            changed_int, skipped_int = apply_field_mapping_to_model(
                guild_config,
                provided=provided_int,
                attr_template="{field}",
                cast_type=int,
            )
            changed_list, skipped_list = apply_field_mapping_to_model(
                guild_config,
                provided=provided_list,
                attr_template="{field}",
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

        logger.info(
            "config.logging invoked user=%s guild=%s updated=%s skipped=%s provided_int=%s provided_list=%s",  # noqa: E501
            interaction.user.id,  # type: ignore
            interaction.guild.id,  # type: ignore
            changed_int + changed_list,
            skipped_int + skipped_list,
            list(provided_int.keys()),
            list(provided_list.keys()),
        )
        return await interaction.response.send_message(
            embed=Embed(
                title="Logging Configuration",
                description="\n\n".join(description_parts),
                color=discord.Color.green(),
            )
        )

    @app_commands.checks.has_permissions(administrator=True)
    @config.command(
        name="moderstats", description="Configure moderation stats settings."
    )
    @app_commands.describe(
        mute="Mute score",
        ban="Ban score",
        kick="Kick score",
        ticket="Ticket score",
        vmute="Voice mute score",
        mpmute="Member mute score",
        ticket_ban="Ticket ban score",
        role_request="Role request score",
        role_remove="Role remove score",
        message="Message score",
        role="Trackable moderation role",
        channel="Count moderator messages channel",
    )
    async def moderstats(
        self,
        interaction: Interaction,
        mute: str | None = None,  # float
        ban: str | None = None,  # float
        kick: str | None = None,  # float
        ticket: str | None = None,  # float
        vmute: str | None = None,  # float
        mpmute: str | None = None,  # float
        ticket_ban: str | None = None,  # float
        role_request: str | None = None,  # float
        role_remove: str | None = None,  # float
        message: str | None = None,  # float
        role: str | None = None,  # int
        channel: str | None = None,  # int
    ):
        """Configure moderation stats settings."""
        provided_float = collect_provided_options(
            mute_score=mute,
            ban_score=ban,
            kick_score=kick,
            ticket_score=ticket,
            vmute_score=vmute,
            mpmute_score=mpmute,
            ticket_ban_score=ticket_ban,
            role_request_score=role_request,
            role_remove_score=role_remove,
            message_score=message,
        )

        provided_int = collect_provided_options(
            trackable_moderation_role_id=role,
            count_moderator_messages_channel_id=channel,
        )

        if not any((provided_float, provided_int)):
            logger.info(
                "config.logging invoked user=%s guild=%s no_options_supplied",
                interaction.user.id,  # type: ignore
                interaction.guild.id,  # type: ignore
            )
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
                logger.info(
                    "config.logging invoked user=%s guild=%s config_missing_will_create",  # noqa: E501
                    interaction.user.id,  # type: ignore
                    interaction.guild.id,  # type: ignore
                )
                return await interaction.response.send_message(
                    embed=Embed(
                        title="Logging Configuration",
                        description="No config found for this guild, but it will be created now. Please run this command again.",  # noqa: E501
                        color=discord.Color.red(),
                    )
                )

            changed_float, skipped_float = apply_field_mapping_to_model(
                guild_config,
                provided=provided_float,
                attr_template="{field}",
                cast_type=float,
            )
            changed_int, skipped_int = apply_field_mapping_to_model(
                guild_config,
                provided=provided_int,
                attr_template="{field}",
                cast_type=int,
            )

        description_parts = []
        if changed_float + changed_int:
            description_parts.append(
                "Updated:\n"
                + "\n".join(f"- {c}" for c in changed_float + changed_int)
            )
        if skipped_float + skipped_int:
            description_parts.append(
                "Unchanged / skipped:\n"
                + "\n".join(f"- {s}" for s in skipped_int + skipped_float)
            )

        logger.info(
            "config.logging invoked user=%s guild=%s updated=%s skipped=%s provided_int=%s provided_list=%s",  # noqa: E501
            interaction.user.id,  # type: ignore
            interaction.guild.id,  # type: ignore
            changed_int + changed_float,
            skipped_int + skipped_float,
            list(provided_int.keys()),
            list(provided_float.keys()),
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
