"""Handle the remove organization roles button interaction."""

import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING, cast

from discord import Guild, Member, Role
from discord.interactions import Interaction

from src.infra.db.operations import get_organization_roles_ids
from src.nightcore.components.view.v2 import ErrorViewV2, SuccessViewV2
from src.nightcore.utils import (
    ensure_role_exists,
    has_any_role_from_sequence,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

    from ..send_role_request import SendRoleRequestView

logger = logging.getLogger(__name__)


async def handle_remove_roles(
    interaction: Interaction["Nightcore"],
    view: "SendRoleRequestView",
) -> None:
    """Handle the remove roles button interaction."""
    guild = cast(Guild, interaction.guild)
    user = cast(Member, interaction.user)

    outcome = ""
    org_roles_ids: Sequence[int] = []

    async with view.bot.uow.start() as session:
        org_roles_ids = await get_organization_roles_ids(
            session, guild_id=guild.id
        )

        outcome = "no_org_roles_configured" if not org_roles_ids else "success"

    if outcome == "no_org_roles_configured":
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Не удалось снять организационные роли",
                "Организационные роли не настроены на этом сервере.",
            ),
            ephemeral=True,
        )
        return

    if outcome == "success":
        if not has_any_role_from_sequence(user, org_roles_ids):
            await interaction.response.send_message(
                view=ErrorViewV2(
                    "Не удалось снять организационные роли",
                    "У вас нет ролей для снятия.",
                ),
                ephemeral=True,
            )
            return

        await interaction.response.defer(thinking=True, ephemeral=True)

        roles_to_remove: list[Role] = []
        for role_id in org_roles_ids:
            role = await ensure_role_exists(guild, role_id)
            if role and role in user.roles:
                roles_to_remove.append(role)

        try:
            await user.remove_roles(
                *roles_to_remove,
                reason="Снятие организационных ролей",
            )
        except Exception as e:
            logger.error(
                "Failed to remove organization roles from user %s "
                "in guild %s: %s",
                user.id,
                guild.id,
                e,
            )
            await interaction.followup.send(
                view=ErrorViewV2(
                    "Не удалось снять организационные роли",
                    "Произошла ошибка при снятии ваших ролей.",
                ),
            )
            return

        await interaction.followup.send(
            view=SuccessViewV2(
                "Снятие ролей успешно",
                f"Ваши организационные роли "
                f"({', '.join(f'<@&{role.id}>' for role in roles_to_remove)})"
                f" были сняты.",
            ),
        )

        logger.info(
            "User %s removed organization roles in guild %s: %s",
            user.id,
            guild.id,
            [role.id for role in roles_to_remove],
        )
