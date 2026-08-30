"""Command to send a valentine."""

import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, cast

from discord import Guild, Member, app_commands
from discord.interactions import Interaction
from sqlalchemy import select

from src.infra.db.models import GuildLoggingConfig, User
from src.infra.db.operations import get_or_create_user, get_specified_webhook
from src.nightcore.components.view.v2 import ErrorViewV2
from src.nightcore.features.special_events.valentine._groups import (
    valentine as valentine_group,
)
from src.nightcore.features.special_events.valentine.components.v2 import (
    ValentineViewV2,
)
from src.nightcore.features.special_events.valentine.events.dto.valentine_send import (  # noqa: E501
    ValentineSendEventDTO,
)
from src.nightcore.features.special_events.valentine.utils.valentine_image import (  # noqa: E501
    generate_valentine_image,
)
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)
from src.utils._enums import ChannelType

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


async def _check_valentine_cooldown(
    session,
    guild_id: int,
    user_id: int,
) -> bool:
    """Check if user can send valentine (cooldown check)."""
    from sqlalchemy import select
    from src.infra.db.models import User

    stmt = (
        select(User)
        .where(User.guild_id == guild_id, User.user_id == user_id)
        .with_for_update()
    )
    user = await session.scalar(stmt)
    if user is None:
        return True  # new user, no cooldown
    if user.valentine_cooldown_until is None:
        return True  # no cooldown
    if user.valentine_cooldown_until <= datetime.now(UTC):
        return True  # cooldown expired
    return False  # still on cooldown


async def _set_valentine_cooldown(
    session,
    guild_id: int,
    user_id: int,
) -> None:
    """Set valentine cooldown for user (20 minutes)."""
    user = await session.scalar(
        select(User)
        .where(User.guild_id == guild_id, User.user_id == user_id)
        .with_for_update()
    )
    if user:
        user.valentine_cooldown_until = datetime.now(UTC) + timedelta(
            minutes=20
        )


@valentine_group.command(name="send", description="Отправить валентинку")  # type: ignore
@app_commands.describe(
    user="Пользователь, которому вы хотите отправить валентинку",
    where_to_send="Куда вы хотите отправить валентинку",
    text="Текст на валентинке (1-20 символов)",
    is_anonymous="Отправить валентинку анонимно",
)
@check_required_permissions(PermissionsFlagEnum.NONE)  # type: ignore
@app_commands.choices(
    where_to_send=[
        app_commands.Choice(name="В текущий чат", value="channel"),
        app_commands.Choice(name="В личные сообщения", value="dm"),
    ]
)
@app_commands.rename(
    user="пользователь",
    where_to_send="место_отправки",
    text="текст",
    is_anonymous="анонимно",
)
async def send_valentine(
    interaction: Interaction["Nightcore"],
    user: Member,
    where_to_send: app_commands.Choice[str],
    text: app_commands.Range[str, 5, 450],
    is_anonymous: bool = False,
):
    """Send a valentine."""

    member = user
    guild = cast(Guild, interaction.guild)
    bot = interaction.client

    # Check valentine cooldown using database
    async with bot.uow.start() as session:
        can_send = await _check_valentine_cooldown(
            session, guild.id, interaction.user.id
        )
        if not can_send:
            await interaction.response.send_message(
                view=ErrorViewV2(
                    "Ошибка отправки валентинки",
                    (
                        "Вы можете отправлять валентинки "
                        "не чаще одного раза в 20 минут."
                    ),
                ),
                ephemeral=True,
            )
            return

    if member.bot:
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка отправки валентинки",
                "Очень приятно, но Вы не можете отправить валентинку мне.",
            ),
            ephemeral=True,
        )
        return

    if member.id == interaction.user.id:
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка отправки валентинки",
                "Вы не можете отправить валентинку самому себе.",
            ),
            ephemeral=True,
        )
        return

    # generate valentine image
    image = await generate_valentine_image(text, cache=bot.images_cache)
    image_bytes = image.fp.read()
    image.fp.seek(0)

    to_user_valentine_count = 0
    try:
        async with bot.uow.start() as session:
            sender, _ = await get_or_create_user(
                session, guild_id=guild.id, user_id=interaction.user.id
            )

            sender.sended_valentines += 1

            recipient, _ = await get_or_create_user(
                session, guild_id=guild.id, user_id=member.id
            )
            recipient.received_valentines += 1
            to_user_valentine_count = recipient.received_valentines

            logging_webhook = await get_specified_webhook(
                session,
                guild_id=guild.id,
                config_type=GuildLoggingConfig,
                channel_type=ChannelType.LOGGING_ECONOMY,
            )

    except Exception as e:
        logger.exception("Error while sending valentine: %s", e)
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка отправки валентинки",
                "Произошла ошибка при отправке валентинки.",
            ),
            ephemeral=True,
        )
        return

    # build view with the image and checking if the user wants to send it anonymously  # noqa: E501
    view = ValentineViewV2(
        bot=bot,
        image_bytes=image_bytes,
        from_user=interaction.user,
        to_user=member,
        to_user_valentine_count=to_user_valentine_count,
        is_anonymous=is_anonymous,
    )

    try:
        if where_to_send.value == "channel":
            await interaction.channel.send(view=view)  # type: ignore
            await interaction.response.send_message(
                "Валентинка успешно отправлена в этот чат! ❤️",
                ephemeral=True,
            )
        else:
            await member.send(
                view=view,
            )
            await interaction.response.send_message(
                "Валентинка успешно отправлена в личные сообщения получателя! ❤️",  # noqa: E501
                ephemeral=True,
            )
        # Set cooldown after successful send
        async with bot.uow.start() as session:
            await _set_valentine_cooldown(
                session, guild.id, interaction.user.id
            )
    except Exception as e:
        logger.exception("Error while sending valentine: %s", e)
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка отправки валентинки",
                "Произошла ошибка при отправке валентинки.",
            ),
            ephemeral=True,
        )
        return

    dto = ValentineSendEventDTO(
        guild=guild,
        event_type="send",
        logging_webhook=logging_webhook,  # type: ignore
        user_id=interaction.user.id,
        reciever_id=user.id,
        text=text,
    )

    bot.dispatch("valentine_send", dto=dto)

    logger.info(
        "Valentine sent successfully to user %s in guild %s by user %s (anonymous: %s)",  # noqa: E501
        member.id,
        guild.id,
        interaction.user.id,
        is_anonymous,
    )
