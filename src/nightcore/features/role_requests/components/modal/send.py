"""Modal for submitting ban requests."""

import logging
from typing import TYPE_CHECKING, Self, cast

import discord
from discord import MediaGalleryItem
from discord.ui import FileUpload, Label, Modal, TextInput

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore
    from src.nightcore.features.role_requests.components.v2.view.check_role_request import (  # noqa: E501
        CheckRoleRequestView,
    )

import contextlib

from src.infra.db.models import RoleRequestState
from src.infra.db.models._enums import RoleRequestStateEnum
from src.nightcore.components.embed import (
    ErrorEmbed,
    SuccessMoveEmbed,
    ValidationErrorEmbed,
)
from src.nightcore.features.role_requests.utils import validate_user_nickname

logger = logging.getLogger(__name__)


class SendRoleRequestModal(Modal, title="Отправить запрос роли"):
    nickname = TextInput[Self](
        label="Введите ваш ник в формате: Имя_Фамилия",
        style=discord.TextStyle.short,
        placeholder="Пример: Raymond_Walker",
        required=True,
        max_length=35,
    )

    rank = TextInput[Self](
        label="Введите ваш ранг",
        style=discord.TextStyle.short,
        placeholder="Пример: 1",
        required=True,
        max_length=2,
    )

    label = Label[Self](
        text="Вставьте скриншот игровой статистики",
        component=FileUpload(
            required=True,
        ),
    )

    def __init__(
        self,
        channel: discord.abc.GuildChannel | discord.Thread,
        role: discord.Role,
        selected_role_tag: str,
        bot: "Nightcore",
        view: type["CheckRoleRequestView"],
    ):
        super().__init__()
        self.bot = bot
        self.channel = channel
        self.requested_role = role
        self.selected_role_tag = selected_role_tag
        self.view = view

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Handles the submission of the ban form modal."""
        guild = cast(discord.Guild, interaction.guild)
        user = cast(discord.Member, interaction.user)

        await interaction.response.defer()

        nickname = validate_user_nickname(self.nickname.value)
        if not nickname:
            return await interaction.followup.send(
                embed=ValidationErrorEmbed(
                    "Неверный формат никнейма. Пожалуйста, используйте Name_Surname.",  # noqa: E501
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        try:
            rank = int(self.rank.value)
        except ValueError:
            return await interaction.followup.send(
                embed=ValidationErrorEmbed(
                    "Неверный формат ранга. Пожалуйста, введите действительное число.",  # noqa: E501
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if 1 > rank > 11:
            return await interaction.followup.send(
                embed=ValidationErrorEmbed(
                    "Ранг должен быть между 1 и 10.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        attachment: discord.Attachment = self.label.component.values[0]  # type: ignore
        if not attachment or not attachment.filename.lower().endswith(  # type: ignore
            (  # type: ignore
                ".png",
                ".jpg",
                ".jpeg",
                ".webp",
            )
        ):
            return await interaction.followup.send(
                embed=ValidationErrorEmbed(
                    "Пожалуйста отправьте валидный файл изображения (png, jpg, jpeg, webp).",  # noqa: E501
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        with contextlib.suppress(Exception):
            user = await user.edit(
                nick=f"[{self.selected_role_tag}][{rank}] {nickname}",
            )

        view = self.view(
            bot=self.bot,
            interaction_user_id=user.id,  # type: ignore
            interaction_user_nick=user.display_name,  # type: ignore
            role_requested_id=self.requested_role.id,
            attachments=[MediaGalleryItem(attachment.url)],  # type: ignore
        )

        try:
            message = await self.channel.send(view=view)  # type: ignore

            await interaction.followup.send(
                embed=SuccessMoveEmbed(
                    "Отправка запроса на роль",
                    "Ваш запрос на роль был успешно отправлен.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        except Exception as e:
            logger.exception(
                "Failed to send message in guild %s to channel %s: %s",
                self.channel.guild.id,
                self.channel.id,
                e,
            )
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Ошибка отправки запроса на роль",
                    "Не удалось отправить сообщение о запросе на роль.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        outcome = ""
        async with self.bot.uow.start() as session:
            try:
                new_rr = RoleRequestState(
                    guild_id=guild.id,
                    author_id=user.id,  # type: ignore
                    role_id=self.requested_role.id,
                    message_id=cast(discord.Message, message).id,
                    channel_id=self.channel.id,
                    state=RoleRequestStateEnum.PENDING,
                )
                session.add(new_rr)
            except Exception as e:
                logger.exception(
                    "Failed to create RoleRequestState in guild %s for user %s: %s",  # noqa: E501
                    guild.id,
                    user.id,  # type: ignore
                    e,
                )
                outcome = "role_request_create_failed"

        if outcome == "role_request_create_failed":
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Ошибка отправки запроса на роль",
                    "Не удалось создать запись запроса на роль в базе данных.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        logger.info(
            "[role_request_submit] - invoked user=%s guild=%s role=%s",
            user.id,  # type: ignore
            guild.id,
            self.requested_role.id,
        )
