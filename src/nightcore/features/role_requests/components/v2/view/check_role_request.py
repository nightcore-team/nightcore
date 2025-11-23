"""View for sending role requests."""

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Self, cast

import discord
from discord import ButtonStyle, Color, Guild, MediaGalleryItem
from discord.components import (
    TextDisplay as TextDisplayOverride,
)
from discord.interactions import Interaction
from discord.ui import (
    ActionRow,
    Button,
    Container,
    LayoutView,
    MediaGallery,
    Separator,
    TextDisplay,
    button,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.infra.db.models import GuildNotificationsConfig
from src.infra.db.models._enums import ChannelType, RoleRequestStateEnum
from src.infra.db.operations import (
    get_latest_user_role_request,
    get_specified_channel,
)
from src.nightcore.components.embed import ErrorEmbed, MissingPermissionsEmbed
from src.nightcore.features.moderation.events.dto import RolesChangeEventData
from src.nightcore.features.role_requests.components.modal.decline import (
    DeclineRoleRequestModal,
)
from src.nightcore.features.role_requests.utils import send_role_request_dm
from src.nightcore.features.tickets.utils import extract_id_from_str
from src.nightcore.utils import (
    discord_ts,
    ensure_member_exists,
    ensure_role_exists,
)

from .role_request_state import RoleRequestStateView

logger = logging.getLogger(__name__)


class ManageRoleRequestActionRow(ActionRow["CheckRoleRequestView"]):
    @button(
        label="Одобрить запрос",
        custom_id="role_request:approve",
        style=ButtonStyle.grey,
        emoji="<:check:1442198763694329959>",
    )
    async def approve_role_request(
        self,
        interaction: Interaction["Nightcore"],
        button: Button["CheckRoleRequestView"],
    ) -> None:
        """Handle the approve button interaction."""
        guild = cast(Guild, interaction.guild)
        view = cast("CheckRoleRequestView", self.view)

        bot = interaction.client

        if not guild.me.guild_permissions.manage_roles:
            return await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    bot.user.name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                    "У меня нет прав для управления ролями.",
                ),
                ephemeral=True,
            )

        await interaction.response.defer()

        for component in interaction.message.components:  # type: ignore
            for item in component.children:  # type: ignore
                if isinstance(item, TextDisplayOverride):  # noqa: SIM102
                    if "Пользователь" in item.content:
                        content = item.content
                        content_parts = content.split("\n")
                        view.interaction_user_id = extract_id_from_str(
                            content_parts[0].split()[1].strip()
                        )
                        view.interaction_user_nick = (
                            content_parts[1].split(":")[1].strip()
                        )
                        view.role_requested_id = extract_id_from_str(
                            content_parts[2].split(":")[1].strip()
                        )
                        break

        member = await ensure_member_exists(
            guild,
            cast(int, view.interaction_user_id),
        )
        if not member:
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Ошибка одобрения запроса",
                    "Пользователь не найден на сервере.",
                    bot.user.name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        role = await ensure_role_exists(
            guild, cast(int, view.role_requested_id)
        )
        if not role:
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Ошибка одобрения запроса",
                    "Не удалось найти запрашиваемую роль на сервере.",
                    bot.user.name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        outcome = ""
        nightcore_notifications_channel_id: int | None = None

        async with bot.uow.start() as session:
            try:
                last_rr = await get_latest_user_role_request(
                    session,
                    guild_id=guild.id,
                    user_id=cast(int, view.interaction_user_id),
                )

                if not last_rr:
                    outcome = "request_not_found"
                elif last_rr.state == RoleRequestStateEnum.APPROVED:
                    outcome = "already_approved"
                else:
                    last_rr.state = RoleRequestStateEnum.APPROVED
                    last_rr.moderator_id = interaction.user.id

                    nightcore_notifications_channel_id = (
                        await get_specified_channel(
                            session,
                            guild_id=guild.id,
                            config_type=GuildNotificationsConfig,
                            channel_type=ChannelType.NIGHTCORE_NOTIFICATIONS,
                        )
                    )

                    outcome = "success"

            except Exception as e:
                logger.exception(
                    "Failed to get role request from %s in %s: %s",
                    view.interaction_user_id,
                    guild.id,
                    e,
                )
                outcome = "database_error"

        if outcome == "request_not_found":
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Ошибка одобрения запроса",
                    "Не удалось найти этот запрос на роль в базе данных.",
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if outcome == "already_approved":
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Ошибка одобрения запроса",
                    "Другой модератор одобрил этот запрос.",
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if outcome == "database_error":
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Ошибка одобрения запроса",
                    "Произошла ошибка при получении запроса на роль из базы данных.",  # noqa: E501
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if outcome == "success":
            try:
                await member.add_roles(
                    role, reason="Одобрение запроса на роль"
                )
            except Exception as e:
                logger.exception(
                    "Failed to add role %s to user %s in guild %s: %s",
                    role.id,
                    member.id,
                    guild.id,
                    e,
                )
                return await interaction.followup.send(
                    embed=ErrorEmbed(
                        "Approve failed",
                        "An error occurred while adding the role to the user.",
                        view.bot.user.name,  # type: ignore
                        view.bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )

            view.state = RoleRequestStateEnum.APPROVED
            view.moderator_id = interaction.user.id
            updated_view = view.make_component(disable_all=True)
            await interaction.message.edit(view=updated_view)  # type: ignore

            await interaction.followup.send(
                view=RoleRequestStateView(
                    bot=bot,
                    moderator_id=interaction.user.id,
                    user_id=cast(int, view.interaction_user_id),
                    role_id=cast(int, view.role_requested_id),
                    state=RoleRequestStateEnum.APPROVED,
                )
            )

            await send_role_request_dm(
                moderator_id=interaction.user.id,
                reserve_channel=nightcore_notifications_channel_id,
                user=member,
                state=RoleRequestStateEnum.APPROVED,
            )

            try:
                bot.dispatch(
                    "roles_change",
                    data=RolesChangeEventData(
                        category="role_approve",
                        moderator=interaction.user,  # type: ignore
                        user=member,
                        role=role,
                        created_at=discord.utils.utcnow(),
                    ),
                    _send_to_rr_channel=False,
                )

            except Exception as e:
                logger.exception(
                    "[event] - Failed to dispatch roles_change event: %s", e
                )
                return

            logger.info(
                "Moderator %s approved role request from user %s in guild %s",
                interaction.user.id,
                view.interaction_user_id,
                guild.id,
            )

    @button(
        label="Отклонить запрос",
        custom_id="role_request:decline",
        style=ButtonStyle.grey,
        emoji="<:failed:1442197027822768270>",
    )
    async def decline_role_request(
        self,
        interaction: Interaction["Nightcore"],
        button: Button["CheckRoleRequestView"],
    ) -> None:
        """Handle the decline button interaction."""
        guild = cast(Guild, interaction.guild)
        view = cast("CheckRoleRequestView", self.view)

        if not guild.me.guild_permissions.manage_roles:
            return await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                    "У меня нет прав для управления ролями.",
                ),
                ephemeral=True,
            )

        for component in interaction.message.components:  # type: ignore
            for item in component.children:  # type: ignore
                if isinstance(item, TextDisplayOverride):  # noqa: SIM102
                    if "Пользователь" in item.content:
                        content = item.content
                        content_parts = content.split("\n")
                        view.interaction_user_id = extract_id_from_str(
                            content_parts[0].split()[1].strip()
                        )
                        view.interaction_user_nick = (
                            content_parts[1].split(":")[1].strip()
                        )
                        view.role_requested_id = extract_id_from_str(
                            content_parts[2].split(":")[1].strip()
                        )
                        break

        member = await ensure_member_exists(
            guild,
            cast(int, view.interaction_user_id),
        )
        if not member:
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка отклонения запроса",
                    "Пользователь не найден на сервере.",
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        outcome = ""
        nightcore_notifications_channel_id: int | None = None

        async with view.bot.uow.start() as session:
            try:
                last_rr = await get_latest_user_role_request(
                    session,
                    guild_id=guild.id,
                    user_id=cast(int, view.interaction_user_id),
                )

                if not last_rr:
                    outcome = "request_not_found"
                else:
                    nightcore_notifications_channel_id = (
                        await get_specified_channel(
                            session,
                            guild_id=guild.id,
                            config_type=GuildNotificationsConfig,
                            channel_type=ChannelType.NIGHTCORE_NOTIFICATIONS,
                        )
                    )

                    outcome = "success"

            except Exception as e:
                logger.exception(
                    "Failed to get role request from %s in %s: %s",
                    view.interaction_user_id,
                    guild.id,
                    e,
                )
                outcome = "database_error"

        if outcome == "request_not_found":
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка отклонения запроса",
                    "Не удалось найти этот запрос на роль в базе данных.",
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if outcome == "database_error":
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка отклонения запроса",
                    "Произошла ошибка при получении запроса на роль из базы данных.",  # noqa: E501
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if outcome == "success":
            view.state = RoleRequestStateEnum.DENIED
            view.moderator_id = interaction.user.id
            updated_view = view.make_component(disable_all=True)

            await interaction.response.send_modal(
                DeclineRoleRequestModal(
                    bot=view.bot,
                    user=member,
                    nightcore_notifications_channel_id=nightcore_notifications_channel_id,
                    view=updated_view,
                    state_view=RoleRequestStateView,
                    message=interaction.message,  # type: ignore
                )
            )

            logger.info(
                "Moderator %s initiated decline for role request from user %s in guild %s",  # noqa: E501
                interaction.user.id,
                view.interaction_user_id,
                guild.id,
            )


class CheckRoleRequestView(LayoutView):
    def __init__(
        self,
        bot: "Nightcore",
        interaction_user_id: int | None = None,
        interaction_user_nick: str | None = None,
        role_requested_id: int | None = None,
        moderator_id: int | None = None,
        state: RoleRequestStateEnum | None = None,
        attachments: list[MediaGalleryItem] | None = None,
        all_disabled: bool = False,
    ) -> None:
        super().__init__(timeout=None)
        self.bot = bot
        self.interaction_user_id = interaction_user_id
        self.role_requested_id = role_requested_id
        self.moderator_id = moderator_id
        self.interaction_user_nick = interaction_user_nick
        self.state = state
        self.attachments = attachments

        self.actions: ManageRoleRequestActionRow

        self.make_component(all_disabled)

    def disable_buttons(self):
        """Disable all buttons in the view."""
        if self.actions:
            for item in self.actions.children:
                if isinstance(item, Button):
                    item.disabled = True  # type: ignore

    def make_component(self, disable_all: bool = False) -> Self:
        """Create view."""
        self.clear_items()

        container = Container[Self]()

        # header
        container.add_item(TextDisplay[Self]("## Запрос на роль"))
        container.add_item(Separator[Self]())

        # main text
        container.add_item(
            TextDisplay[Self](
                f"**Пользователь**: <@{self.interaction_user_id}> (`{self.interaction_user_id}`)\n"  # noqa: E501
                f"**Никнейм**: {self.interaction_user_nick}\n"
                f"**Запрашиваемая роль**: <@&{self.role_requested_id}>\n"
            )
        )
        container.add_item(Separator[Self]())

        accent_color: Color | None = None
        # state
        if self.state:
            state_str = ""
            match self.state:
                case RoleRequestStateEnum.APPROVED:
                    accent_color = Color.from_str("#32F113")
                    state_str = f"Запрос на статистику был **одобрен** модератором: <@{self.moderator_id}>"  # noqa: E501
                case RoleRequestStateEnum.DENIED:
                    accent_color = Color.from_str("#F11313")
                    state_str = f"Запрос на статистику был **отклонен** модератором: <@{self.moderator_id}>"  # noqa: E501
                case RoleRequestStateEnum.CANCELED:
                    accent_color = Color.from_str("#F11313")
                    state_str = "Пользователь отменил свой запрос на роль."
                    self.moderator_id = None
                case RoleRequestStateEnum.EXPIRED:
                    accent_color = Color.from_str("#F1F113")
                    state_str = "Запрос на роль **истек**."
                    self.moderator_id = None
                case _:
                    state_str = "Cannot determine state."

            container.add_item(TextDisplay[Self](f"{state_str}"))
            container.add_item(Separator[Self]())

        if accent_color:
            container._colour = accent_color  # type: ignore

        if self.attachments:
            # attachments
            gallery = MediaGallery[Self](*self.attachments)
            container.add_item(gallery)
            container.add_item(Separator[Self]())

        # manage buttons
        self.actions = ManageRoleRequestActionRow()
        container.add_item(self.actions)
        container.add_item(Separator[Self]())

        if disable_all:
            self.disable_buttons()

        # footer
        now = datetime.now(timezone.utc)

        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {self.bot.user.name} in {discord_ts(now)}\n"  # type: ignore
            )
        )

        self.add_item(container)

        return self
