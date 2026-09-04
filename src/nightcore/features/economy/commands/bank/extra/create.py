"""Command to check user's bank account."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, app_commands
from discord.interactions import Interaction

from src.config.config import config
from src.infra.db.operations import (
    create_extra_wallet,
    get_or_create_bank_account,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.components.view.v2 import ErrorViewV2, SuccessViewV2
from src.nightcore.features.economy._groups import extra as extra_group
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

logger = logging.getLogger(__name__)


@extra_group.command(  # type: ignore
    name="create",
    description="Создать дополнительный счёт в банке.",
)
@app_commands.guild_only()
@check_required_permissions(PermissionsFlagEnum.NONE)  # type: ignore
async def extra_create(interaction: Interaction["Nightcore"]):
    """Create new extra wallet."""

    guild = cast(Guild, interaction.guild)

    outcome = ""

    await interaction.response.defer(thinking=True, ephemeral=True)

    try:
        async with interaction.client.uow.start() as session:
            bank_account, _ = await get_or_create_bank_account(
                session,
                guild_id=guild.id,
                user_id=interaction.user.id,
                for_update=True,
            )
            wallets_count = len(bank_account.extra_wallets)

            if wallets_count >= config.bot.MAX_EXTRA_WALLETS:
                outcome = "max_wallets_limit_exceeded"

            if not outcome:
                new_extra_wallet = await create_extra_wallet(
                    session, bank_account_id=bank_account.id
                )
                outcome = "success"

    except Exception as e:
        logger.error(
            "Failed to create extra wallet for user %s in guild %s",
            interaction.user.id,
            guild.id,
            exc_info=e,
        )
        outcome = "failed_to_create"

    if outcome == "max_wallets_limit_exceeded":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка создания дополнительного счёта",
                "Достигнуло максимальное количество доступных счетов.",
            )
        )
        return

    if outcome == "failed_to_create":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка создания дополнительного счёта",
                "Произошла ошибка при создании дополнительного счёта.",
            )
        )
        return

    if outcome == "success":
        await interaction.followup.send(
            view=SuccessViewV2(
                "Создание дополнительного счёта",
                f"Вы успешно создали дополнительный счёт #{new_extra_wallet.slot}.",  # type: ignore  # noqa: E501
            )
        )

    logger.info(
        "[command] - invoked user=%s guild=%s outcome=%s",
        interaction.user.id,
        guild.id,
        outcome,
    )
