"""Handle the approve role request button interaction."""

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

import discord
from discord import Guild
from discord.components import (
    TextDisplay as TextDisplayOverride,
)
from discord.interactions import Interaction

from src.infra.db.models import GuildNotificationsConfig
from src.infra.db.operations import (
    get_latest_user_role_request,
    get_specified_webhook,
)
from src.nightcore.components.view.v2 import (
    ErrorViewV2,
    MissingPermissionsViewV2,
)
from src.nightcore.features.moderation.events.dto import RolesChangeEventData
from src.nightcore.features.role_requests.utils import send_role_request_dm
from src.nightcore.features.tickets.utils import extract_id_from_str
from src.nightcore.utils import ensure_member_exists, ensure_role_exists
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)
from src.utils._enums import ChannelType, RoleRequestStateEnum

from ..role_request_state import RoleRequestStateView

if TYPE_CHECKING:
    from src.infra.db.models.discord_webhook import DiscordWebhook
    from src.nightcore.bot import Nightcore

    from ..check_role_request import CheckRoleRequestView

logger = logging.getLogger(__name__)


@check_required_permissions(PermissionsFlagEnum.MODERATION_ACCESS)
async def handle_approve(
    interaction: Interaction["Nightcore"],
    view: "CheckRoleRequestView",
) -> None:
    """Handle the approve button interaction."""
    guild = cast(Guild, interaction.guild)
    bot = interaction.client

    if not guild.me.guild_permissions.manage_roles:
        await interaction.response.send_message(
            view=MissingPermissionsViewV2(
                "У меня нет прав для управления ролями.",
            ),
            ephemeral=True,
        )
        return

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
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка одобрения запроса",
                "Пользователь не найден на сервере.",
            ),
            ephemeral=True,
        )
        return

    role = await ensure_role_exists(guild, cast(int, view.role_requested_id))
    if not role:
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка одобрения запроса",
                "Не удалось найти запрашиваемую роль на сервере.",
            ),
            ephemeral=True,
        )
        return

    outcome = ""
    nightcore_notifications_webhook: DiscordWebhook | None = None

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
                last_rr.updated_at = datetime.now(UTC)

                nightcore_notifications_webhook = await get_specified_webhook(
                    session,
                    guild_id=guild.id,
                    config_type=GuildNotificationsConfig,
                    channel_type=ChannelType.NIGHTCORE_NOTIFICATIONS,
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
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка одобрения запроса",
                "Не удалось найти этот запрос на роль в базе данных.",
            ),
            ephemeral=True,
        )
        return

    if outcome == "already_approved":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка одобрения запроса",
                "Другой модератор одобрил этот запрос.",
            ),
            ephemeral=True,
        )
        return

    if outcome == "database_error":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка одобрения запроса",
                "Произошла ошибка при получении запроса на роль "
                "из базы данных.",
            ),
            ephemeral=True,
        )
        return

    if outcome == "success":
        try:
            await member.add_roles(role, reason="Одобрение запроса на роль")
        except Exception as e:
            logger.exception(
                "Failed to add role %s to user %s in guild %s: %s",
                role.id,
                member.id,
                guild.id,
                e,
            )
            await interaction.followup.send(
                view=ErrorViewV2(
                    "Approve failed",
                    "An error occurred while adding the role to the user.",
                ),
                ephemeral=True,
            )
            return

        view.state = RoleRequestStateEnum.APPROVED
        view.moderator_id = interaction.user.id
        updated_view = view.make_component(disable_all=True)
        await interaction.message.edit(view=updated_view)  # type: ignore

        await interaction.followup.send(
            view=RoleRequestStateView(
                bot=bot,
                moderator_id=interaction.user.id,
                user_id=cast(int, view.interaction_user_id),
                roles_ids=cast(list[int], [view.role_requested_id]),
                state=RoleRequestStateEnum.APPROVED,
            )
        )

        await send_role_request_dm(
            bot=bot,
            moderator_id=interaction.user.id,
            reserve_webhook=nightcore_notifications_webhook,
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
                    roles_ids=[role.id],
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
