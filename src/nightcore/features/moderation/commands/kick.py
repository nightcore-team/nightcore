"""Kick command for the Nightcore bot."""

import logging
from datetime import UTC
from typing import TYPE_CHECKING, cast

import discord
from discord import Guild, Member, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.infra.db.operations import get_moderation_access_roles
from src.nightcore.components.view.v2 import (
    ErrorViewV2,
    MissingPermissionsViewV2,
)
from src.nightcore.features.moderation.components.v2 import PunishViewV2
from src.nightcore.features.moderation.events import UserKickEventData
from src.nightcore.features.moderation.utils.transformers import (
    StringToRuleTransformer,
)
from src.nightcore.utils import (
    compare_top_roles,
    has_any_role_from_sequence,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

logger = logging.getLogger(__name__)


class Kick(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

    @app_commands.command(  # type: ignore
        name="kick",
        description="Кикнуть пользователя с сервера",
    )
    @app_commands.guild_only()
    @app_commands.describe(user="Пользователь для кика", reason="Причина кика")
    @check_required_permissions(PermissionsFlagEnum.MODERATION_ACCESS)  # type: ignore
    async def kick(
        self,
        interaction: Interaction,
        user: Member,
        reason: app_commands.Transform[
            app_commands.Range[str, 1, 1000], StringToRuleTransformer
        ],
    ):
        """Kick a user from the server."""
        guild = cast(Guild, interaction.guild)

        # Ensure we have a guild Member object
        member = user

        async with self.bot.uow.start() as session:
            moderation_access_roles = await get_moderation_access_roles(
                session, guild_id=guild.id
            )

        is_member_moderator = has_any_role_from_sequence(
            member, moderation_access_roles
        )
        if is_member_moderator:
            await interaction.response.send_message(
                view=ErrorViewV2(
                    "Ошибка кика пользователя",
                    "Вы не можете кикнуть модераторов.",
                ),
                ephemeral=True,
            )
            return

        if member.guild_permissions.administrator:
            await interaction.response.send_message(
                view=ErrorViewV2(
                    "Ошибка кика пользователя",
                    "Вы не можете кикнуть администраторов.",
                ),
                ephemeral=True,
            )
            return

        if not guild.me.guild_permissions.kick_members:
            await interaction.response.send_message(
                view=MissingPermissionsViewV2(
                    "У меня нет прав для кика участников."
                ),
                ephemeral=True,
            )
            return

        if guild.me == member:
            await interaction.response.send_message(
                view=ErrorViewV2(
                    "Ошибка кика пользователя",
                    "Вы не можете кикнуть меня.",
                ),
                ephemeral=True,
            )
            return

        if not compare_top_roles(guild, member):
            await interaction.response.send_message(
                view=MissingPermissionsViewV2(
                    "Я не могу кикнуть этого пользователя, потому что у него роль выше моей.",  # noqa: E501
                ),
                ephemeral=True,
            )
            return

        await interaction.response.defer(thinking=True)

        try:
            await guild.kick(member, reason=reason)
        except discord.Forbidden as e:
            logger.warning("[command] - Forbidden kick user: %s", e)
            await interaction.followup.send(
                view=ErrorViewV2(
                    "Ошибка кика",
                    "Не удалось кикнуть пользователя.",
                ),
                ephemeral=True,
            )
            return
        except discord.NotFound:
            # Idempotent: already kicked / not in guild
            await interaction.followup.send(
                view=ErrorViewV2(
                    "Ошибка кика",
                    "Пользователь уже не на сервере.",
                ),
                ephemeral=True,
            )
            return
        except discord.HTTPException as e:
            logger.warning("[command] - Failed to kick user (http): %s", e)
            await interaction.followup.send(
                view=ErrorViewV2(
                    "Ошибка кика",
                    "Не удалось кикнуть пользователя.",
                ),
                ephemeral=True,
            )
            return
        except Exception as e:
            logger.warning("[command] - Failed to kick user: %s", e)
            await interaction.followup.send(
                view=ErrorViewV2(
                    "Ошибка кика",
                    "Не удалось кикнуть пользователя.",
                ),
                ephemeral=True,
            )
            return

        # Dispatch after successful Discord action
        try:
            self.bot.dispatch(
                "user_kicked",
                data=UserKickEventData(
                    mode="dm",
                    moderator=interaction.user,  # type: ignore
                    user=member,
                    category=self.__class__.__name__.lower(),
                    reason=reason,
                    created_at=discord.utils.utcnow().astimezone(tz=UTC),
                    guild_name=guild.name,
                ),
            )
        except Exception as e:
            logger.warning(
                "[event] - Failed to dispatch user_kicked event: %s", e
            )
            return

        await interaction.followup.send(
            view=PunishViewV2(
                bot=self.bot,
                user_id=member.id,
                punish_type="kick",
                moderator_id=interaction.user.id,  # type: ignore
                reason=reason,
                mode="server",
            )
        )
        logger.debug(
            "[command] - invoked user=%s guild=%s target=%s reason=%s",
            interaction.user.id,
            guild.id,
            user.id,
            reason,
        )


async def setup(bot: "Nightcore"):
    """Setup the Kick cog."""
    await bot.add_cog(Kick(bot))
