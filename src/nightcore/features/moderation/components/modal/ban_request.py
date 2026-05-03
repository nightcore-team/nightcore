"""Modal for submitting ban requests."""

import logging
from typing import TYPE_CHECKING

import discord
from discord import Member
from discord.interactions import Interaction
from discord.ui import FileUpload, Label, Modal, TextInput
from sqlalchemy.exc import IntegrityError

from src.infra.db.models import VoteBanState
from src.nightcore.components.embed import (
    ErrorEmbed,
    SuccessMoveEmbed,
    ValidationErrorEmbed,
)
from src.nightcore.features.moderation.components.v2 import BanRequestViewV2
from src.nightcore.utils.content import is_image_url
from src.nightcore.utils.object import cast_guild
from src.nightcore.utils.time_utils import parse_duration

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


class BanFormModal(Modal, title="Отправить запрос на бан"):
    duration = TextInput["BanFormModal"](
        label="Продолжительность s/m/d/w",
        placeholder="Пример: 30m, 2h, 3d",
        required=True,
        max_length=50,
    )

    reason = TextInput["BanFormModal"](
        label="Причина наказания",
        style=discord.TextStyle.paragraph,
        placeholder="Опишите причину...",
        required=True,
        max_length=1000,
    )

    delete_messages_per = TextInput["BanFormModal"](
        label="Удалить сообщения за последние",
        style=discord.TextStyle.short,
        placeholder="Пример: 1m, 1h, 1d, 7d",
        required=False,
        max_length=20,
    )

    attachment = Label["BanFormModal"](
        text="Вставьте скриншот(ы) доказательств",
        component=FileUpload(required=False, min_values=1, max_values=10),
    )

    def __init__(
        self,
        moderator: Member,
        user: Member,
        voteban_channel: discord.TextChannel | discord.Thread,
        ping_role_id: int | None = None,
    ):
        super().__init__()
        self.user = user
        self.moderator = moderator
        self.ping_role_id = ping_role_id
        self.voteban_channel = voteban_channel

    async def on_submit(self, interaction: Interaction["Nightcore"]) -> None:  # pyright: ignore[reportIncompatibleMethodOverride]
        """Handles the submission of the ban form modal."""

        bot = interaction.client
        guild = cast_guild(interaction.guild)

        reason = self.reason.value

        await interaction.response.defer(ephemeral=True, thinking=True)

        parsed_duration = parse_duration(self.duration.value)
        if parsed_duration is None:
            return await interaction.followup.send(
                embed=ValidationErrorEmbed(
                    "Invalid duration format. Use s/m/h/d (e.g., 30m, 2h, 3d).",  # noqa: E501
                    bot.user.name,
                    bot.user.display_avatar.url,
                ),
                ephemeral=True,
            )

        parsed_delete_messages_per = None
        original_delete_messages_per = ""

        if self.delete_messages_per.value:
            parsed_delete_messages_per = parse_duration(
                self.delete_messages_per.value
            )
            if parsed_delete_messages_per is None:
                return await interaction.followup.send(
                    embed=ValidationErrorEmbed(
                        "Неверная продолжительность. Используйте s/m/h/d до 7d (например, 30m, 2h, 3d).",  # noqa: E501
                        bot.user.name,
                        bot.user.display_avatar.url,
                    ),
                )

            if (
                parsed_delete_messages_per
                > bot.config.bot.DELETE_MESSAGES_SECONDS
            ):
                return await interaction.followup.send(
                    embed=ValidationErrorEmbed(
                        f"Продолжительность удаления сообщений не может превышать {bot.config.bot.DELETE_MESSAGES_SECONDS // 86400} дней.",  # noqa: E501
                        bot.user.name,
                        bot.user.display_avatar.url,
                    ),
                )

            original_delete_messages_per = self.delete_messages_per.value

        attachments_urls: list[str] = []
        if attachments := self.attachment.component.values:  # type: ignore (list[Attachment])
            for attachment in attachments:  # type: ignore
                content_type = getattr(attachment, "content_type", None)  # type: ignore
                if content_type and not content_type.startswith("image/"):
                    continue

                filename = getattr(attachment, "filename", "")  # type: ignore
                if filename and not is_image_url(filename):
                    continue

                if not is_image_url(attachment.url):  # type: ignore
                    continue

                attachments_urls.append(attachment.url)  # type: ignore

        try:
            async with bot.uow.start() as session:
                votebanstate = VoteBanState(
                    guild_id=guild.id,
                    moderator_id=self.moderator.id,
                    user_id=self.user.id,
                    reason=reason,
                    original_duration=self.duration.value,
                    duration=parsed_duration,
                    original_delete_messages_per=self.delete_messages_per.value,
                    delete_messages_per=original_delete_messages_per,
                    attachments_urls=attachments_urls,
                )

                session.add(votebanstate)
                await session.flush()

        except IntegrityError:
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Ошибка отправки запроса на блокировку",
                    "Пользователь уже имеет активный запрос на блокировку.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                )
            )

        view = BanRequestViewV2(
            bot=bot,
            moderator_id=votebanstate.moderator_id,
            user=self.user,
            reason=votebanstate.reason,
            original_duration=votebanstate.original_duration,
            original_delete_messages_per=votebanstate.original_delete_messages_per,
            ping_role_id=self.ping_role_id,
        ).create_component()

        try:
            message = await self.voteban_channel.send(view=view)

            await interaction.followup.send(
                embed=SuccessMoveEmbed(
                    "Запрос на бан отправлен",
                    f"Ваш [запрос на бан]({message.jump_url}) для {self.user.mention} было успешно отправлено.",  # noqa: E501 # type: ignore
                    bot.user.name,
                    bot.user.display_avatar.url,
                ),
            )

        except Exception as e:
            logger.exception(
                "Failed to send message in guild %s to channel %s: %s",
                guild.id,
                self.voteban_channel.id,
                e,
            )
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Запрос на бан не удался",
                    "Не удалось отправить сообщение с запросом на бан.",
                    bot.user.name,
                    bot.user.display_avatar.url,
                )
            )

        logger.info(
            "[ban_request_submit] - invoked user=%s guild=%s target=%s duration=%s reason=%s delete_messages_for_last=%s",  # noqa: E501
            self.moderator.id,
            guild.id,
            self.user.id,
            self.duration.value,
            reason,
            self.delete_messages_per.value,
        )
