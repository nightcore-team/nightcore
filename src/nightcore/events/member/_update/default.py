import logging
from datetime import datetime, timezone

import discord
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.models import GuildLoggingConfig
from src.infra.db.models._enums import ChannelType
from src.infra.db.operations import get_specified_channel
from src.nightcore.bot import Nightcore
from src.nightcore.utils import ensure_messageable_channel_exists

from ..utils.roles import roles_difference  # type: ignore

logger = logging.getLogger(__name__)


class DefaultUpdateMemberHandler(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @Cog.listener()
    async def on_default_member_update(
        self, before: discord.Member, after: discord.Member
    ) -> None:
        """Handle default member update events."""
        logger.info(f"Member updated: {before} -> {after}")

        if not before:
            logger.warning("[logging] 'before' member is None.")
            return

        guild = after.guild

        async with self.bot.uow.start() as session:
            if not (
                logging_members_channel_id := await get_specified_channel(
                    session,
                    guild_id=guild.id,
                    config_type=GuildLoggingConfig,
                    channel_type=ChannelType.LOGGING_MEMBERS,
                )
            ):
                logger.warning(
                    f"[logging] Logging channel (members) not configured for guild {guild.id}"  # noqa: E501
                )
                return

        if not (
            logging_channel := await ensure_messageable_channel_exists(
                guild, logging_members_channel_id
            )
        ):
            logger.warning(
                f"[logging] Logging channel (members) not found in guild {guild.id}"  # noqa: E501
            )
            return

        executor_id: int | None = None

        embed = discord.Embed(
            color=discord.Color.yellow(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(
            text="Powered by nightcore",
            icon_url=self.bot.user.display_avatar.url,  # type: ignore
        )

        old_display = before.display_name
        new_display = after.display_name

        # check if nickname changed
        nickname_changed = old_display != new_display

        if nickname_changed:
            # AuditLogAction.member_update
            try:
                async for entry in after.guild.audit_logs(
                    action=discord.AuditLogAction.member_update, limit=10
                ):
                    if entry.target.id == after.id:  # type: ignore
                        executor_id = entry.user.id  # type: ignore
                        break

            except discord.Forbidden as e:
                logger.exception(
                    "[logging] Missing permissions to access audit logs in guild %s: %s",  # noqa: E501
                    guild.id,
                    e,
                )
                return
            except discord.HTTPException as e:
                logger.exception(
                    "[logging] HTTP error occurred while accessing audit logs in guild %s: %s",  # noqa: E501
                    guild.id,
                    e,
                )
                return
            except Exception as e:
                logger.exception(
                    "[logging] Unexpected error occurred while accessing audit logs in guild %s: %s",  # noqa: E501
                    guild.id,
                    e,
                )
                return

            if executor_id is None:
                executor_id = after.id

            embed.description = (
                f"Никнейм участника {after.mention} был изменен"
            )
            embed.add_field(
                name="Изменил", value=f"<@{executor_id}>", inline=False
            )
            embed.add_field(
                name="Старый никнейм", value=old_display or "—", inline=False
            )
            embed.add_field(
                name="Новый никнейм", value=new_display or "—", inline=False
            )

        # check roles difference
        before_role_ids = [r.id for r in before.roles]
        after_role_ids = [r.id for r in after.roles]

        added_roles, removed_roles = roles_difference(
            before_role_ids, after_role_ids
        )

        if added_roles or removed_roles:
            if executor_id is None:
                try:
                    async for entry in after.guild.audit_logs(
                        action=discord.AuditLogAction.member_role_update,
                        limit=10,
                    ):
                        if entry.target.id == after.id:  # type: ignore
                            executor_id = entry.user.id  # type: ignore
                            break

                except discord.Forbidden as e:
                    logger.exception(
                        "[logging] Missing permissions to access audit logs in guild %s: %s",  # noqa: E501
                        guild.id,
                        e,
                    )
                    return
                except discord.HTTPException as e:
                    logger.exception(
                        "[logging] HTTP error occurred while accessing audit logs in guild %s: %s",  # noqa: E501
                        guild.id,
                        e,
                    )
                    return
                except Exception as e:
                    logger.exception(
                        "[logging] Unexpected error occurred while accessing audit logs in guild %s: %s",  # noqa: E501
                        guild.id,
                        e,
                    )
                    return

            added_str = (
                "".join(f"<@&{rid}>" for rid in added_roles)
                if added_roles
                else ""
            )
            removed_str = (
                "".join(f"<@&{rid}>" for rid in removed_roles)
                if removed_roles
                else ""
            )

            if embed.description:
                embed.description = "Участник был изменен"
            else:
                embed.description = (
                    f"Роли участника {after.mention} были изменены"
                )
                if executor_id:
                    embed.add_field(
                        name="Изменил", value=f"<@{executor_id}>", inline=False
                    )

            if added_roles:
                embed.add_field(
                    name="Добавленные роли:",
                    value=added_str or "—",
                    inline=False,
                )
            if removed_roles:
                embed.add_field(
                    name="Удаленные роли:",
                    value=removed_str or "—",
                    inline=False,
                )

        if embed.fields:
            try:
                await logging_channel.send(embed=embed)  # type: ignore
            except Exception as e:
                logger.error(f"Failed to send member join log message: {e}")
                return


async def setup(bot: Nightcore) -> None:
    """Setup the DefaultUpdateMemberHandler cog."""
    await bot.add_cog(DefaultUpdateMemberHandler(bot))
