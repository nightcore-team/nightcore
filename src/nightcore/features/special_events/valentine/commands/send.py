"""Command to send a valentine."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, Member, app_commands
from discord.interactions import Interaction

from src.nightcore.components.embed import ErrorEmbed
from src.nightcore.features.special_events.valentine.commands._groups import (
    valentine as valentine_group,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.infra.db.operations import get_or_create_user
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

logger = logging.getLogger(__name__)


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
    where_to_send="место отправки",
    text="текст",
    anonymous="анонимно",
)
async def send_valentine(
    interaction: Interaction["Nightcore"],
    user: Member,
    where_to_send: app_commands.Choice[str],
    text: app_commands.Range[str, 1, 20],
    is_anonymous: bool = False,
):
    """Send a valentine."""

    member = user
    guild = cast(Guild, interaction.guild)
    bot = interaction.client

    # generate valentine image
    # image = generate_valentine_image(text)

    # build view with the image and checking if the user wants to send it anonymously  # noqa: E501
    # view = ValentineView(image, is_anonymous, bot, user)

    try:
        if where_to_send.value == "channel":
            await interaction.response.send_message()
        else:
            await member.send()

    except Exception as e:
        logger.exception("Failed to send valentine: %s", e)

        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка отправки валентинки",
                "Произошла ошибка при отправке валентинки.",
                bot.user.name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            )
        )

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

    except Exception as e:
        logger.exception("Failed to send valentine: %s", e)

    logger.info(
        "Valentine sent successfully to user %s in guild %s by user %s (anonymous: %s)",  # noqa: E501
        member.id,
        guild.id,
        interaction.user.id,
        is_anonymous,
    )
