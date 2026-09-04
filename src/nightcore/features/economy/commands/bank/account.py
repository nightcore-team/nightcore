"""Command to check user's bank account."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, User, app_commands
from discord.interactions import Interaction

from src.infra.db.models import GuildEconomyConfig
from src.infra.db.operations import (
    get_or_create_bank_account,
    get_or_create_user,
)
from src.nightcore.components.view.v2 import EntityNotFoundViewV2
from src.nightcore.features.economy.components.v2 import BankAccountViewV2
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils import ensure_member_exists

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.features.economy._groups import bank as bank_group
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

logger = logging.getLogger(__name__)


@bank_group.command(  # type: ignore
    name="account",
    description="Посмотреть банковский аккаунт пользователя.",
)
@app_commands.guild_only()
@app_commands.describe(
    user="Пользователь, чей банковский аккаунт посмотреть. По умолчанию - вы сами."  # noqa: E501
)
@check_required_permissions(PermissionsFlagEnum.NONE)  # type: ignore
async def account(
    interaction: Interaction["Nightcore"], user: User | None = None
):
    """Check user's bank account."""

    guild = cast(Guild, interaction.guild)
    member = interaction.user

    if user:
        member = await ensure_member_exists(guild, user.id)
        if member is None:
            await interaction.response.send_message(
                view=EntityNotFoundViewV2(
                    "пользователь",
                ),
                ephemeral=True,
            )
            return

    await interaction.response.defer(thinking=True, ephemeral=True)

    async with specified_guild_config(
        interaction.client,
        guild_id=guild.id,
        config_type=GuildEconomyConfig,
    ) as (
        guild_config,
        session,
    ):
        coin_name = guild_config.coin_name or "коинов"

        dbuser, _ = await get_or_create_user(
            session,
            guild_id=guild.id,
            user_id=member.id,
        )

        bank_account, _ = await get_or_create_bank_account(
            session,
            guild_id=guild.id,
            user_id=dbuser.id,
            for_update=True,
        )

    assert bank_account.deposit is not None

    deposit_float_rate = float(guild_config.deposit_base_interest_rate) * 100

    view = BankAccountViewV2(
        user_id=member.id,
        coin_name=coin_name,
        deposit_balance=bank_account.deposit.coins,
        deposit_interest_cap_amount=guild_config.deposit_interest_cap_amount,
        deposit_current_rate=deposit_float_rate,
        deposit_last_updated_at=bank_account.deposit.updated_at,
        extra_wallets=[
            {
                "coins": wallet.coins,
                "slot": wallet.slot,
                "updated_at": wallet.updated_at,
            }
            for wallet in bank_account.extra_wallets
        ],
    )

    await interaction.followup.send(view=view)

    logger.info(
        "[command] - invoked user=%s guild=%s target_user=%s",
        interaction.user.id,
        guild.id,
        member.id,
    )
