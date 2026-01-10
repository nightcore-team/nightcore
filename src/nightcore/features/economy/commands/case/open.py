"""Command to open case."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, Member, app_commands
from discord.interactions import Interaction
from sqlalchemy.orm import attributes

from src.infra.db.models import GuildEconomyConfig, GuildLoggingConfig
from src.infra.db.models._enums import ChannelType
from src.infra.db.operations import get_or_create_user, get_specified_channel
from src.nightcore.components.embed import (
    ErrorEmbed,
    ValidationErrorEmbed,
)
from src.nightcore.features.economy._groups import case as case_group
from src.nightcore.features.economy.components.v2 import CaseOpenViewV2
from src.nightcore.features.economy.events.dto import AwardNotificationEventDTO
from src.nightcore.features.economy.utils import user_cases_autocomplete
from src.nightcore.features.economy.utils.case import (
    CASES_NAMES,
    open_coins_case,
    open_colors_case,
)
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


@case_group.command(name="open", description="Открыть кейс")  # type: ignore
@app_commands.describe(case="Кейс для открытия.")
@app_commands.autocomplete(case=user_cases_autocomplete)
@check_required_permissions(PermissionsFlagEnum.NONE)
async def open_case(
    interaction: Interaction["Nightcore"],
    case: str,
):
    """Open case and get reward."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)
    member = cast(Member, interaction.user)

    outcome = ""
    reward_text = ""
    coins_reward = 0
    color_role_id = 0
    color_name = ""
    chance = 0
    logging_channel_id = None
    coin_name = ""

    async with specified_guild_config(
        bot, guild_id=guild.id, config_type=GuildEconomyConfig
    ) as (guild_config, session):
        try:
            user, _ = await get_or_create_user(
                session,
                guild_id=guild.id,
                user_id=member.id,
            )

            logging_channel_id = await get_specified_channel(
                session,
                guild_id=guild.id,
                config_type=GuildLoggingConfig,
                channel_type=ChannelType.LOGGING_ECONOMY,
            )

            case_count = user.inventory.get("cases", {}).get(case, 0)

            if case_count <= 0:
                outcome = "no_case"

            else:
                match case:
                    case "coins_case":
                        if not guild_config.drop_from_coins_case:
                            outcome = "case_not_configured"
                        else:
                            coins_reward, chance = open_coins_case(
                                guild_config.drop_from_coins_case
                            )

                            user.coins += coins_reward

                            # remove case from inventory
                            user.inventory["cases"][case] -= 1  # type: ignore
                            if user.inventory["cases"][case] <= 0:  # type: ignore
                                del user.inventory["cases"][case]  # type: ignore

                            attributes.flag_modified(user, "inventory")

                            coin_name = guild_config.coin_name or "коины"
                            reward_coin_name = (
                                guild_config.coin_name or "коинов"
                            )
                            reward_text = f"{coins_reward} {reward_coin_name}"
                            outcome = "success"

                    case "colors_case":
                        if not guild_config.drop_from_colors_case:
                            outcome = "case_not_configured"
                        else:
                            color_name, color_role_id, chance = (
                                open_colors_case(
                                    guild_config.drop_from_colors_case
                                )
                            )

                            if "colors" not in user.inventory:
                                user.inventory["colors"] = []

                            if color_name in user.inventory["colors"]:
                                pass
                            else:
                                user.inventory["colors"].append(color_name)

                            # remove case from inventory
                            user.inventory["cases"][case] -= 1  # type: ignore
                            if user.inventory["cases"][case] <= 0:  # type: ignore
                                del user.inventory["cases"][case]  # type: ignore

                            attributes.flag_modified(user, "inventory")

                            reward_text = f"цвет <@&{color_role_id}>"
                            outcome = "success"

                    case _:
                        outcome = "unknown_case"

        except Exception as e:
            logger.exception(
                "[case/open] Error opening case %s for user %s in guild %s: %s",  # noqa: E501
                case,
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

    if outcome == "case_not_configured":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка открытия кейса",
                "Этот кейс не настроен на этом сервере.",
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

    if outcome == "error":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка открытия кейса",
                "Произошла ошибка при открытии кейса.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "success":
        view = CaseOpenViewV2(
            bot=bot,
            case_name=CASES_NAMES.get(case, case).lower(),
            reward=reward_text,
            chance=chance,
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
                item_name=coin_name if coin_name else f"цвет {color_name}",
                amount=coins_reward if coins_reward else 1,
                reason="открытие кейса",
            ),
        )

    logger.info(
        "[command] - invoked user=%s guild=%s case=%s reward=%s",
        member.id,
        case,
        guild.id,
        reward_text,
    )
