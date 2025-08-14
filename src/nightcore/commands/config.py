"""Config command for the Nightcore bot."""

import logging
from typing import Literal

import discord
from discord import Embed, app_commands
from discord.ext.commands import Cog
from discord.interactions import Interaction, InteractionCallbackResponse

from src.nightcore.bot import Nightcore
from src.nightcore.components.embed.error import NoOptionsSuppliedEmbed
from src.nightcore.services.config import open_guild_config

# from src.nightcore.utils import collect_provided_options
from src.nightcore.utils.config_updates import (
    FieldSpec,
    apply_field_changes,
    float_value,
    format_changes,
    int_id,
    list_csv,
    split_changes,
    str_value,
    update_id_list,
)

logger = logging.getLogger(__name__)
"""
TODO: separate config commands into their own files
"""


class Config(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    config = app_commands.Group(
        name="config",
        description="Configuration commands for the Nightcore bot.",
    )
    logging = app_commands.Group(
        name="logging",
        description="Configuration commands for the logging.",
        parent=config,
    )
    moderation = app_commands.Group(
        name="moderation",
        description="Configuration commands for the moderation.",
        parent=config,
    )
    economy = app_commands.Group(
        name="economy",
        description="Configuration commands for the economy.",
        parent=config,
    )

    clans = app_commands.Group(
        name="clans", description="Configuration commands for the clans."
    )  # TODO: create clans config with update access roles method

    @config.command(
        name="check",
        description="Check if the config is synced with the database.",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def check(
        self, interaction: Interaction
    ) -> InteractionCallbackResponse:
        """Check if the config is synced with the database."""
        async with open_guild_config(
            self.bot,
            interaction.guild.id,  # type: ignore
        ) as guild_config:
            config = guild_config
            description = f"Config is synced with the database for guild ID: {interaction.guild_id}.\n"  # type: ignore  # noqa: E501

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
            ),
            ephemeral=True,
        )

    @logging.command(name="setup", description="Configure logging settings.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        bans="The channel to log bans.",
        voices="The channel to log voice state changes.",
        members="The channel to log member updates.",
        channels="The channel to log channel updates.",
        roles="The channel to log role updates.",
        messages="The channel to log message updates.",
        moderation="The channel to log moderation actions.",
        tickets="The channel to log ticket updates.",
        reactions="The channel to log reaction updates.",
        private_rooms="The channel to log private room updates.",
        ignoring_channels="The channels to ignore for logging. Type: `id,id,id,...`",  # noqa: E501
    )
    async def setup_logging(
        self,
        interaction: Interaction,
        bans: discord.TextChannel | None = None,
        voices: discord.TextChannel | None = None,
        members: discord.TextChannel | None = None,
        channels: discord.TextChannel | None = None,
        roles: discord.TextChannel | None = None,
        messages: discord.TextChannel | None = None,
        moderation: discord.TextChannel | None = None,
        tickets: discord.TextChannel | None = None,
        reactions: discord.TextChannel | None = None,
        private_rooms: discord.TextChannel | None = None,
        ignoring_channels: str | None = None,
    ) -> InteractionCallbackResponse:
        """Configure logging settings for the guild."""
        specs: list[FieldSpec | None] = [
            int_id("bans_log_channel_id", bans),
            int_id("voices_log_channel_id", voices),
            int_id("members_log_channel_id", members),
            int_id("channels_log_channel_id", channels),
            int_id("roles_log_channel_id", roles),
            int_id("messages_log_channel_id", messages),
            int_id("moderation_log_channel_id", moderation),
            int_id("tickets_log_channel_id", tickets),
            int_id("reactions_log_channel_id", reactions),
            int_id("private_rooms_log_channel_id", private_rooms),
            list_csv("message_log_ignoring_channels_ids", ignoring_channels),
        ]

        specs = [s for s in specs if s is not None]

        if not specs:
            logger.info(
                "config.logging invoked user=%s guild=%s no_options_supplied",
                interaction.user.id,  # type: ignore
                interaction.guild.id,  # type: ignore
            )
            return await interaction.response.send_message(
                embed=NoOptionsSuppliedEmbed(),
                ephemeral=True,
            )

        async with open_guild_config(
            self.bot,
            interaction.guild.id,  # type: ignore
        ) as guild_config:
            changes = apply_field_changes(guild_config, specs)  # type: ignore

        changed, skipped = split_changes(changes)
        description = format_changes(changed, skipped)

        logger.info(
            "config.logging invoked user=%s guild=%s updated=%s skipped=%s",
            interaction.user.id,  # type: ignore
            interaction.guild.id,  # type: ignore
            changed,
            skipped,
        )
        return await interaction.response.send_message(
            embed=Embed(
                title="Logging Configuration",
                description=description,
                color=discord.Color.green(),
            ),
            ephemeral=True,
        )

    @logging.command(name="update_ignoring_channels")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.choices(
        option=[
            app_commands.Choice(name="Add", value="add"),
            app_commands.Choice(name="Remove", value="remove"),
        ]
    )
    @app_commands.describe(
        channel="The channel to update",
        option="Whether to add or remove the channel from the ignore list",
    )
    async def update_ignoring_channels(
        self,
        interaction: Interaction,
        channel: discord.TextChannel,
        option: Literal["add", "remove"],
    ) -> InteractionCallbackResponse:
        """Update the list of channels to ignore for logging."""
        async with open_guild_config(
            self.bot,
            interaction.guild.id,  # type: ignore
        ) as guild_config:
            new_list, changed, state = update_id_list(
                guild_config.message_log_ignoring_channels_ids,
                channel.id,
                option,
            )
            if changed:
                guild_config.message_log_ignoring_channels_ids = new_list

        if state == "exists":
            desc = (
                f"Channel <@&{channel.id}> already exists in the ignore list."
            )
            color = discord.Color.yellow()
        elif state == "absent":
            desc = f"Channel <#{channel.id}> is not in the ignore list."
            color = discord.Color.red()
        elif state == "added":
            desc = f"Channel <#{channel.id}> added to the ignore list."
            color = discord.Color.blurple()
        else:  # removed
            desc = f"Channel <#{channel.id}> removed from the ignore list."
            color = discord.Color.blurple()

        logger.info(
            "config.logging.update_ignoring_channels user=%s guild=%s option=%s channel=%s",  # noqa: E501
            interaction.user.id,  # type: ignore
            interaction.guild.id,  # type: ignore
            option,
            channel.id,
        )
        return await interaction.response.send_message(
            embed=Embed(
                title="Logging Configuration",
                description=desc,
                color=color,
            ),
            ephemeral=True,
        )

    @config.command(
        name="moderstats", description="Configure moderation stats settings."
    )
    @app_commands.checks.has_permissions(administrator=True)
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
        mute: float | None = None,
        ban: float | None = None,
        kick: float | None = None,
        ticket: float | None = None,
        vmute: float | None = None,
        mpmute: float | None = None,
        ticket_ban: float | None = None,
        role_request: float | None = None,
        role_remove: float | None = None,
        message: float | None = None,
        role: discord.Role | None = None,
        channel: discord.TextChannel | None = None,
    ):
        """Configure moderation stats settings."""

        specs: list[FieldSpec | None] = [
            float_value("mute_score", mute),
            float_value("ban_score", ban),
            float_value("kick_score", kick),
            float_value("ticket_score", ticket),
            float_value("vmute_score", vmute),
            float_value("mpmute_score", mpmute),
            float_value("ticket_ban_score", ticket_ban),
            float_value("role_request_score", role_request),
            float_value("role_remove_score", role_remove),
            float_value("message_score", message),
            int_id("trackable_moderation_role_id", role),
            int_id("count_moderator_messages_channel_id", channel),
        ]

        specs = [s for s in specs if s is not None]

        if not specs:
            logger.info(
                "config.moderstats invoked user=%s guild=%s no_options_supplied",
                interaction.user.id,  # type: ignore
                interaction.guild.id,  # type: ignore
            )
            return await interaction.response.send_message(
                embed=NoOptionsSuppliedEmbed(),
                ephemeral=True,
            )

        async with open_guild_config(
            self.bot,
            interaction.guild.id,  # type: ignore
        ) as guild_config:
            changes = apply_field_changes(guild_config, specs)  # type: ignore

        changed, skipped = split_changes(changes)
        description = format_changes(changed, skipped)

        logger.info(
            "config.moderstats invoked user=%s guild=%s updated=%s skipped=%s",
            interaction.user.id,  # type: ignore
            interaction.guild.id,  # type: ignore
            changed,
            skipped,
        )
        return await interaction.response.send_message(
            embed=Embed(
                title="Moderstats Configuration",
                description=description,
                color=discord.Color.green(),
            ),
            ephemeral=True,
        )

    @moderation.command(
        name="setup", description="Configure moderation settings."
    )
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        moderation_access_roles="The roles that can access moderation features.",  # noqa: E501
        ban_access_roles="The roles that can access ban features.",
        ban_request_ping_role="The role to ping when a ban request is made.",
        ban_request_channel="The channel where ban requests are made.",
        new_tickets_category="The category for new tickets.",
        pinned_tickets_category="The category for pinned tickets.",
        closed_tickets_category="The category for closed tickets.",
        ticket_created_ping_role="The role to ping when a ticket is created.",
        notifications_channel="The channel for notifications.",
        moderation_notifications_channel="The channel for notifications related to moderation.",  # noqa: E501
        mute_type="The type of mute to apply. Timeout | Role",
        mute_role="The role to assign when a user is muted.",
        mpmute_role="The role to assign when a user is muted in a specific channel.",  # noqa: E501
        vmute_role="The role to assign when a user is voice muted.",
        leaders_access_rr_roles="The roles that can access the leader's report.",  # noqa: E501
    )
    @app_commands.choices(
        mute_type=[
            app_commands.Choice(name="Timeout", value="timeout"),
            app_commands.Choice(name="Role", value="role"),
        ]
    )
    async def setup_moderation(
        self,
        interaction: Interaction,
        moderation_access_roles: str | None = None,
        ban_access_roles: str | None = None,
        ban_request_ping_role: discord.Role | None = None,
        ban_request_channel: discord.TextChannel | None = None,
        new_tickets_category: discord.CategoryChannel | None = None,
        pinned_tickets_category: discord.CategoryChannel | None = None,
        closed_tickets_category: discord.CategoryChannel | None = None,
        ticket_created_ping_role: discord.Role | None = None,
        notifications_channel: discord.TextChannel | None = None,
        moderation_notifications_channel: discord.TextChannel | None = None,
        mute_type: Literal["timeout", "role"] | None = None,
        mute_role: discord.Role | None = None,
        mpmute_role: discord.Role | None = None,
        vmute_role: discord.Role | None = None,
        leaders_access_rr_roles: str | None = None,
    ):
        """Configure moderation settings."""

        specs: list[FieldSpec | None] = [
            int_id("ban_request_ping_role_id", ban_request_ping_role),
            int_id("send_ban_request_channel_id", ban_request_channel),
            int_id("new_tickets_category_id", new_tickets_category),
            int_id("pinned_tickets_category_id", pinned_tickets_category),
            int_id("closed_tickets_category_id", closed_tickets_category),
            int_id("create_ticket_channel_id", ticket_created_ping_role),
            int_id("notifications_channel_id", notifications_channel),
            int_id(
                "notifications_for_moderation_channel_id",
                moderation_notifications_channel,
            ),
            int_id("mute_role_id", mute_role),
            int_id("mpmute_role_id", mpmute_role),
            int_id("vmute_role_id", vmute_role),
            list_csv("moderation_access_roles_ids", moderation_access_roles),
            list_csv("ban_access_roles_ids", ban_access_roles),
            list_csv("leaders_access_rr_roles_ids", leaders_access_rr_roles),
            str_value("mute_type", mute_type),
        ]

        specs = [s for s in specs if s is not None]

        if not specs:
            logger.info(
                "config.moderation.setup invoked user=%s guild=%s no_options_supplied",  # noqa: E501
                interaction.user.id,  # type: ignore
                interaction.guild.id,  # type: ignore
            )
            return await interaction.response.send_message(
                embed=NoOptionsSuppliedEmbed(),
                ephemeral=True,
            )

        async with open_guild_config(
            self.bot,
            interaction.guild.id,  # type: ignore
        ) as guild_config:
            changes = apply_field_changes(guild_config, specs)  # type: ignore

        changed, skipped = split_changes(changes)
        description = format_changes(changed, skipped)

        logger.info(
            "config.moderation.setup invoked user=%s guild=%s updated=%s skipped=%s",  # noqa: E501
            interaction.user.id,  # type: ignore
            interaction.guild.id,  # type: ignore
            changed,
            skipped,
        )
        return await interaction.response.send_message(
            embed=Embed(
                title="Moderation Configuration",
                description=description,
                color=discord.Color.green(),
            ),
            ephemeral=True,
        )

    @moderation.command(name="update_moderation_access")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.choices(
        option=[
            app_commands.Choice(name="Add", value="add"),
            app_commands.Choice(name="Remove", value="remove"),
        ]
    )
    @app_commands.describe(
        role="The role to update",
        option="Whether to add or remove the role from the moderation access list",  # noqa: E501
    )
    async def update_moderation_access(
        self,
        interaction: Interaction,
        role: discord.Role,
        option: Literal["add", "remove"],
    ) -> InteractionCallbackResponse:
        """Update the list of roles with moderation access."""

        async with open_guild_config(
            self.bot,
            interaction.guild.id,  # type: ignore
        ) as guild_config:
            new_list, changed, state = update_id_list(
                guild_config.moderation_access_roles_ids,
                role.id,
                option,
            )
            if changed:
                guild_config.moderation_access_roles_ids = new_list

        if state == "exists":
            desc = f"Role <@&{role.id}> already in the moderation access list."
            color = discord.Color.yellow()
        elif state == "absent":
            desc = f"Role <@&{role.id}> not in the moderation access list."
            color = discord.Color.red()
        elif state == "added":
            desc = f"Role <@&{role.id}> added to the moderation access list."
            color = discord.Color.blurple()
        else:  # removed
            desc = (
                f"Role <@&{role.id}> removed from the moderation access list."
            )
            color = discord.Color.blurple()

        logger.info(
            "config.logging.update_moderation_access user=%s guild=%s option=%s role=%s",  # noqa: E501
            interaction.user.id,  # type: ignore
            interaction.guild.id,  # type: ignore
            option,
            role.id,
        )

        return await interaction.response.send_message(
            embed=Embed(
                title="Moderation Configuration",
                description=desc,
                color=color,
            ),
            ephemeral=True,
        )

    @moderation.command(name="update_ban_access")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.choices(
        option=[
            app_commands.Choice(name="Add", value="add"),
            app_commands.Choice(name="Remove", value="remove"),
        ]
    )
    @app_commands.describe(
        role="The role to update",
        option="Whether to add or remove the role from the ban access list",
    )
    async def update_ban_access(
        self,
        interaction: Interaction,
        role: discord.Role,
        option: Literal["add", "remove"],
    ) -> InteractionCallbackResponse:
        """Update the list of roles with ban access."""
        async with open_guild_config(
            self.bot,
            interaction.guild.id,  # type: ignore
        ) as guild_config:
            new_list, changed, state = update_id_list(
                guild_config.ban_access_roles_ids,
                role.id,
                option,
            )
            if changed:
                guild_config.ban_access_roles_ids = new_list

        if state == "exists":
            desc = f"Role <@&{role.id}> already in the ban access list."
            color = discord.Color.yellow()
        elif state == "absent":
            desc = f"Role <@&{role.id}> not in the ban access list."
            color = discord.Color.red()
        elif state == "added":
            desc = f"Role <@&{role.id}> added to the ban access list."
            color = discord.Color.blurple()
        else:  # removed
            desc = f"Role <@&{role.id}> removed from the ban access list."
            color = discord.Color.blurple()

        logger.info(
            "config.logging.update_ban_access user=%s guild=%s option=%s role=%s",  # noqa: E501
            interaction.user.id,  # type: ignore
            interaction.guild.id,  # type: ignore
            option,
            role.id,
        )

        return await interaction.response.send_message(
            embed=Embed(
                title="Moderation Configuration",
                description=desc,
                color=color,
            ),
            ephemeral=True,
        )

    @moderation.command(name="update_leaders_access")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.choices(
        option=[
            app_commands.Choice(name="Add", value="add"),
            app_commands.Choice(name="Remove", value="remove"),
        ]
    )
    @app_commands.describe(
        role="The role to update",
        option="Whether to add or remove the role from the leaders access list",  # noqa: E501
    )
    async def update_leaders_access(
        self,
        interaction: Interaction,
        role: discord.Role,
        option: Literal["add", "remove"],
    ) -> InteractionCallbackResponse:
        """Update the list of leaders roles with `rr` access."""
        async with open_guild_config(
            self.bot,
            interaction.guild.id,  # type: ignore
        ) as guild_config:
            new_list, changed, state = update_id_list(
                guild_config.leader_access_rr_roles_ids,
                role.id,
                option,
            )
            if changed:
                guild_config.leader_access_rr_roles_ids = new_list

        if state == "exists":
            desc = f"Role <@&{role.id}> already in the leaders access list."
            color = discord.Color.yellow()
        elif state == "absent":
            desc = f"Role <@&{role.id}> not in the leaders access list."
            color = discord.Color.red()
        elif state == "added":
            desc = f"Role <@&{role.id}> added to the leaders access list."
            color = discord.Color.blurple()
        else:  # removed
            desc = f"Role <@&{role.id}> removed from the leaders access list."
            color = discord.Color.blurple()

        logger.info(
            "config.logging.update_leaders_access user=%s guild=%s option=%s role=%s",  # noqa: E501
            interaction.user.id,  # type: ignore
            interaction.guild.id,  # type: ignore
            option,
            role.id,
        )

        return await interaction.response.send_message(
            embed=Embed(
                title="Moderation Configuration",
                description=desc,
                color=color,
            ),
            ephemeral=True,
        )

    @config.command(
        name="private_channels",
        description="Configure private channels settings.",
    )
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        create_private_channel="The channel to create for private rooms."
    )
    async def private_channels(
        self,
        interaction: Interaction,
        create_private_channel: discord.VoiceChannel | None = None,
    ) -> InteractionCallbackResponse:
        """Configure private channels settings."""
        specs: list[FieldSpec | None] = [
            int_id("private_rooms_create_channel_id", create_private_channel)
        ]

        specs = [s for s in specs if s is not None]

        if not specs:
            logger.info(
                "config.private_channels invoked user=%s guild=%s no_options_supplied",  # noqa: E501
                interaction.user.id,  # type: ignore
                interaction.guild.id,  # type: ignore
            )
            return await interaction.response.send_message(
                embed=NoOptionsSuppliedEmbed(),
                ephemeral=True,
            )

        async with open_guild_config(
            self.bot,
            interaction.guild.id,  # type: ignore
        ) as guild_config:
            changes = apply_field_changes(guild_config, specs)  # type: ignore

        changed, skipped = split_changes(changes)
        description = format_changes(changed, skipped)

        logger.info(
            "config.private_channels invoked user=%s guild=%s updated=%s skipped=%s",  # noqa: E501
            interaction.user.id,  # type: ignore
            interaction.guild.id,  # type: ignore
            changed,
            skipped,
        )
        return await interaction.response.send_message(
            embed=Embed(
                title="Private Channels Configuration",
                description=description,
                color=discord.Color.green(),
            ),
            ephemeral=True,
        )

    @config.command(name="main", description="Configure main settings.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe()
    # TODO: create main config command
    async def main(self, interaction: Interaction): ...


async def setup(bot: Nightcore):
    """Setup the Config cog."""
    await bot.add_cog(Config(bot))
