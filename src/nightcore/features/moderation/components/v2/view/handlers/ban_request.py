"""Handlers for ban request buttons."""

import logging
from datetime import UTC
from typing import TYPE_CHECKING

import discord
from discord.interactions import Interaction
from sqlalchemy.orm import attributes

from src.infra.db.models import GuildModerationConfig
from src.infra.db.models._enums import VoteBanStateEnum
from src.infra.db.operations import (
    get_specified_guild_config,
    get_voteban_state,
)
from src.nightcore.components.embed import ErrorEmbed, MissingPermissionsEmbed
from src.nightcore.exceptions import ConfigMissingError
from src.nightcore.features.moderation.components.v2.view import (
    BanRequestViewV2,
)
from src.nightcore.features.moderation.events.dto import UserBannedEventData
from src.nightcore.features.moderation.utils.punish_notify import (
    send_punish_dm_message,
)
from src.nightcore.utils import ensure_member_exists
from src.nightcore.utils.object import (
    cast_guild,
    cast_member,
    has_any_role_from_sequence,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


async def handle_voteban_button_callback(
    interaction: Interaction["Nightcore"], custom_id: str
):
    """Handle the voteban button callback interaction."""

    bot = interaction.client
    guild = cast_guild(interaction.guild)
    moderator = cast_member(interaction.user)

    try:
        _, user_id, action = custom_id.split(":")
    except ValueError:
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                title="Ошибка взаимодействия",
                description="Некорректный формат custom_id для кнопки голосования за бан.",  # noqa: E501
                footer_text=bot.user.name,
                footer_icon_url=bot.user.display_avatar.url,
            ),
            ephemeral=True,
        )

    try:
        user_id = int(user_id)
    except ValueError:
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                title="Ошибка взаимодействия",
                description="Некорректный ID пользователя в custom_id для кнопки голосования за бан.",  # noqa: E501
                footer_text=bot.user.name,
                footer_icon_url=bot.user.display_avatar.url,
            ),
            ephemeral=True,
        )

    async with bot.uow.start() as session:
        guild_config = await get_specified_guild_config(
            session=session,
            config_type=GuildModerationConfig,
            guild_id=guild.id,
        )
        if guild_config is None:
            raise ConfigMissingError(guild.id)

        moderation_access_roles = guild_config.moderation_access_roles_ids
        ban_access_roles = guild_config.ban_access_roles_ids

        ping_role_id = guild_config.ban_request_ping_role_id

    has_moder_role = has_any_role_from_sequence(
        moderator, moderation_access_roles
    )

    if not has_moder_role:
        return await interaction.response.send_message(
            embed=MissingPermissionsEmbed(
                footer_text=bot.user.name,
                footer_icon_url=bot.user.display_avatar.url,
            ),
            ephemeral=True,
        )

    match action:
        case "approve":
            await handle_voteban_approve_button_callback(
                interaction=interaction,
                user_id=user_id,
                ban_access_roles=ban_access_roles,
                ping_role_id=ping_role_id,
            )
        case "reject":
            await handle_voteban_reject_button_callback(
                interaction=interaction,
                user_id=user_id,
                ban_access_roles=ban_access_roles,
                ping_role_id=ping_role_id,
            )

        case _:
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    title="Ошибка взаимодействия",
                    description="Некорректное действие в custom_id для кнопки голосования за бан.",  # noqa: E501
                    footer_text=bot.user.name,
                    footer_icon_url=bot.user.display_avatar.url,
                ),
                ephemeral=True,
            )


async def handle_voteban_approve_button_callback(
    interaction: Interaction["Nightcore"],
    user_id: int,
    ban_access_roles: list[int] | None,
    ping_role_id: int | None,
):
    """Handle the voteban approve button callback interaction."""

    await interaction.response.defer(ephemeral=True)

    bot = interaction.client
    guild = cast_guild(interaction.guild)
    moderator = cast_member(interaction.user)
    user = cast_member(await ensure_member_exists(guild, user_id))

    outcome = ""
    async with bot.uow.start() as session:
        votebanstate = await get_voteban_state(
            session, guild_id=guild.id, user_id=user_id
        )

        if votebanstate is None:
            outcome = "not_found"
        else:
            if votebanstate.state != VoteBanStateEnum.PENDING:
                outcome = "already_concluded"
            else:
                if moderator.id in votebanstate.for_moderators_ids:
                    outcome = "already_voted"
                else:
                    votebanstate.for_moderators_ids.append(moderator.id)
                    attributes.flag_modified(
                        votebanstate, "for_moderators_ids"
                    )

                    if not (
                        len(votebanstate.for_moderators_ids) >= 4
                        or has_any_role_from_sequence(
                            moderator, ban_access_roles
                        )
                    ):
                        outcome = "success_stay_pending"
                    else:
                        votebanstate.state = VoteBanStateEnum.APPROVED
                        outcome = "success_approved"

    if outcome == "not_found":
        return await interaction.followup.send(
            embed=ErrorEmbed(
                title="Ошибка голосования",
                description="Состояние голосования за бан не найдено.",
                footer_text=bot.user.name,
                footer_icon_url=bot.user.display_avatar.url,
            ),
            ephemeral=True,
        )

    if outcome == "already_concluded":
        return await interaction.followup.send(
            embed=ErrorEmbed(
                title="Ошибка голосования",
                description="Голосование за бан уже было завершено.",
                footer_text=bot.user.name,
                footer_icon_url=bot.user.display_avatar.url,
            ),
            ephemeral=True,
        )

    if outcome == "already_voted":
        return await interaction.followup.send(
            embed=ErrorEmbed(
                title="Ошибка голосования",
                description="Вы уже голосовали в этом голосовании за бан.",
                footer_text=bot.user.name,
                footer_icon_url=bot.user.display_avatar.url,
            ),
            ephemeral=True,
        )

    view = BanRequestViewV2(
        bot=bot,
        moderator_id=votebanstate.moderator_id,  # type: ignore
        user=user,
        reason=votebanstate.reason,  # type: ignore
        original_duration=votebanstate.original_duration,  # type: ignore
        original_delete_messages_per=votebanstate.original_delete_messages_per,  # type: ignore
        for_moderators_ids=votebanstate.for_moderators_ids,  # type: ignore
        against_moderators_ids=votebanstate.against_moderators_ids,  # type: ignore
        attachments=votebanstate.attachments_urls,  # type: ignore
        ping_role_id=ping_role_id,
    )

    if outcome == "success_stay_pending":
        return await interaction.response.edit_message(
            view=view.create_component()
        )

    if outcome == "success_approved":
        view.state = VoteBanStateEnum.APPROVED

        await interaction.edit_original_response(view=view.create_component())

        data = UserBannedEventData(
            mode="dm",
            guild_name=guild.name,
            guild_id=guild.id,
            category="ban",
            moderator_id=moderator.id,
            user=user,
            reason=view.reason,
            created_at=discord.utils.utcnow().astimezone(tz=UTC),
            duration=votebanstate.duration,  # type: ignore
            original_duration=view.original_duration,
            delete_messages_per=votebanstate.original_delete_messages_per,  # type: ignore
        )

        try:
            await send_punish_dm_message(
                view.bot, guild_name=guild.name, event_data=data
            )
        except Exception as e:
            logger.exception(
                "[event] - Failed to send ban DM to user=%s guild=%s: %s",
                user.id,
                guild.id,
                e,
            )

        try:
            view.bot.dispatch("user_banned", data=data)
        except Exception as e:
            logger.exception(
                "[event] - Failed to dispatch user_banned event: %s", e
            )

        try:
            await guild.ban(
                user,
                reason=view.reason,
                delete_message_seconds=votebanstate.delete_messages_per,  # type: ignore
            )
        except (discord.Forbidden, discord.HTTPException) as e:
            logger.exception(
                "Failed to ban user=%s guild=%s: %s", user.id, guild.id, e
            )

            return await interaction.followup.send(
                embed=MissingPermissionsEmbed(
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        return


async def handle_voteban_reject_button_callback(
    interaction: Interaction["Nightcore"],
    user_id: int,
    ban_access_roles: list[int] | None,
    ping_role_id: int | None,
):
    """Handle the voteban reject button callback interaction."""
    await interaction.response.defer(ephemeral=True)

    bot = interaction.client
    guild = cast_guild(interaction.guild)
    moderator = cast_member(interaction.user)
    user = cast_member(await ensure_member_exists(guild, user_id))

    outcome = ""
    async with bot.uow.start() as session:
        votebanstate = await get_voteban_state(
            session, guild_id=guild.id, user_id=user_id
        )

        if votebanstate is None:
            outcome = "not_found"
        else:
            if votebanstate.state != VoteBanStateEnum.PENDING:
                outcome = "already_concluded"
            else:
                against_ids = votebanstate.against_moderators_ids or []

                if moderator.id in against_ids:
                    outcome = "already_voted"
                else:
                    against_ids.append(moderator.id)
                    votebanstate.against_moderators_ids = against_ids
                    attributes.flag_modified(
                        votebanstate, "against_moderators_ids"
                    )

                    if not (
                        len(against_ids) >= 4
                        or has_any_role_from_sequence(
                            moderator, ban_access_roles
                        )
                        or moderator.id == votebanstate.moderator_id
                    ):
                        outcome = "success_stay_pending"
                    else:
                        votebanstate.state = VoteBanStateEnum.DENIED
                        outcome = "success_denied"

    if outcome == "not_found":
        return await interaction.followup.send(
            embed=ErrorEmbed(
                title="Ошибка голосования",
                description="Состояние голосования за бан не найдено.",
                footer_text=bot.user.name,
                footer_icon_url=bot.user.display_avatar.url,
            ),
            ephemeral=True,
        )

    if outcome == "already_concluded":
        return await interaction.followup.send(
            embed=ErrorEmbed(
                title="Ошибка голосования",
                description="Голосование за бан уже было завершено.",
                footer_text=bot.user.name,
                footer_icon_url=bot.user.display_avatar.url,
            ),
            ephemeral=True,
        )

    if outcome == "already_voted":
        return await interaction.followup.send(
            embed=ErrorEmbed(
                title="Ошибка голосования",
                description="Вы уже голосовали в этом голосовании за бан.",
                footer_text=bot.user.name,
                footer_icon_url=bot.user.display_avatar.url,
            ),
            ephemeral=True,
        )

    view = BanRequestViewV2(
        bot=bot,
        moderator_id=votebanstate.moderator_id,  # type: ignore
        user=user,
        reason=votebanstate.reason,  # type: ignore
        original_duration=votebanstate.original_duration,  # type: ignore
        original_delete_messages_per=votebanstate.original_delete_messages_per,  # type: ignore
        for_moderators_ids=votebanstate.for_moderators_ids,  # type: ignore
        against_moderators_ids=votebanstate.against_moderators_ids,  # type: ignore
        attachments=votebanstate.attachments_urls,  # type: ignore
        ping_role_id=ping_role_id,
    )

    if outcome == "success_stay_pending":
        return await interaction.response.edit_message(
            view=view.create_component()
        )

    if outcome == "success_denied":
        view.state = VoteBanStateEnum.DENIED
        return await interaction.edit_original_response(
            view=view.create_component()
        )
