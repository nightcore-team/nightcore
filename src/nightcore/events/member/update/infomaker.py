"""Handle infomaker member update events."""

import logging
from datetime import datetime, timezone

import discord
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.models import GuildInfomakerConfig
from src.nightcore.bot import Nightcore
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils import ensure_messageable_channel_exists

from ..utils.roles import roles_difference  # type: ignore

logger = logging.getLogger(__name__)


class InfomakerUpdateMemberEvent(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @Cog.listener()
    async def on_infomaker_member_update(
        self, before: discord.Member, after: discord.Member
    ) -> None:
        """Handle infomaker member update events."""

        if not before:
            logger.warning("[logging] 'before' member is None.")
            return

        guild = after.guild

        async with specified_guild_config(
            self.bot,
            guild.id,
            config_type=GuildInfomakerConfig,  # type: ignore
        ) as (guild_config, _):
            if not guild_config:
                logger.info(
                    f"[infomaker] Infomaker config not configured for guild {guild.id}"  # noqa: E501
                )
                return

        leader_roles_ids: list[int] = guild_config.leaders_roles_ids or []
        admin_roles_ids: list[int] = guild_config.admins_roles_ids or []

        if not leader_roles_ids and not admin_roles_ids:
            logger.warning(
                f"[logging] Leader roles not configured for guild {guild.id}"
            )
            return

        if (
            not guild_config.leaders_roles_logging_channel_id
            and not guild_config.admins_roles_logging_channel_id
        ):
            logger.warning(
                f"[logging] Logging channel (leaders/admins) not configured for guild {guild.id}"  # noqa: E501
            )
            return

        added_roles, removed_roles = roles_difference(
            [r.id for r in before.roles], [r.id for r in after.roles]
        )
        added_roles, removed_roles = set(added_roles), set(removed_roles)

        if not added_roles and not removed_roles:
            logger.info("[infomaker] No role changes detected.")
            return

        added_leader_roles_string = "".join(
            f"<@&{r}>" for r in added_roles if r in leader_roles_ids
        )
        added_admin_roles_string = "".join(
            f"<@&{r}>" for r in added_roles if r in admin_roles_ids
        )
        removed_leader_roles_string = "".join(
            f"<@&{r}>" for r in removed_roles if r in leader_roles_ids
        )
        removed_admin_roles_string = "".join(
            f"<@&{r}>" for r in removed_roles if r in admin_roles_ids
        )
        if added_leader_roles_string or removed_leader_roles_string:
            leader_embed = discord.Embed(
                description=f"Изменение лидерских ролей пользователя {after.mention}",  # noqa: E501
                color=discord.Color.blurple(),
                timestamp=datetime.now(timezone.utc),
            )
            leader_embed.set_footer(
                text="Powered by nightcore",
                icon_url=self.bot.user.display_avatar.url,  # type: ignore
            )
            leader_embed.add_field(
                name="Никнейм пользователя",
                value=after.display_name,
            )

            if added_leader_roles_string:
                leader_embed.add_field(
                    name="Добавленные роли",
                    value=added_leader_roles_string,
                    inline=False,
                )
            if removed_leader_roles_string:
                leader_embed.add_field(
                    name="Удалённые роли",
                    value=removed_leader_roles_string,
                    inline=False,
                )

            if logging_channel := await ensure_messageable_channel_exists(
                guild,
                guild_config.leaders_roles_logging_channel_id,  # type: ignore
            ):
                await logging_channel.send(embed=leader_embed)  # type: ignore

        if added_admin_roles_string or removed_admin_roles_string:
            admin_embed = discord.Embed(
                description=f"Изменение административных ролей пользователя {after.mention}",  # noqa: E501
                color=discord.Color.blurple(),
                timestamp=datetime.now(timezone.utc),
            )
            admin_embed.set_footer(
                text="Powered by nightcore",
                icon_url=self.bot.user.display_avatar.url,  # type: ignore
            )
            admin_embed.add_field(
                name="Никнейм пользователя",
                value=after.display_name,
            )

            if added_admin_roles_string:
                admin_embed.add_field(
                    name="Добавленные роли",
                    value=added_admin_roles_string,
                    inline=False,
                )
            if removed_admin_roles_string:
                admin_embed.add_field(
                    name="Удалённые роли",
                    value=removed_admin_roles_string,
                    inline=False,
                )

            if logging_channel := await ensure_messageable_channel_exists(
                guild,
                guild_config.admins_roles_logging_channel_id,  # type: ignore
            ):
                await logging_channel.send(embed=admin_embed)  # type: ignore


async def setup(bot: Nightcore) -> None:
    """Setup the InfomakerUpdateMemberEvent cog."""
    await bot.add_cog(InfomakerUpdateMemberEvent(bot))
