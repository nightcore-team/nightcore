"""Handle the decline role request button interaction."""

import logging
from typing import TYPE_CHECKING, cast

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
from src.nightcore.features.role_requests.components.modal.decline import (
    DeclineRoleRequestModal,
)
from src.nightcore.features.tickets.utils import extract_id_from_str
from src.nightcore.utils import ensure_member_exists
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
async def handle_decline(
    interaction: Interaction["Nightcore"],
    view: "CheckRoleRequestView",
) -> None:
    """Handle the decline button interaction."""
    guild = cast(Guild, interaction.guild)

    if not guild.me.guild_permissions.manage_roles:
        await interaction.response.send_message(
            view=MissingPermissionsViewV2(
                "У меня нет прав для управления ролями.",
            ),
            ephemeral=True,
        )
        return

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
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка отклонения запроса",
                "Пользователь не найден на сервере.",
            ),
            ephemeral=True,
        )
        return

    outcome = ""
    nightcore_notifications_webhook: DiscordWebhook | None = None

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
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка отклонения запроса",
                "Не удалось найти этот запрос на роль в базе данных.",
            ),
            ephemeral=True,
        )
        return

    if outcome == "database_error":
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка отклонения запроса",
                "Произошла ошибка при получении запроса на роль "
                "из базы данных.",
            ),
            ephemeral=True,
        )
        return

    if outcome == "success":
        view.state = RoleRequestStateEnum.DENIED
        view.moderator_id = interaction.user.id
        updated_view = view.make_component(disable_all=True)

        await interaction.response.send_modal(
            DeclineRoleRequestModal(
                bot=view.bot,
                user=member,
                nightcore_notifications_webhook=nightcore_notifications_webhook,
                view=updated_view,
                state_view=RoleRequestStateView,
                message=interaction.message,  # type: ignore
            )
        )

        logger.info(
            "Moderator %s initiated decline for role request "
            "from user %s in guild %s",
            interaction.user.id,
            view.interaction_user_id,
            guild.id,
        )
