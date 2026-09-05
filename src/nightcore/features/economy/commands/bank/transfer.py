"""Command to transfer money between user's own bank accounts (main/deposit/extra)."""  # noqa: E501

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, app_commands
from discord.interactions import Interaction

from src.infra.db.operations import (
    get_or_create_bank_account,
    get_or_create_user,
    get_user_deposit_for_update,
    get_user_extra_wallet_for_update,
)
from src.nightcore.components.view.v2 import ErrorViewV2, SuccessViewV2
from src.nightcore.features.economy.utils.autocomplete import (
    all_user_bank_accounts_autocomplete,
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


def _sort_key(choice: str) -> tuple[int, int]:
    """
    Fixed ordering for locking multiple wallets: deposit first, then
    extra wallets sorted by id. Prevents deadlocks between transfers
    going in opposite directions between the same two wallets.
    """  # noqa: D205

    if choice == "deposit":
        return (0, 0)
    return (1, int(choice.split(":", 1)[1]))


@bank_group.command(  # type: ignore
    name="transfer",
    description="Перевести деньги между своими счетами.",
)
@app_commands.guild_only()
@app_commands.describe(
    source="Счёт, с которого перевести деньги.",
    target="Счёт, на который перевести деньги.",
    amount="Сумма для перевода.",
)
@app_commands.autocomplete(
    source=all_user_bank_accounts_autocomplete,
    target=all_user_bank_accounts_autocomplete,
)
@app_commands.rename(from_wallet="from", to_wallet="to")
@check_required_permissions(PermissionsFlagEnum.NONE)  # type: ignore
async def transfer(
    interaction: Interaction["Nightcore"],
    from_wallet: app_commands.Choice[str],
    to_wallet: app_commands.Choice[str],
    amount: app_commands.Range[int, 1],
):
    """Transfer money between the user's own main balance / deposit / extra wallets."""  # noqa: E501

    guild = cast(Guild, interaction.guild)
    source = from_wallet.value
    target = to_wallet.value

    if source == target:
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка перевода",
                "Счёт списания и счёт зачисления не могут совпадать.",
            ),
            ephemeral=True,
        )
        return

    await interaction.response.defer(thinking=True, ephemeral=True)

    outcome = ""
    new_source_balance: int | None = None
    new_target_balance: int | None = None

    needs_main = "main" in (source, target)
    wallet_choices = {c for c in (source, target) if c != "main"}

    locked_wallets: dict[str, Deposit | ExtraWallet] = {}
    missing_choice: str | None = None
    account: Deposit | ExtraWallet | None = None

    try:
        async with interaction.client.uow.start() as session:
            bank_account, _ = await get_or_create_bank_account(
                session,
                guild_id=guild.id,
                user_id=interaction.user.id,
            )

            # lock wallets before user to avoid deadlocks
            for choice in sorted(wallet_choices, key=_sort_key):
                if choice == "deposit":
                    account = await get_user_deposit_for_update(
                        session,
                        bank_account_id=bank_account.id,
                        for_update=True,
                    )

                if choice.startswith("extra:"):
                    wallet_id = int(choice.split(":", 1)[1])
                    account = await get_user_extra_wallet_for_update(
                        session,
                        bank_account_id=bank_account.id,
                        wallet_id=wallet_id,
                        for_update=True,
                    )

                if account is None:
                    missing_choice = choice
                    break

                locked_wallets[choice] = account

            if missing_choice is not None:
                outcome = (
                    "deposit_not_found"
                    if missing_choice == "deposit"
                    else "extra_wallet_not_found"
                )

            if not outcome:
                # lock user after locking all needed wallets
                locked_user = None
                if needs_main:
                    locked_user, _ = await get_or_create_user(
                        session,
                        guild_id=guild.id,
                        user_id=interaction.user.id,
                        for_update=True,
                    )

                def _balance_holder(
                    choice: str,
                ):
                    return (
                        locked_user
                        if choice == "main"
                        else locked_wallets[choice]
                    )

                src = _balance_holder(source)
                dst = _balance_holder(target)

                if src is None or dst is None:
                    outcome = "specified_not_found"

                elif src.coins < amount:
                    outcome = "not_enough_coins"

                else:
                    src.coins -= amount
                    dst.coins += amount

                    new_source_balance = src.coins
                    new_target_balance = dst.coins

                    outcome = "success"

    except Exception as e:
        logger.error(
            "Failed to transfer for user=%s guild=%s",
            interaction.user.id,
            guild.id,
            exc_info=e,
        )
        outcome = "unexpected_error"

    if outcome == "deposit_not_found":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка перевода",
                "Депозитный счёт не был найден.\n> Создать его вы можете введя команду /bank profile",  # noqa: E501
            )
        )

    elif outcome == "extra_wallet_not_found":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка перевода",
                "Extra счёт не был найден.\n> Создать его вы можете введя команду /bank extra create",  # noqa: E501
            )
        )

    elif outcome == "specified_not_found":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка перевода",
                "Один из указанных счетов не был найден.",
            )
        )

    elif outcome == "not_enough_coins":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка перевода",
                "Недостаточно средств на счёте списания.",
            )
        )

    elif outcome == "success":

        def _account_desc(choice: str) -> str:
            if choice == "main":
                return "основного"
            if choice == "deposit":
                return "депозитного"
            return "extra"

        source_desc = _account_desc(source)
        target_desc = _account_desc(target)

        await interaction.followup.send(
            view=SuccessViewV2(
                "Перевод средств между счетами",
                f"Вы успешно перевели {amount}"
                f" <:nightcoreBanknoteDown:1545558909631201321> с {source_desc}"  # noqa: E501
                f" счёта на {target_desc} счёт.\n"
                f"> Текущий баланс {source} счёта: {new_source_balance}, баланс {target_desc} счёта: {new_target_balance} <:nightcoreBanknote:1540403146072002624>",  # noqa: E501
            )
        )

    elif outcome == "unexpected_error":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка перевода",
                "Произошла ошибка при переводе средств.",
            )
        )

    logger.info(
        "[command transfer] invoked user=%s guild=%s amount=%s source=%s target=%s",  # noqa: E501
        interaction.user.id,
        guild.id,
        amount,
        source,
        target,
    )
