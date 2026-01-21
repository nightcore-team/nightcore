"""Command to open case."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, Member, app_commands
from discord.interactions import Interaction

from src.infra.db.models import GuildLoggingConfig
from src.infra.db.models._enums import ChannelType
from src.infra.db.operations import (
    get_case_by_id,
    get_or_create_user,
    get_specified_channel,
)
from src.nightcore.components.embed import (
    ErrorEmbed,
    ValidationErrorEmbed,
)
from src.nightcore.features.economy._groups import case as case_group
from src.nightcore.features.economy.components.v2 import CaseOpenViewV2
from src.nightcore.features.economy.events.dto import AwardNotificationEventDTO
from src.nightcore.features.economy.utils import user_cases_autocomplete
from src.nightcore.features.economy.utils.case import (
    RewardOutcomeEnum,
    give_reward_by_type,
)
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)
from src.nightcore.utils.transformers.str_to_int import StrToIntTransformer

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


@case_group.command(name="open", description="Открыть кейс")  # type: ignore
@app_commands.describe(case="Кейс для открытия.")
@app_commands.rename(case_id="case_name")
@app_commands.autocomplete(case=user_cases_autocomplete)
@check_required_permissions(PermissionsFlagEnum.NONE)
async def open_case(
    interaction: Interaction["Nightcore"],
    case_id: app_commands.Transform[int, StrToIntTransformer],
):
    """Open case and get reward."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)
    member = cast(Member, interaction.user)

    outcome = ""
    reward_text = ""
    logging_channel_id = None

    async with bot.uow.start() as session:
        try:
            user, _ = await get_or_create_user(
                session,
                guild_id=guild.id,
                user_id=member.id,
                with_relations=True,
            )

            case = await get_case_by_id(
                session, guild_id=guild.id, case_id=case_id
            )

            if case is None:
                outcome = "unknown_case"
            else:
                logging_channel_id = await get_specified_channel(
                    session,
                    guild_id=guild.id,
                    config_type=GuildLoggingConfig,
                    channel_type=ChannelType.LOGGING_ECONOMY,
                )

                user_case = user.get_case(case_id)

                if user_case is None:
                    outcome = "no_case"
                else:
                    user_case.amount -= 1

                    reward = user_case.item.open()

                    result = await give_reward_by_type(
                        session, reward=reward, user=user
                    )

                    reward_text = reward["name"]

                    outcome = (
                        "success"
                        if result == RewardOutcomeEnum.SUCCESS
                        else "error: " + result.name
                    )

        except Exception as e:
            logger.exception(
                "[case/open] Error opening case %s for user %s in guild %s: %s",  # noqa: E501
                case_name.value,
                member.id,
                guild.id,
                e,
            )
            outcome = "error"

    if outcome == "no_case":
        return await interaction.response.send_message(
            embed=ValidationErrorEmbed(
                "У вас нет такого кейса для открытия.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "unknown_case":
        return await interaction.response.send_message(
            embed=ValidationErrorEmbed(
                "Неизвестный тип кейса.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome.startswith("error"):
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка открытия кейса",
                f"Произошла ошибка при открытии кейса. {outcome}",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "success":
        view = CaseOpenViewV2(
            bot=bot,
            case_name=case_name.name,
            reward=reward["name"],  # type: ignore
            chance=reward["chance"],  # type: ignore
        )
        await interaction.response.send_message(
            view=view,
            ephemeral=True,
        )

        bot.dispatch(
            "user_items_changed",
            dto=AwardNotificationEventDTO(
                guild=guild,
                event_type="case/open",
                logging_channel_id=logging_channel_id,
                user_id=member.id,
                moderator_id=bot.user.id,  # type: ignore
                item_name=reward["name"],  # type: ignore
                amount=reward["amount"],  # type: ignore
                reason="открытие кейса",
            ),
        )

    logger.info(
        "[command] - invoked user=%s guild=%s case=%s reward=%s",
        member.id,
        case_id,
        guild.id,
        reward_text,
    )
