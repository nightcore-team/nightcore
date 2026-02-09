"""Command to send a valentine."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, Member, app_commands
from discord.interactions import Interaction

from src.infra.db.models._enums import ChannelType
from src.infra.db.models.guild import GuildLoggingConfig
from src.nightcore.components.embed import ErrorEmbed
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

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.infra.db.operations import get_or_create_user, get_specified_channel
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

logger = logging.getLogger(__name__)


@valentine_group.command(name="send", description="Отправить валентинку")  # type: ignore
@app_commands.checks.cooldown(
    1,
    20 * 60,
    key=lambda i: (i.guild.id, i.user.id),  # type: ignore
)
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

    # generate valentine image
    image = await generate_valentine_image(text, cache=bot.images_cache)

    to_user_valentine_count = 0
    try:
        async with bot.uow.start() as session:
            sender, _ = await get_or_create_user(
                session, guild_id=guild.id, user_id=interaction.user.id
            )

            sender.sended_valentines += sender.sended_valentines + 1

            recipient, _ = await get_or_create_user(
                session, guild_id=guild.id, user_id=member.id
            )
            recipient.received_valentines += recipient.received_valentines + 1
            to_user_valentine_count = recipient.received_valentines

            logging_channel_id = await get_specified_channel(
                session,
                guild_id=guild.id,
                config_type=GuildLoggingConfig,
                channel_type=ChannelType.LOGGING_ECONOMY,
            )

    except Exception as e:
        logger.exception("Error while sending valentine: %s", e)
        await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка отправки валентинки",
                "Произошла ошибка при отправке валентинки.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )
        return

    # build view with the image and checking if the user wants to send it anonymously  # noqa: E501
    view = ValentineViewV2(
        bot=bot,
        image_uri=image.uri,
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
    except Exception as e:
        logger.exception("Error while sending valentine: %s", e)
        await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка отправки валентинки",
                "Произошла ошибка при отправке валентинки.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )
        return

    dto = ValentineSendEventDTO(
        guild=guild,
        event_type="send",
        logging_channel_id=logging_channel_id,  # type: ignore
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
