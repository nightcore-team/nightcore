"""Modal for submitting inactive requests."""

import logging
from typing import TYPE_CHECKING, Self

from discord import SelectOption, TextStyle
from discord.interactions import Interaction
from discord.ui import Label, Modal, Select, TextInput
from nightforo.types.thread.params import ThreadCreateParams

from src.nightcore.components.embed import ErrorEmbed, SuccessMoveEmbed

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

        nickname = interaction.user.display_name

        date_range = self.date_range.value
        reason = self.reason.value
        dm_notified = bool(self.dm_notified.component.values[0])  # type: ignore

        message = f"""
            1. Ник: {nickname}
            2. Дата отпуска/неактива: {date_range}
            3. Причина: {reason}
            4. Уведомили ли вы своего дискорд мастера?: {"Да" if dm_notified else "Нет"}
        """  # noqa: E501

        try:
            result = await bot.apis.forum.create_thread(
                params=ThreadCreateParams(
                    node_id=bot.config.bot.INACTIVE_FORUM_NODE_ID,
                    title=f"{nickname}",
                    message=message,
                )
            )

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

        url = result.thread.view_url

        await interaction.response.send_message(
            embed=SuccessMoveEmbed(
                "Заявка на неактив отправлена",
                f"Ваша заявка на неактив успешно отправлена. Вы можете отслеживать статус заявки по [ссылке]({url}).",  # noqa: E501
                bot.user.name,
                bot.user.display_avatar.url,
            ),
            ephemeral=True,
        )
        logger.info(
            "[inactive] - submitted inactive request user=%s thread_url=%s",
            interaction.user.id,
            url,
        )
