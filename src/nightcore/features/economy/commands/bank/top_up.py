"""Command to deposit money into user's bank wallet (deposit/extra)."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, app_commands
from discord.interactions import Interaction

from src.infra.db.models.bank import Deposit, ExtraWallet
from src.infra.db.operations import (
    get_or_create_bank_account,
    get_or_create_user,
    get_user_deposit_for_update,
    get_user_extra_wallet_for_update,
)
from src.nightcore.components.view.v2 import ErrorViewV2, SuccessViewV2
from src.nightcore.features.economy.utils.autocomplete import (
    deposit_extra_wallets_autocomplete,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.features.economy._groups import bank as bank_group
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

logger = logging.getLogger(__name__)


@bank_group.command(  # type: ignore
    name="top_up",
    description="Пополнить депозитный/дополнительный счёт.",
)
@app_commands.guild_only()
@app_commands.describe(
    account="Счёт, который нужно пополнить.",
    amount="Сумма для пополнения.",
)
@app_commands.autocomplete(account=deposit_extra_wallets_autocomplete)
@check_required_permissions(PermissionsFlagEnum.NONE)  # type: ignore
async def top_up(
    interaction: Interaction["Nightcore"],
    account: app_commands.Choice[str],
    amount: app_commands.Range[int, 1],
):
    """Top up money from user's main balance into a deposit/extra wallet."""

    guild = cast(Guild, interaction.guild)
    choice = account.value

    await interaction.response.defer(thinking=True, ephemeral=True)

    outcome = ""
    new_user_balance: int | None = None
    new_target_balance: int | None = None

    try:
        async with interaction.client.uow.start() as session:
            user, _ = await get_or_create_user(
                session,
                guild_id=guild.id,
                user_id=interaction.user.id,
            )

            bank_account, _ = await get_or_create_bank_account(
                session,
                guild_id=guild.id,
                user_id=user.id,
            )

            target: Deposit | ExtraWallet | None = None

            if choice == "deposit":
                target = await get_user_deposit_for_update(
                    session, bank_account_id=bank_account.id, for_update=True
                )
                if target is None:
                    outcome = "deposit_not_found"

            elif choice.startswith("extra:"):
                wallet_id = int(choice.split(":", 1)[1])
                target = await get_user_extra_wallet_for_update(
                    session,
                    bank_account_id=bank_account.id,
                    wallet_id=wallet_id,
                    for_update=True,
                )
                if target is None:
                    outcome = "extra_wallet_not_found"

            else:
                outcome = "specified_not_found"

            if not outcome and target is not None:
                locked_user, _ = await get_or_create_user(
                    session,
                    guild_id=guild.id,
                    user_id=interaction.user.id,
                    for_update=True,
                )

                if locked_user.coins < amount:
                    outcome = "not_enough_coins"
                else:
                    locked_user.coins -= amount
                    target.coins += amount

                    new_user_balance = locked_user.coins
                    new_target_balance = target.coins

                    outcome = "success"

    except Exception as e:
        logger.error(
            "Failed to deposit for user=%s guild=%s",
            interaction.user.id,
            guild.id,
            exc_info=e,
        )
        outcome = "unexpected_error"

    if outcome == "deposit_not_found":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка пополнения счёта",
                "Депозитный счёт не был найден.\n> Создать его вы можете введя команду /bank profile",  # noqa: E501
            )
        )

    elif outcome == "extra_wallet_not_found":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка пополнения счёта",
                "Extra счёт не был найден.\n> Создать его вы можете введя команду /bank extra create",  # noqa: E501
            )
        )

    elif outcome == "specified_not_found":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка пополнения счёта",
                "Указанный счёт не был найден.\n> Убедитесь, что депозитный/extra счёт существует.",  # noqa: E501
            )
        )

    elif outcome == "not_enough_coins":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка пополнения счёта",
                "Недостаточно средств на основном балансе.",
            )
        )

    elif outcome == "success":
        account_desc = "депозитный" if choice == "deposit" else "extra"

        await interaction.followup.send(
            view=SuccessViewV2(
                "Пополнение счёта",
                f"Вы успешно пополнили {account_desc} счёт"
                " на сумму {amount} <:nightcoreBanknoteUp:1540436249809133683>\n"  # noqa: E501
                f"> Ваш текущий баланс: {new_user_balance}, баланс счёта: {new_target_balance} <:nightcoreBanknote:1540403146072002624>",  # noqa: E501
            )
        )

    elif outcome == "unexpected_error":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка пополнения счёта",
                "Произошла ошибка при пополнении указанного счёта.",
            )
        )

    logger.info(
        "[command deposit] invoked user=%s guild=%s amount=%s account=%s",
        interaction.user.id,
        guild.id,
        amount,
        choice,
    )
