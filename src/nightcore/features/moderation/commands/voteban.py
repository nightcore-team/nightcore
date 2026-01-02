"""Command to send a vote ban request."""

import logging
from typing import TYPE_CHECKING, cast

from discord import (
    Guild,
    User,
    app_commands,
)
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.config.config import config
from src.infra.db.models import GuildModerationConfig
from src.nightcore.components.embed import (
    EntityNotFoundEmbed,
    ErrorEmbed,
    MissingPermissionsEmbed,
    SuccessMoveEmbed,
    ValidationErrorEmbed,
)
from src.nightcore.exceptions import FieldNotConfiguredError
from src.nightcore.features.moderation.components.v2 import (
    BanRequestViewV2,
)
from src.nightcore.features.moderation.utils.transformers import (
    StringToRuleTransformer,
)
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils import (
    compare_top_roles,
    ensure_member_exists,
    ensure_messageable_channel_exists,
    ensure_role_exists,
    has_any_role_from_sequence,
)
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)
from src.nightcore.utils.time_utils import parse_duration

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


class Voteban(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

    @app_commands.command(  # type: ignore
        name="voteban",
        description="Отправить запрос на голосование по бану пользователя",
    )
    @app_commands.guild_only()
    @app_commands.describe(
        user="Пользователь, которого нужно забанить",
        reason="Причина бана пользователя",
        duration="Продолжительность бана (например, 1h, 1d, 7d)",
        delete_messages_per="Удалять сообщения за последний период времени (например, 1h, 1d, 7d)",  # noqa: E501
    )
    @check_required_permissions(PermissionsFlagEnum.MODERATION_ACCESS)  # type: ignore
    async def voteban(
        self,
        interaction: Interaction,
        user: User,
        duration: str,
        reason: app_commands.Transform[
            app_commands.Range[str, 1, 1000], StringToRuleTransformer
        ],
        delete_messages_per: str | None = None,
    ):
        """Vote to ban a user on the server."""
        guild = cast(Guild, interaction.guild)

        ping_role = None

        async with specified_guild_config(
            self.bot,
            guild.id,
            GuildModerationConfig,
        ) as (guild_config, _):
            moderation_access_roles = guild_config.moderation_access_roles_ids

            if not (ban_access_roles := guild_config.ban_access_roles_ids):
                raise FieldNotConfiguredError("доступ к банам")

            if not (
                ban_request_channel_id
                := guild_config.send_ban_request_channel_id
            ):
                raise FieldNotConfiguredError("канал запросов на бан")

            ping_role_id = guild_config.ban_request_ping_role_id

        if ping_role_id:
            ping_role = await ensure_role_exists(guild, ping_role_id)

        if guild.me == user:
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка отправки запроса на блокировку",
                    "Вы не можете заблокировать меня.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if (member := await ensure_member_exists(guild, user.id)) is not None:
            if member.guild_permissions.administrator:
                return await interaction.response.send_message(
                    embed=ErrorEmbed(
                        "Ошибка отправки запроса на блокировку",
                        "Вы не можете заблокировать администраторов.",
                        self.bot.user.name,  # type: ignore
                        self.bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )

            is_member_moderator = has_any_role_from_sequence(
                member, moderation_access_roles
            )

            if is_member_moderator:
                return await interaction.response.send_message(
                    embed=ErrorEmbed(
                        "Ошибка отправки запроса на блокировку",
                        "Вы не можете заблокировать модераторов.",
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
                        "Я не могу забанить этого пользователя, потому что у него роль выше, чем у меня.",  # noqa: E501
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

        parsed_delete_messages_per_seconds = 0

        if delete_messages_per:
            tmp_delete_messages_per = parse_duration(delete_messages_per)

            if tmp_delete_messages_per is None:
                return await interaction.response.send_message(
                    embed=ValidationErrorEmbed(
                        "Неверная продолжительность удаления сообщений. Используйте s/m/h/d (например, 1h, 1d, 7d).",  # noqa: E501
                        self.bot.user.name,  # type: ignore
                        self.bot.user.display_avatar.url,  # type: ignore
                    ),
                )

            if tmp_delete_messages_per > config.bot.DELETE_MESSAGES_SECONDS:
                return await interaction.response.send_message(
                    embed=ValidationErrorEmbed(
                        f"Продолжительность удаления сообщений не может превышать {config.bot.DELETE_MESSAGES_SECONDS // 86400} дней.",  # noqa: E501
                        self.bot.user.name,  # type: ignore
                        self.bot.user.display_avatar.url,  # type: ignore
                    ),
                )

            parsed_delete_messages_per_seconds = tmp_delete_messages_per

        channel = await ensure_messageable_channel_exists(
            guild, ban_request_channel_id
        )
        if not channel:
            return await interaction.response.send_message(
                embed=EntityNotFoundEmbed(
                    "канал",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )
        await interaction.response.defer(thinking=True, ephemeral=True)

        view = BanRequestViewV2(
            author_id=interaction.user.id,
            reason=reason,
            target=user,
            bot=self.bot,
            ping_role=ping_role,
            original_duration=duration,
            duration=parsed_duration,
            original_delete_seconds=delete_messages_per,
            delete_seconds=parsed_delete_messages_per_seconds,
            ban_access_roles_ids=ban_access_roles,
            moderation_access_roles_ids=cast(
                list[int], moderation_access_roles
            ),
        )

        try:
            message = await channel.send(  # type: ignore
                view=view
            )

            await interaction.followup.send(
                embed=SuccessMoveEmbed(
                    "Запрос на бан отправлен",
                    f"Ваш [запрос на бан]({message.jump_url}) для {user.mention} было успешно отправлено.",  # noqa: E501 # type: ignore
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
            )

        except Exception as e:
            logger.exception(
                "Failed to send message in guild %s to channel %s: %s",
                channel.guild.id,
                channel.id,
                e,
            )
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Ошибка отправки запроса на блокировку",
                    "Не удалось отправить сообщение с запросом на блокировку.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                )
            )

        logger.info(
            "[ban_request_submit] - invoked user=%s guild=%s target=%s duration=%s reason=%s delete_messages_for_last=%s",  # noqa: E501
            interaction.user.id,
            channel.guild.id,
            user.id,
            duration,
            reason,
            delete_messages_per,
        )


async def setup(bot: "Nightcore") -> None:
    """Setup the Voteban cog."""
    await bot.add_cog(Voteban(bot))
