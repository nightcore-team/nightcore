"""Handlers for inactive request buttons."""

import logging
from typing import TYPE_CHECKING

from discord.interactions import Interaction
from nightforo.types.thread.params import ThreadCreateParams

from src.infra.db.models._enums import InactiveRequestStateEnum
from src.infra.db.models.guild import GuildModerationConfig
from src.infra.db.operations import (
    get_guild_forum_config,
    get_specified_guild_config,
)
from src.nightcore.exceptions import (
    ConfigMissingError,
    FieldNotConfiguredError,
)
from src.nightcore.features.moderation.utils.content import (
    parse_author_id_from_components,
    parse_inactive_text_from_components,
    parse_nickname_from_components,
    remove_emoji_from_text,
)
from src.nightcore.utils import has_any_role_from_sequence
from src.nightcore.utils.object import cast_guild, cast_message

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.components.embed import ErrorEmbed
from src.nightcore.features.moderation.components.modal import (
    InactiveRejectModal,
)

from ..inactive import InactiveRequestViewV2

logger = logging.getLogger(__name__)


async def handle_inactive_request_button_callback(
    interaction: Interaction["Nightcore"], custom_id: str
):
    """Handle inactive request button callback."""

    bot = interaction.client
    guild = cast_guild(interaction.guild)
    _, author_id, action = custom_id.split(":")

    try:
        author_id = int(author_id)
    except ValueError:
        logger.error(
            "[inactive] Invalid author ID in custom_id: %s", custom_id
        )
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка обработки запроса на неактив",
                "Некорректный идентификатор автора в данных кнопки.",
                interaction.client.user.name,
                interaction.client.user.display_avatar.url,
            ),
            ephemeral=True,
        )

    async with bot.uow.start() as session:
        guild_config = await get_specified_guild_config(
            session, config_type=GuildModerationConfig, guild_id=guild.id
        )

    if guild_config is None:
        logger.error(
            "[inactive] Guild moderation config not found for guild_id=%s",
            guild.id,
        )
        raise ConfigMissingError(guild.id)

    if interaction.user.id == author_id:
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка обработки запроса на неактив",
                "Вы не можете одобрить или отклонить свой собственный запрос.",
                bot.user.name,
                bot.user.display_avatar.url,
            ),
            ephemeral=True,
        )

    if not has_any_role_from_sequence(
        interaction.user, guild_config.leadership_access_roles_ids
    ):
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка обработки запроса на неактив",
                "У вас нет прав для одобрения или отклонения этого запроса.",
                bot.user.name,
                bot.user.display_avatar.url,
            ),
            ephemeral=True,
        )

    match action:
        case "approve":
            await handle_inactive_request_approve_button(interaction)

        case "deny":
            await interaction.response.send_modal(InactiveRejectModal())

        case _:
            ...


async def handle_inactive_request_approve_button(
    interaction: Interaction["Nightcore"],
):
    """Handle approve button for inactive request."""

    bot = interaction.client
    guild = cast_guild(interaction.guild)
    message = cast_message(interaction.message)

    author_id = parse_author_id_from_components(message.components)
    if not author_id:
        logger.error(
            "[inactive] Failed to parse author ID from message components for guild=%s, message_id=%s",  # noqa: E501
            guild.id,
            message.id,
        )
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка отправки запроса не неактив",
                "Не удалось определить автора запроса на неактив.",
                bot.user.name,
                bot.user.display_avatar.url,
            ),
            ephemeral=True,
        )

    inactive_message = parse_inactive_text_from_components(message.components)
    if not inactive_message:
        logger.error(
            "[inactive] Failed to parse inactive message from message components for guild=%s, message_id=%s",  # noqa: E501
            guild.id,
            message.id,
        )
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка отправки запроса не неактив",
                "Не удалось определить текст запроса на неактив.",
                bot.user.name,
                bot.user.display_avatar.url,
            ),
            ephemeral=True,
        )
    nickname = parse_nickname_from_components(message.components)
    if not nickname:
        logger.error(
            "[inactive] Failed to parse nickname from message components for guild=%s, message_id=%s",  # noqa: E501
            guild.id,
            message.id,
        )
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка отправки запроса не неактив",
                "Не удалось определить никнейм в запросе на неактив.",
                bot.user.name,
                bot.user.display_avatar.url,
            ),
            ephemeral=True,
        )

    nickname = remove_emoji_from_text(nickname)

    try:
        async with bot.uow.start() as session:
            forum_config = await get_guild_forum_config(
                session, guild_id=guild.id
            )
            if forum_config is None:
                raise ConfigMissingError(guild.id)
            elif not forum_config.prefix_id:
                raise FieldNotConfiguredError("префикс для неактива")

    except Exception as e:
        logger.exception(
            "[inactive] Failed to retrieve forum config for guild=%s: %s",
            guild.id,
            e,
        )
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка отправки запроса не неактив",
                "Произошла ошибка при отправке запроса на неактив.",
                bot.user.name,
                bot.user.display_avatar.url,
            ),
            ephemeral=True,
        )

    view = InactiveRequestViewV2(
        bot=bot,
        author_id=author_id,
        message=inactive_message,
        state=InactiveRequestStateEnum.APPROVED,
    )

    await interaction.response.defer()

    try:
        await message.edit(view=view)
    except Exception as e:
        logger.exception(
            "[inactive] Failed to edit message with new view for guild=%s: %s",
            guild.id,
            e,
        )
        return await interaction.followup.send(
            embed=ErrorEmbed(
                "Ошибка отправки запроса не неактив",
                "Произошла ошибка при изменении сообщения о неактиве.",
                bot.user.name,
                bot.user.display_avatar.url,
            ),
            ephemeral=True,
        )

    try:
        result = await bot.apis.forum.create_thread(
            params=ThreadCreateParams(
                node_id=bot.config.bot.INACTIVE_FORUM_NODE_ID,
                title=nickname,
                message=inactive_message,
                prefix_id=forum_config.prefix_id,
            )
        )
    except Exception as e:
        logger.exception(
            "[inactive] Failed to send approval confirmation message for guild=%s: %s",  # noqa: E501
            guild.id,
            e,
        )
        return await interaction.followup.send(
            embed=ErrorEmbed(
                "Ошибка создания темы на форуме",
                "Произошла ошибка при создании темы на форуме.",
                bot.user.name,
                bot.user.display_avatar.url,
            ),
            ephemeral=True,
        )

    url = result.thread.view_url

    await interaction.followup.send(
        f"Заявление на неактив одобрено. [Посмотреть тему на форуме]({url}).",
        ephemeral=True,
    )
