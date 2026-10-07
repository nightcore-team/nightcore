"""Command to give badges."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, User, app_commands
from discord.interactions import Interaction

from src.infra.db.models import (
    GuildEconomyConfig,
    GuildLoggingConfig,
    UserGlobalBadge,
    UserGuildBadge,
)
from src.infra.db.operations import (
    get_badge_by_id,
    get_or_create_user,
    get_specified_field,
    get_specified_webhook,
    get_user_badges_for_update,
)
from src.nightcore.components.view.v2 import ErrorViewV2, SuccessViewV2
from src.nightcore.exceptions import FieldNotConfiguredError
from src.nightcore.features.economy._groups import give as give_group
from src.nightcore.features.economy.events.dto import AwardNotificationEventDTO
from src.nightcore.features.economy.utils.autocomplete import (
    guild_global_badges_autocomplete,
)
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils import has_any_role_from_sequence
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
    check_user_permission,
)
from src.nightcore.utils.transformers.str_to_int import StrToIntTransformer
from src.utils._enums import BadgeTypeEnum, ChannelType

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


@give_group.command(name="badge", description="Выдать значок пользователю.")  # type: ignore
@app_commands.describe(
    user="Пользователь, которому выдается значок.",
    type="Тип значка: Глобальный/Серверный",
    badge_id="Значок для выдачи.",
    reason="Причина выдачи значка.",
)
@app_commands.rename(badge_id="badge")
@app_commands.choices(
    type=[
        app_commands.Choice(name="Глобальный", value="global"),
        app_commands.Choice(name="Серверный", value="local"),
    ]
)
@app_commands.autocomplete(badge_id=guild_global_badges_autocomplete)
@check_required_permissions(PermissionsFlagEnum.UNSAFE)
async def give_badge(
    interaction: Interaction["Nightcore"],
    user: User,
    type: str,
    badge_id: app_commands.Transform[int, StrToIntTransformer],
    reason: str | None = None,
):
    """Give a global/guild badge to user."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)
    outcome = ""
    badge_name = ""
    badge_emoji = ""

    if user == bot.user:
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка выдачи значка", "Вы не можете выдать значок боту."
            ),
            ephemeral=True,
        )
        return

    try:
        badge_type = BadgeTypeEnum(type)
    except ValueError:
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка выдачи значка", "Укажите валидный тип значка."
            ),
            ephemeral=True,
        )
        return

    if badge_type == BadgeTypeEnum.GLOBAL:
        has_permissions = await check_user_permission(
            interaction, permissions=PermissionsFlagEnum.BOT_ACCESS
        )
        if not has_permissions:
            raise app_commands.MissingPermissions(
                missing_permissions=["bot_access"]
            )

    await interaction.response.defer(thinking=True, ephemeral=True)

    logging_webhook = None

    try:
        async with specified_guild_config(
            bot,
            guild_id=guild.id,
            config_type=GuildEconomyConfig,
        ) as (_, session):
            # Global badges are covered by BOT_ACCESS above, so the economy
            # access roles are only required for guild badges.
            if badge_type == BadgeTypeEnum.LOCAL:
                economy_access_roles_ids = await get_specified_field(
                    session,
                    guild_id=guild.id,
                    config_type=GuildEconomyConfig,
                    field_name="economy_access_roles_ids",
                )
                if not economy_access_roles_ids:
                    outcome = "economy_access_not_configured"
                elif not has_any_role_from_sequence(
                    interaction.user, economy_access_roles_ids
                ):
                    outcome = "missing_permissions"

            if not outcome:
                logging_webhook = await get_specified_webhook(
                    session,
                    guild_id=guild.id,
                    config_type=GuildLoggingConfig,
                    channel_type=ChannelType.LOGGING_ECONOMY,
                )

                badge = await get_badge_by_id(
                    session,
                    badge_type=badge_type,
                    badge_id=badge_id,
                    guild_id=guild.id,
                )

                if badge is None:
                    outcome = "unknown_badge"
                else:
                    user_record, _ = await get_or_create_user(
                        session,
                        guild_id=guild.id,
                        user_id=user.id,
                    )

                    user_all_badges = await get_user_badges_for_update(
                        session,
                        badge_type=badge_type,
                        user_id=user_record.id,
                        guild_id=guild.id,
                    )

                    if len(user_all_badges) >= bot.config.bot.MAX_USER_BADGES:
                        outcome = "max_badges_limit_exceeded"
                    else:
                        existing = next(
                            (
                                user_badge
                                for user_type_badges in user_all_badges
                                for user_badge in user_type_badges
                                if user_badge.badge_id == badge_id
                            ),
                            None,
                        )

                        if existing is not None:
                            outcome = "already_has_badge"
                        else:
                            # Grab everything needed for the reply while
                            # the session is still open.
                            badge_name = badge.name
                            badge_emoji = badge.emoji_str

                            session.add(
                                UserGlobalBadge(
                                    user_id=user_record.id,
                                    badge_id=badge_id,
                                )
                                if badge_type == BadgeTypeEnum.GLOBAL
                                else UserGuildBadge(
                                    guild_id=guild.id,
                                    user_id=user_record.id,
                                    badge_id=badge_id,
                                )
                            )

                            outcome = "success"

    except Exception as e:
        logger.exception(
            "[give/badge] Error giving badge %s to user %s in guild %s: %s",
            badge_id,
            user.id,
            guild.id,
            e,
        )
        outcome = "give_badge_error"

    if outcome == "economy_access_not_configured":
        raise FieldNotConfiguredError("доступ к экономике")

    if outcome == "missing_permissions":
        raise app_commands.MissingPermissions(
            missing_permissions=["economy_access"]
        )

    if outcome == "unknown_badge":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка выдачи значка",
                "Значок не найден.",
            ),
        )
        return

    if outcome == "max_badges_limit_exceeded":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка выдачи значка",
                "Достигнуто максимальное количество доступных значков у пользователя.",  # noqa: E501
            ),
        )
        return

    if outcome == "already_has_badge":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка выдачи значка",
                "У пользователя уже есть данный значок.",
            ),
        )
        return

    if outcome == "give_badge_error":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка выдачи значка",
                "Не удалось выдать значок пользователю.",
            ),
        )
        return

    item_name = f"значок: {badge_name}"

    await interaction.followup.send(
        view=SuccessViewV2(
            "Выдача значка",
            f"Значок **{badge_name}** {badge_emoji} выдан пользователю <@{user.id}>.",  # noqa: E501
        ),
    )

    if badge_type == BadgeTypeEnum.LOCAL:
        item_name += f" {badge_emoji}"

    bot.dispatch(
        "user_items_changed",
        dto=AwardNotificationEventDTO(
            guild=guild,
            event_type="give/badge",
            logging_webhook=logging_webhook,
            user_id=user.id,
            moderator_id=interaction.user.id,
            item_name=item_name,
            amount=-1,
            duration=None,
            reason=reason,
        ),
    )
