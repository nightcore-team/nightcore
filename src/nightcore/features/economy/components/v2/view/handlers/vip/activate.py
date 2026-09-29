"""Handle VIP-status activation button."""

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from discord import Forbidden, Guild, HTTPException, Member, Role
from discord.interactions import Interaction

from src.infra.db.loads import vip_status_load_vip
from src.infra.db.operations import (
    get_guild_vip_statuses,
    get_or_create_user,
    get_user_vip_statuses_for_update,
    get_vip_status_by_id,
)
from src.nightcore.components.view.v2 import ErrorViewV2, SuccessViewV2
from src.nightcore.features.economy.components.v2 import (
    VipStatusActivateViewV2,
)
from src.nightcore.features.economy.utils.pages import (
    build_user_vip_statuses_content,
)
from src.nightcore.utils import ensure_role_exists

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


async def handle_vip_activate_button(
    interaction: Interaction["Nightcore"],
    *,
    vip_id: int,
) -> None:
    """Activate the user's VIP-status and update the activate view."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)
    member = cast(Member, interaction.user)

    await interaction.response.defer()

    outcome = ""
    vip_name = ""
    role_id_to_give: int | None = None
    old_role_ids_to_remove: list[int] = []

    now = datetime.now(UTC)

    async with bot.uow.start() as session:
        user_record, _ = await get_or_create_user(
            session,
            guild_id=guild.id,
            user_id=member.id,
        )

        # the previously active row's VIP is read below for its role, and
        # a lazy load of it on the async session raises MissingGreenlet
        user_vip_statuses = await get_user_vip_statuses_for_update(
            session,
            guild_id=guild.id,
            user_id=user_record.id,
            options=[vip_status_load_vip],
            for_update=True,
        )

        target = next(
            (row for row in user_vip_statuses if row.vip_id == vip_id),
            None,
        )

        if target is None:
            outcome = "vip_not_found"
        elif target.expires_at is not None and target.expires_at <= now:
            outcome = "vip_expired"
        elif target.is_active:
            outcome = "already_active"
        else:
            vip_status = await get_vip_status_by_id(
                session, guild_id=guild.id, vip_id=vip_id
            )

            if vip_status is None:
                outcome = "vip_not_found"
            else:
                vip_name = vip_status.name
                role_id_to_give = vip_status.role_id

                deactivated = [
                    row for row in user_vip_statuses if row.is_active
                ]

                if deactivated:
                    for row in deactivated:
                        row.is_active = False

                        if row.vip.role_id is not None:
                            old_role_ids_to_remove.append(row.vip.role_id)

                    # the unique index on the active row can't be deferred,
                    # and the flush orders the UPDATEs by primary key, so an
                    # older VIP would be set active while the current one
                    # still is - the old one has to be written off first
                    await session.flush()

                target.is_active = True
                outcome = "activated"

    additional_outcome = ""
    if outcome == "activated":
        if role_id_to_give is not None:
            role = await ensure_role_exists(guild, role_id_to_give)

            if role is None:
                outcome = "role_not_assigned"
            else:
                try:
                    await member.add_roles(
                        role, reason="Активация VIP-статуса"
                    )
                except (Forbidden, HTTPException) as e:
                    logger.error(
                        "[vip/activate] Failed to add role %s to user %s: %s",
                        role_id_to_give,
                        member.id,
                        e,
                    )
                    outcome = "role_not_assigned"

        old_roles_to_remove: list[Role] = []

        for old_role_id in old_role_ids_to_remove:
            if old_role_id == role_id_to_give:
                continue

            old_role = await ensure_role_exists(guild, old_role_id)

            if old_role is None or old_role not in member.roles:
                continue

            old_roles_to_remove.append(old_role)

        try:
            await member.remove_roles(
                *old_roles_to_remove, reason="Активация другого VIP-статуса."
            )
        except (Forbidden, HTTPException) as e:
            logger.error(
                "[vip/activate] Failed to remove old roles from user %s: %s",
                member.id,
                e,
            )
            additional_outcome = "role_not_removed"

    if outcome == "vip_not_found":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка активации VIP-статуса",
                "VIP-статус не найден у вас.",
            ),
            ephemeral=True,
        )
        return

    if outcome == "vip_expired":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка активации VIP-статуса",
                "Срок действия данного VIP-статуса истёк.",
            ),
            ephemeral=True,
        )
        return

    if outcome == "already_active":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка активации VIP-статуса",
                "Данный VIP-статус уже активирован.",
            ),
            ephemeral=True,
        )
        return

    if outcome == "role_not_assigned":
        role_error = SuccessViewV2(
            "Активация VIP-статуса.",
            "VIP-статус активирован, но не удалось выдать роль."
            "\n> Не удалось снять роли предыдущих VIP-статусов."
            if additional_outcome
            else "",
        )
    else:
        role_error = None

    async with bot.uow.start() as session:
        user_vip_rows = await get_user_vip_statuses_for_update(
            session,
            guild_id=guild.id,
            user_id=user_record.id,
            for_update=False,
        )
        guild_vip_statuses = await get_guild_vip_statuses(
            session, guild_id=guild.id
        )

    content, statuses = build_user_vip_statuses_content(
        user_vip_rows, guild_vip_statuses
    )

    view = VipStatusActivateViewV2(bot=bot, content=content, statuses=statuses)

    await interaction.followup.edit_message(
        interaction.message.id,  # type: ignore
        view=view,
    )
    await interaction.followup.send(
        view=role_error
        or SuccessViewV2(
            "VIP-статус активирован",
            f"VIP-статус **{vip_name}** был успешно активирован.",
        ),
        ephemeral=True,
    )
