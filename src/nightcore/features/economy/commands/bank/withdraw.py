"""Command to withdraw money from user's bank wallet (deposit/extra)."""

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
    from src.infra.db.models.bank import Deposit, ExtraWallet
    from src.nightcore.bot import Nightcore

from src.nightcore.features.economy._groups import bank as bank_group
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

logger = logging.getLogger(__name__)


@bank_group.command(  # type: ignore
    name="withdraw",
    description="Снять деньги с депозитного/дополнительного счёта.",
)
@app_commands.guild_only()
@app_commands.describe(
    account="Счёт, с которого снять деньги.",
    amount="Сумма для снятия.",
)
@app_commands.autocomplete(from_wallet=deposit_extra_wallets_autocomplete)
@app_commands.rename(from_wallet="from")
@check_required_permissions(PermissionsFlagEnum.NONE)  # type: ignore
async def withdraw(
    interaction: Interaction["Nightcore"],
    from_wallet: app_commands.Choice[str],
    amount: app_commands.Range[int, 1],
):
    """Withdraw money from user's deposit/extra wallet to main."""

    guild = cast(Guild, interaction.guild)
    choice = from_wallet.value

    await interaction.response.defer(thinking=True, ephemeral=True)

    outcome = ""
    new_user_balance: int | None = None
    new_target_balance: int | None = None

    try:
        async with interaction.client.uow.start() as session:
            bank_account, _ = await get_or_create_bank_account(
                session,
                guild_id=guild.id,
                user_id=interaction.user.id,
            )

            source: Deposit | ExtraWallet | None = None

            if choice == "deposit":
                source = await get_user_deposit_for_update(
                    session, bank_account_id=bank_account.id
                )
                if source is None:
                    outcome = "deposit_not_found"

            elif choice.startswith("extra:"):
                wallet_id = int(choice.split(":", 1)[1])

                source = await get_user_extra_wallet_for_update(
                    session,
                    bank_account_id=bank_account.id,
                    wallet_id=wallet_id,
                )
                if source is None:
                    outcome = "extra_wallet_not_found"

            else:
                source = None
                outcome = "specified_not_found"

            if not outcome and source is not None:
                if source.coins < amount:
                    outcome = "not_enough_coins"
                else:
                    locked_user, _ = await get_or_create_user(
                        session,
                        guild_id=guild.id,
                        user_id=interaction.user.id,
                        for_update=True,
                    )

                    source.coins -= amount
                    locked_user.coins += amount

                    new_user_balance = locked_user.coins
                    new_target_balance = source.coins

                    outcome = "success"

    except Exception as e:
        logger.error(
            "Failed to withdraw for user=%s guild=%s",
            interaction.user.id,
            guild.id,
            exc_info=e,
        )
        outcome = "unexpected_error"

    if outcome == "deposit_not_found":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка снятия средств со счёта",
                "Депозитный счёт не был найден.\n> Создать его вы можете введя команду /bank profile",  # noqa: E501
            )
        )

    elif outcome == "extra_wallet_not_found":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка снятия средств со счёта",
                "Extra счёт не был найден.\n> Создать его вы можете введя команду /bank extra create",  # noqa: E501
            )
        )

    elif outcome == "specified_not_found":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка снятия средств со счёта",
                "Указанный счёт не был найден.\n> Убедитель, что депозитный/extra счёт существует.",  # noqa: E501
            )
        )

    elif outcome == "not_enough_coins":
        account_desc = "депозитном" if choice == "deposit" else "extra"

        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка снятия средств со счёта",
                f"Недостаточно средств на {account_desc} счёту.",
            )
        )

    elif outcome == "unexpected_error":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка снятия средств со счёта",
                "Произошла ошибка при снятии денег с указанного счёта.",
            )
        )

    elif outcome == "success":
        account_desc = "депозитного" if choice == "deposit" else "extra"

        await interaction.followup.send(
            view=SuccessViewV2(
                "Снятие средств со счёта",
                f"Вы успешно сняли {amount}"
                f" <:nightcoreBanknoteDown:1545558909631201321> с {account_desc} счёта.\n"  # noqa: E501
                f"> Ваш новый баланс: {new_user_balance}, баланс счёта: {new_target_balance} <:nightcoreBanknote:1540403146072002624>",  # noqa: E501
            )
        )

    logger.info(
        "[command] - invoked user=%s guild=%s amount=%s account=%s",
        interaction.user.id,
        guild.id,
        amount,
        choice,
    )
