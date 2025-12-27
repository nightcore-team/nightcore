"""Ban command for the Nightcore bot."""

import logging
from datetime import UTC
from typing import TYPE_CHECKING, cast

import discord
from discord import AppCommandContext, Guild, Member, User, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.config.config import config
from src.infra.db.models import GuildModerationConfig
from src.nightcore.components.embed import (
    ErrorEmbed,
    MissingPermissionsEmbed,
    ValidationErrorEmbed,
)
from src.nightcore.exceptions import FieldNotConfiguredError
from src.nightcore.features.moderation.components.modal import BanFormModal
from src.nightcore.features.moderation.components.v2 import PunishViewV2
from src.nightcore.features.moderation.events import UserBannedEventData
from src.nightcore.features.moderation.utils.punish_notify import (
    send_punish_dm_message,
)
from src.nightcore.features.moderation.utils.transformers import (
    StringToRuleTransformer,
)
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils import (
    compare_top_roles,
    ensure_member_exists,
    ensure_messageable_channel_exists,
    has_any_role_from_sequence,
)
from src.nightcore.utils.time_utils import calculate_end_time, parse_duration

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

logger = logging.getLogger(__name__)


class Ban(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

    @app_commands.command(  # type: ignore
        name="ban", description="Забанить пользователя на сервере"
    )
    @app_commands.describe(
        user="Пользователь для бана", reason="Причина бана пользователя"
    )
    @app_commands.guild_only()
    @check_required_permissions(PermissionsFlagEnum.BAN_ACCESS)  # type: ignore
    async def ban(
        self,
        interaction: Interaction,
        user: User,
        duration: str,
        reason: app_commands.Transform[
            app_commands.Range[str, 1, 1000], StringToRuleTransformer
        ],
        delete_messages_per: str | None = None,
    ):
        """Mute a user in the server."""
        guild = cast(Guild, interaction.guild)

        member = user

        async with specified_guild_config(
            self.bot,
            guild.id,
            GuildModerationConfig,
            _create=False,
        ) as (guild_config, _):
            moderation_access_roles = guild_config.moderation_access_roles_ids

        is_member_moderator = has_any_role_from_sequence(
            member, moderation_access_roles
        )
        if is_member_moderator:
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка бана пользователя",
                    "Вы не можете забанить модераторов.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if (
            isinstance(member, Member)
            and member.guild_permissions.administrator
        ):
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка бана пользователя",
                    "Вы не можете забанить администраторов.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if not guild.me.guild_permissions.ban_members:
            return await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                    "У меня нет прав на бан участников.",
                ),
                ephemeral=True,
            )

        if guild.me == member:
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка бана пользователя",
                    "Вы не можете забанить меня.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if not compare_top_roles(guild, member):
            return await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                    "Я не могу забанить этого пользователя, потому что у него роль выше моей.",  # noqa: E501
                ),
                ephemeral=True,
            )

        parsed_duration = parse_duration(duration)

        if not parsed_duration:
            return await interaction.response.send_message(
                embed=ValidationErrorEmbed(
                    "Неверная продолжительность. Используйте s/m/h/d (например, 1h, 1d, 7d).",  # noqa: E501
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        parsed_delete_messages_per = 0

        if delete_messages_per:
            tmp_delete_messages_per = parse_duration(delete_messages_per)

            if tmp_delete_messages_per is None:
                return await interaction.response.send_message(
                    embed=ValidationErrorEmbed(
                        "Неверная длительность удаления сообщений. Используйте s/m/h/d (например, 1h, 1d, 7d).",  # noqa: E501
                        self.bot.user.name,  # type: ignore
                        self.bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )

            if tmp_delete_messages_per > config.bot.DELETE_MESSAGES_SECONDS:
                return await interaction.response.send_message(
                    embed=ValidationErrorEmbed(
                        f"Длительность удаления сообщений не может превышать {config.bot.DELETE_MESSAGES_SECONDS // 86400} дней.",  # noqa: E501
                        self.bot.user.name,  # type: ignore
                        self.bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )

            parsed_delete_messages_per = tmp_delete_messages_per

        end_time = calculate_end_time(parsed_duration)

        await interaction.response.defer()

        try:
            await guild.fetch_ban(member)
        except discord.NotFound:
            try:
                data = UserBannedEventData(
                    mode="dm",
                    category=self.__class__.__name__.lower(),
                    guild_id=guild.id,
                    moderator_id=interaction.user.id,
                    user=member,
                    reason=reason,
                    created_at=discord.utils.utcnow().astimezone(tz=UTC),
                    guild_name=guild.name,
                    duration=parsed_duration,
                    original_duration=duration,
                    end_time=end_time,  # type: ignore
                    delete_messages_per=delete_messages_per,
                )
                try:
                    self.bot.dispatch("user_banned", data=data)
                except Exception as e:
                    logger.warning(
                        "[event] - Failed to dispatch user_banned event: %s", e
                    )
                    return

                try:
                    await send_punish_dm_message(
                        self.bot,
                        guild_name=guild.name,
                        event_data=data,  # type: ignore
                    )
                except Exception as e:
                    logger.warning(
                        "[command] - Failed to send ban DM to user=%s guild=%s: %s",
                        member.id,
                        guild.id,
                        e,
                    )

                await guild.ban(
                    member,
                    reason=reason,
                    delete_message_seconds=parsed_delete_messages_per,
                )

            except discord.HTTPException as e:
                logger.warning(
                    "Failed to ban user=%s guild=%s: %s",
                    member.id,
                    guild.id,
                    e,
                )
                return await interaction.followup.send(
                    embed=ErrorEmbed(
                        "Ошибка бана пользователя",
                        "Не удалось забанить пользователя.",
                        self.bot.user.name,  # type: ignore
                        self.bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    view=PunishViewV2(
                        bot=self.bot,
                        user=member,
                        punish_type="ban",
                        moderator_id=interaction.user.id,  # type: ignore
                        duration=duration,
                        reason=reason,
                        mode="server",
                    )
                )
        else:
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Ошибка бана пользователя",
                    f"{user.mention} уже забанен на этом сервере.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        logger.info(
            "[command] - invoked user=%s guild=%s target=%s reason=%s",
            interaction.user.id,
            guild.id,
            user.id,
            reason,
        )


async def _ban_request_callback(
    interaction: Interaction["Nightcore"], user: discord.Member
):
    """Callback for the ban request context menu."""
    guild = cast(Guild, interaction.guild)
    client = interaction.client
    # Ensure we have a guild Member object
    member = await ensure_member_exists(guild, user.id)

    if member is None:
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка отправки запроса на бан",
                "Пользователь не найден на сервере.",
                client.user.name,  # type: ignore
                client.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    async with specified_guild_config(
        client,
        guild.id,
        GuildModerationConfig,
    ) as (guild_config, _):
        if not (
            moderation_access_roles := guild_config.moderation_access_roles_ids
        ):
            raise FieldNotConfiguredError("доступ к модерации")

        if not (
            ban_request_channel_id := guild_config.send_ban_request_channel_id
        ):
            raise FieldNotConfiguredError("канал запросов на бан")

        if not (ban_access_roles := guild_config.ban_access_roles_ids):
            raise FieldNotConfiguredError("доступ к бану")

        ban_request_ping_role_id = guild_config.ban_request_ping_role_id

    has_moder_role = any(
        interaction.user.get_role(role_id)  # type: ignore
        for role_id in moderation_access_roles
    )
    if not has_moder_role:
        return await interaction.response.send_message(
            embed=MissingPermissionsEmbed(
                client.user.name,  # type: ignore
                client.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    is_member_moderator = any(
        member.get_role(role_id) for role_id in moderation_access_roles
    )
    if is_member_moderator:
        return await interaction.response.send_message(
            embed=ValidationErrorEmbed(
                "Вы не можете забанить модераторов.",
                client.user.name,  # type: ignore
                client.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if member.guild_permissions.administrator:
        return await interaction.response.send_message(
            embed=ValidationErrorEmbed(
                "Вы не можете забанить администраторов.",
                client.user.name,  # type: ignore
                client.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if not guild.me.guild_permissions.ban_members:
        return await interaction.response.send_message(
            embed=MissingPermissionsEmbed(
                client.user.name,  # type: ignore
                client.user.display_avatar.url,  # type: ignore
                "У меня нет прав на бан участников.",
            ),
            ephemeral=True,
        )

    if guild.me == member:
        return await interaction.response.send_message(
            embed=ValidationErrorEmbed(
                "Вы не можете забанить меня.",
                client.user.name,  # type: ignore
                client.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if not compare_top_roles(guild, member):
        return await interaction.response.send_message(
            embed=MissingPermissionsEmbed(
                client.user.name,  # type: ignore
                client.user.display_avatar.url,  # type: ignore
                "Я не могу забанить этого пользователя, потому что у него роль выше моей.",  # noqa: E501
            ),
            ephemeral=True,
        )

    role = None
    if ban_request_ping_role_id:
        role = guild.get_role(ban_request_ping_role_id)
        if role is None:
            try:
                role = await guild.fetch_role(ban_request_ping_role_id)
            except discord.NotFound:
                role = None

    channel = await ensure_messageable_channel_exists(
        guild, ban_request_channel_id
    )
    if channel is None:
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка отправки запроса на бан",
                "Канал для отправки запросов на бан не найден.",
                client.user.name,  # type: ignore
                client.user.display_avatar.url,  # type: ignore
            )
        )

    modal = BanFormModal(
        target=user,
        moderator=interaction.user,  # type: ignore
        bot=client,
        ping_role=role,
        channel=channel,  # type: ignore
        ban_access_roles_ids=ban_access_roles,
        moderation_access_roles_ids=moderation_access_roles,
    )

    await interaction.response.send_modal(modal)

    logger.info(
        "[command] - invoked user=%s guild=%s target=%s",
        interaction.user.id,
        guild.id,
        user.id,
    )


async def setup(bot: "Nightcore"):
    """Setup the Ban cog."""
    bot.tree.add_command(
        app_commands.ContextMenu(
            name="Отправить запрос на бан",
            callback=_ban_request_callback,
            extras={"allowed_contexts": AppCommandContext.guild},
        )
    )
    await bot.add_cog(Ban(bot))
