"""Modal for submitting inactive requests."""

import logging
from typing import TYPE_CHECKING, Self

from discord import SelectOption, TextStyle
from discord.interactions import Interaction
from discord.ui import Label, Modal, Select, TextInput

from src.infra.db.models import GuildModerationConfig
from src.infra.db.operations import (
    get_guild_forum_config,
    get_specified_guild_config,
)
from src.nightcore.components.embed import (
    EntityNotFoundEmbed,
    ErrorEmbed,
    SuccessMoveEmbed,
)
from src.nightcore.exceptions import FieldNotConfiguredError
from src.nightcore.features.moderation.components.v2 import (
    InactiveRequestViewV2,
)
from src.nightcore.utils import ensure_messageable_channel_exists
from src.nightcore.utils.object import cast_guild
from src.utils._enums import InactiveRequestStateEnum

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


class InactiveFormModal(Modal, title="Отправить заявку на неактив"):
    date_range = TextInput[Self](
        label="Дата отпуска/неактива",
        placeholder="Укажите в формате: с хх/хх/хххх по хх/хх/хххх",
        required=True,
        max_length=50,
    )

    reason = TextInput[Self](
        label="Причина",
        style=TextStyle.paragraph,
        placeholder="Опишите причину...",
        required=True,
        max_length=1000,
    )

    dm_notified = Label[Self](
        text="Уведомили ли вы своего дискорд мастера?",
        component=Select[Self](
            placeholder="Да/Нет",
            required=True,
            options=[
                SelectOption(label="Да", value=str(True)),
                SelectOption(label="Нет", value=str(False)),
            ],
        ),
    )

    async def on_submit(self, interaction: Interaction["Nightcore"]):  # type: ignore
        """Handle the submission of the inactive form."""

        bot = interaction.client
        guild = cast_guild(interaction.guild)

        nickname = interaction.user.display_name

        date_range = self.date_range.value
        reason = self.reason.value
        dm_notified = bool(self.dm_notified.component.values[0])  # type: ignore

        try:
            async with bot.uow.start() as session:
                forum_config = await get_guild_forum_config(
                    session, guild_id=guild.id
                )
                if not forum_config or not forum_config.prefix_id:
                    raise FieldNotConfiguredError("префикс сервера на форуме")
                else:
                    moderation_config = await get_specified_guild_config(
                        session,
                        config_type=GuildModerationConfig,
                        guild_id=guild.id,
                    )
                    if (
                        not moderation_config
                        or not moderation_config.inactive_channel_id
                    ):
                        raise FieldNotConfiguredError("канал для неактива")

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

        try:
            inactive_channel = await ensure_messageable_channel_exists(
                guild, moderation_config.inactive_channel_id
            )
            if inactive_channel is None:
                return await interaction.response.send_message(
                    embed=EntityNotFoundEmbed(
                        "канал для неактива",
                        bot.user.name,
                        bot.user.display_avatar.url,
                    ),
                    ephemeral=True,
                )

            message = f"""
1. Ник: {nickname}
2. Дата отпуска/неактива: {date_range}
3. Причина: {reason}
4. Уведомили ли вы своего дискорд мастера?: {"Да" if dm_notified else "Нет"}"""

            view = InactiveRequestViewV2(
                bot=bot,
                author_id=interaction.user.id,
                message=message,
                state=InactiveRequestStateEnum.PENDING,
                ping_role_id=forum_config.role_id,
            )

            message = await inactive_channel.send(view=view)  # type: ignore

        except Exception as e:
            logger.exception(
                "[inactive] Failed to process inactive request for user=%s: %s",  # noqa: E501
                interaction.user.id,
                e,
            )
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка отправки запроса не неактив",
                    "Не удалить отправить запрос на неактив",
                    bot.user.name,
                    bot.user.display_avatar.url,
                ),
                ephemeral=True,
            )

        url = message.jump_url  # type: ignore

        await interaction.response.send_message(
            embed=SuccessMoveEmbed(
                "Заявка на неактив отправлена",
                f"Ваша заявка на неактив успешно отправлена: {url}.",
                bot.user.name,
                bot.user.display_avatar.url,
            ),
            ephemeral=True,
        )
        logger.info(
            "[inactive] - submitted inactive request user=%s thread_url=%s",
            interaction.user.id,
            url,  # type: ignore
        )


class InactiveRejectModal(Modal, title="Отклонение заявки на неактив"):
    def __init__(self) -> None:
        super().__init__(custom_id="inactive_modal:reject")

    reason = TextInput[Self](
        label="Причина отклонения",
        style=TextStyle.paragraph,
        placeholder="Введите причину отклонения заявки.",
        required=True,
        max_length=100,
    )
