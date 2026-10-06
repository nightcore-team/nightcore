"""Command to remove a badge from a user."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, User, app_commands
from discord.interactions import Interaction

from src.infra.db.models import GuildEconomyConfig, GuildLoggingConfig
from src.infra.db.operations import (
    get_badge_by_id,
    get_or_create_user,
    get_specified_field,
    get_specified_webhook,
    get_user_badges_for_update,
)
from src.nightcore.components.view.v2 import ErrorViewV2, SuccessViewV2
from src.nightcore.exceptions import FieldNotConfiguredError
from src.nightcore.features.economy._groups import remove as remove_group
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


@remove_group.command(
    name="badge", description="Удалить значок у пользователя"
)  # type: ignore
@app_commands.describe(
    user="Пользователь, у которого удаляется значок.",
    type="Тип значка: Глобальный/Серверный",
    badge_id="Значок для удаления.",
    reason="Причина удаления значка (необязательно).",
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
async def remove_badge(
    interaction: Interaction["Nightcore"],
    user: User,
    type: str,
    badge_id: app_commands.Transform[int, StrToIntTransformer],
    reason: str | None = None,
):
    """Remove a global/guild badge from a user."""

    guild = cast(Guild, interaction.guild)
    bot = interaction.client
    outcome = ""
    badge_name = ""
    badge_emoji = ""

    if user == bot.user:
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка удаления значка", "Вы не можете удалить значок у бота."
            ),
            ephemeral=True,
        )
        return

    try:
        badge_type = BadgeTypeEnum[type]
    except KeyError:
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка удаления значка", "Укажите валидный тип значка."
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
                        session, guild_id=guild.id, user_id=user.id
                    )

                    user_badges = await get_user_badges_for_update(
                        session,
                        badge_type=badge_type,
                        user_id=user_record.id,
                        guild_id=guild.id,
                    )
                    target = next(
                        (
                            user_badge
                            for user_badge in user_badges
                            if user_badge.badge_id == badge_id
                        ),
                        None,
                    )

                    if target is None:
                        outcome = "does_not_have_badge"
                    else:
                        badge_name = badge.name
                        badge_emoji = badge.emoji_str

                        await session.delete(target)

                        outcome = "success"

    except Exception as e:
        logger.exception(
            "[remove/badge] Error removing badge %s from user %s in guild %s: %s",  # noqa: E501
            badge_id,
            user.id,
            guild.id,
            e,
        )
        outcome = "remove_badge_error"

    if outcome == "economy_access_not_configured":
        raise FieldNotConfiguredError("доступ к экономике")

    if outcome == "missing_permissions":
        raise app_commands.MissingPermissions(
            missing_permissions=["economy_access"]
        )

    if outcome == "unknown_badge":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка удаления значка",
                "Значок не найден.",
            ),
        )
        return

    if outcome == "does_not_have_badge":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка удаления значка",
                "У пользователя нет этого значка.",
            ),
        )
        return

    if outcome == "remove_badge_error":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка удаления значка",
                "Не удалось удалить значок у пользователя.",
            ),
        )
        return

    await interaction.followup.send(
        view=SuccessViewV2(
            "Удаление значка",
            f"Значок **{badge_name}** {badge_emoji} удален у пользователя <@{user.id}>.",  # noqa: E501
        ),
    )

    item_name = f"значок: {badge_name}"

    if badge_type == BadgeTypeEnum.LOCAL:
        item_name += f" {badge_emoji}"

    bot.dispatch(
        "user_items_changed",
        dto=AwardNotificationEventDTO(
            guild=guild,
            event_type="remove/badge",
            logging_webhook=logging_webhook,
            user_id=user.id,
            moderator_id=interaction.user.id,
            item_name=item_name,
            amount=-1,
            duration=None,
            reason=reason,
        ),
    )
