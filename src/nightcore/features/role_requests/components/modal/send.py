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
    MissingPermissionsEmbed,
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

        if not guild.me.guild_permissions.manage_nicknames:
            return await interaction.followup.send(
                embed=MissingPermissionsEmbed(
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                    "I do not have permission to manage messages.",
                ),
                ephemeral=True,
            )

        nickname = validate_user_nickname(self.nickname.value)
        if not nickname:
            return await interaction.followup.send(
                embed=ValidationErrorEmbed(
                    "Invalid nickname format. Please use Name_Surname.",
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
                    "Invalid rank format. Please enter a valid number.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if 1 > rank > 11:
            return await interaction.followup.send(
                embed=ValidationErrorEmbed(
                    "Rank must be between 1 and 10.",
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
            member = await user.edit(
                nick=f"[{self.selected_role_tag}][{rank}] {nickname}",
            )

        view = self.view(
            bot=self.bot,
            interaction_user_id=user.id,
            interaction_user_nick=cast(discord.Member, member).display_name,  # type: ignore
            role_requested_id=self.requested_role.id,
            attachments=[MediaGalleryItem(attachment.url)],  # type: ignore
        )

        try:
            message = await self.channel.send(view=view)  # type: ignore

            await interaction.followup.send(
                embed=SuccessMoveEmbed(
                    "Role Request Submitted",
                    "Your role request has sent successfully.",
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
                    "Ban Request Failed",
                    "Failed to send ban request message.",
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
                    author_id=user.id,
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
                    user.id,
                    e,
                )
                outcome = "role_request_create_failed"

        if outcome == "role_request_create_failed":
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Role Request Failed",
                    "Failed to create role request in database.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        logger.info(
            "[role_request_submit] - invoked user=%s guild=%s role=%s",
            user.id,
            guild.id,
            self.requested_role.id,
        )
