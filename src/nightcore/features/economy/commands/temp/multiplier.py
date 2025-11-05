"""Command to set an specified multiplier for a guild for a limited time."""

import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, cast

from discord import Guild, Member, app_commands
from discord.interactions import Interaction

from src.infra.db.models import (
    GuildEconomyConfig,
    GuildLevelsConfig,
)
from src.infra.db.models._enums import MultiplierTypeEnum
from src.infra.db.operations import (
    get_or_create_temp_multiplier,
    get_specified_field,
)
from src.nightcore.components.embed import (
    ErrorEmbed,
    MissingPermissionsEmbed,
    SuccessMoveEmbed,
    ValidationErrorEmbed,
)
from src.nightcore.exceptions import FieldNotConfiguredError
from src.nightcore.features.economy._groups import temp as temp_group
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils import has_any_role_from_sequence
from src.nightcore.utils.time_utils import parse_duration

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


@temp_group.command(
    name="multiplier", description="Поставить временный множитель"
)
@app_commands.describe(
    multiplier_type="Тип множителя",
    multiplier="Множитель: целое число",
    duration="Срок действия множителя. Формат: s/m/h/d (например, 1h, 1d, 7d).",  # noqa: E501
)
@app_commands.choices(
    multiplier_type=[
        app_commands.Choice(name="Опыт", value="exp"),
        app_commands.Choice(name="Коины", value="coins"),
    ]
)
async def set_multiplier(
    interaction: Interaction["Nightcore"],
    multiplier_type: app_commands.Choice[str],
    multiplier: int,
    duration: str,
):
    """Give a role to user for a limited time."""

    guild = cast(Guild, interaction.guild)
    bot = interaction.client

    outcome = ""

    parsed_duration = parse_duration(duration)

    if not parsed_duration:
        return await interaction.response.send_message(
            embed=ValidationErrorEmbed(
                "Неверная продолжительность. Используйте s/m/h/d (например, 1h, 1d, 7d).",  # noqa: E501
                bot.user.name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    outcome = ""
    multiplier_type_enum = MultiplierTypeEnum(multiplier_type.value)

    async with specified_guild_config(bot, guild.id, GuildLevelsConfig) as (
        guild_config,
        session,
    ):
        economy_access_roles_ids = await get_specified_field(
            session,
            guild_id=guild.id,
            config_type=GuildEconomyConfig,
            field_name="economy_access_roles_ids",
        )

        if not economy_access_roles_ids:
            raise FieldNotConfiguredError("доступ к экономике")

        if not has_any_role_from_sequence(
            cast(Member, interaction.user), economy_access_roles_ids
        ):
            outcome = "missing_permissions"
        else:
            # Get or create multiplier
            try:
                temp_multiplier, created = await get_or_create_temp_multiplier(
                    session,
                    guild_id=guild.id,
                    multiplier_type=multiplier_type_enum,
                    multiplier=multiplier,
                    duration=parsed_duration,
                )

                if not created:
                    end_time = datetime.now(timezone.utc) + timedelta(
                        seconds=parsed_duration
                    )

                    temp_multiplier.multiplier = multiplier
                    temp_multiplier.duration = parsed_duration
                    temp_multiplier.end_time = end_time

                match multiplier_type_enum:
                    case MultiplierTypeEnum.EXP:
                        guild_config.temp_exp_multiplier = multiplier
                    case MultiplierTypeEnum.COINS:
                        guild_config.temp_coins_multiplier = multiplier

                outcome = "success"
            except Exception as e:
                logger.exception(
                    "[temp/multiplier] Failed to set temporary %s multiplier to %s for guild %s: %s",  # noqa: E501
                    multiplier_type_enum.value,
                    multiplier,
                    guild.id,
                    e,
                )
                outcome = "error"

    if outcome == "missing_permissions":
        return await interaction.response.send_message(
            embed=MissingPermissionsEmbed(
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "error":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка установки множителя",
                "Не удалось установить временный множитель.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "success":
        await interaction.response.send_message(
            embed=SuccessMoveEmbed(
                "Множитель установлен",
                f"Временный множитель {multiplier_type_enum.value} x{multiplier} установлен на {duration}.",  # noqa: E501
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    logger.info(
        "[command] - invoker user=%s guild=%s command=temp/multiplier outcome=%s multiplier_type=%s multiplier=%s duration=%s",  # noqa: E501
        interaction.user.id,
        guild.id,
        outcome,
        multiplier_type_enum.value,
        multiplier,
        duration,
    )
