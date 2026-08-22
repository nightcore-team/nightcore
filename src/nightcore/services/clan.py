"""Service for building and sending the clan info view."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from discord import Guild

from src.infra.db.operations import get_user_clan
from src.nightcore.components.view.v2 import ErrorViewV2
from src.nightcore.features.clans.components.v2 import ClanInfoViewV2

if TYPE_CHECKING:
    from discord.interactions import Interaction

    from src.nightcore.bot import Nightcore


async def send_clan_info_view(
    bot: Nightcore,
    interaction: Interaction[Nightcore],
    user_id: int | None = None,
) -> None:
    """Build and send the clan info view for the interaction's user."""

    guild = cast(Guild, interaction.guild)
    target_user_id = user_id if user_id else interaction.user.id

    async with bot.uow.start() as session:
        dbclan = await get_user_clan(
            session,
            guild_id=guild.id,
            user_id=target_user_id,
        )

    if not dbclan:
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка получения информации о клане",
                "Вы не состоите в клане на этом сервере.",
            ),
            ephemeral=True,
        )
        return

    view = ClanInfoViewV2(
        bot=bot,
        name=dbclan.name,
        leader_id=dbclan.leader.user_id,
        created_at=dbclan.created_at,
        deputies=[deputy.user_id for deputy in dbclan.deputies],
        lvl=dbclan.level,
        current_exp=dbclan.current_exp,
        reputation=dbclan.coins,
        members=dbclan.members,
        max_members=dbclan.max_members,
        max_deputies=dbclan.max_deputies,
        reputation_multiplier=dbclan.payday_multipler,
    )

    await interaction.response.send_message(view=view, ephemeral=True)
