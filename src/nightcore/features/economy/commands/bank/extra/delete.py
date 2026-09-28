"""Command to delete user's extra bank account."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, app_commands
from discord.interactions import Interaction

from src.infra.db.operations import (
    delete_extra_wallet,
    get_or_create_user,
    get_user_extra_wallet_for_update,
)
from src.nightcore.components.view.v2 import ErrorViewV2, SuccessViewV2
from src.nightcore.features.economy._groups import extra as extra_group
from src.nightcore.features.economy.utils.autocomplete import (
    user_extra_wallets_autocomplete,
)
from src.nightcore.features.economy.utils.content import safe_split_wallet_id
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


@extra_group.command(  # type: ignore
    name="delete",
    description="Удалить дополнительный счёт в банке.",
)
@app_commands.guild_only()
@app_commands.describe(
    wallet="Дополнительный счёт, который нужно удалить.",
)
@app_commands.autocomplete(wallet=user_extra_wallets_autocomplete)
@check_required_permissions(PermissionsFlagEnum.NONE)  # type: ignore
async def extra_delete(interaction: Interaction["Nightcore"], wallet: str):
    """Delete extra wallet, moving its balance to the main one."""

    guild = cast(Guild, interaction.guild)

    outcome = ""

    deleted_slot: int | None = None
    transferred_coins: int | None = None
    new_user_balance: int | None = None

    await interaction.response.defer(thinking=True, ephemeral=True)

    try:
        async with interaction.client.uow.start() as session:
            user, _ = await get_or_create_user(
                session,
                guild_id=guild.id,
                user_id=interaction.user.id,
            )

            if user.bank_account is None:
                outcome = "bank_account_not_found"
            else:
                locked_user, _ = await get_or_create_user(
                    session,
                    guild_id=guild.id,
                    user_id=interaction.user.id,
                    for_update=True,
                )

                w = None
                wallet_id = safe_split_wallet_id(wallet)

                if wallet_id is None:
                    outcome = "extra_wallet_not_found"
                else:
                    w = await get_user_extra_wallet_for_update(
                        session,
                        bank_account_id=user.bank_account.id,
                        wallet_id=wallet_id,
                        for_update=True,
                    )

                    if w is None:
                        outcome = "extra_wallet_not_found"

                if not outcome and w is not None:
                    transferred_coins = w.coins
                    locked_user.coins += transferred_coins

                    deleted_slot = w.slot
                    new_user_balance = locked_user.coins

                    await delete_extra_wallet(
                        session,
                        bank_account_id=user.bank_account.id,
                        wallet_id=w.id,
                    )

                    outcome = "success"

    except Exception as e:
        logger.error(
            "Failed to delete extra wallet for user %s in guild %s",
            interaction.user.id,
            guild.id,
            exc_info=e,
        )
        outcome = "unexpected_error"

    if outcome == "bank_account_not_found":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка удаления дополнительного счёта",
                "Банковский аккаунт не был найден.\n> Создать его вы можете введя команду /bank profile",  # noqa: E501
            )
        )

    elif outcome == "extra_wallet_not_found":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка удаления дополнительного счёта",
                "Дополнительный счёт не был найден.\n> Создать его вы можете введя команду /bank extra create",  # noqa: E501
            )
        )

    elif outcome == "unexpected_error":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка удаления дополнительного счёта",
                "Произошла ошибка при удалении дополнительного счёта.",
            )
        )

    elif outcome == "success":
        moved = (
            f"Все средства ({transferred_coins} <:nightcoreBanknote:1540403146072002624>) "  # noqa: E501
            "были переведены на ваш основной счёт.\n"
            if transferred_coins
            else "Счёт был пуст, средства переводить не потребовалось.\n"
        )

        await interaction.followup.send(
            view=SuccessViewV2(
                "Удаление дополнительного счёта",
                f"Вы успешно удалили дополнительный счёт #{deleted_slot}.\n"
                f"{moved}"
                f"> Ваш баланс: {new_user_balance} <:nightcoreBanknote:1540403146072002624>",  # noqa: E501
            )
        )

    logger.info(
        "[command] - invoked user=%s guild=%s account=%s outcome=%s",
        interaction.user.id,
        guild.id,
        wallet,
        outcome,
    )
