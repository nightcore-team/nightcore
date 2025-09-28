import logging

from discord import Member

from src.infra.db.models._enums import RoleRequestStateEnum
from src.nightcore.utils import ensure_messageable_channel_exists

logger = logging.getLogger(__name__)

REQUESTED_MESSAGE = """
<:72151staff:1421169506230866050> | STATS <:42920arrowrightalt:1421170550759489616> <@{user_id}>, модератор <@{moderator_id}> запросил у вас статистику игрового аккаунта.
> Как правильно предоставить статистику?

1. Сделайте в игре скриншот вашей статистики `[/stats + /time]`.
2. Отправьте вашу статистику боту который прислал вам данное сообщение.
3. В случае, если модерация не рассматривает ваш запрос, то попробуйте отправить статистику модератору который принял ваш запрос.
"""  # noqa: E501, RUF001

APPROVED_MESSAGE = """
<:52104checkmark:1414732973005340672> | APPROVED <:42920arrowrightalt:1421170550759489616> <@{user_id}>, модератор <@{moderator_id}> одобрил ваш запрос на роль.
"""  # noqa: E501

DENIED_MESSAGE = """
<:9349_nope:1414732960841859182> | DENIED <:42920arrowrightalt:1421170550759489616> <@{user_id}>, модератор <@{moderator_id}> отклонил ваш запрос на роль.

Причина: {reason}
"""  # noqa: E501


async def send_role_request_dm(
    moderator_id: int,
    reserve_channel: int | None,
    user: Member,
    state: RoleRequestStateEnum,
    reason: str | None = None,
) -> None:
    """Send a DM to the user about their role request status."""
    match state:
        case RoleRequestStateEnum.REQUESTED:
            try:
                await user.send(
                    REQUESTED_MESSAGE.format(
                        user_id=user.id, moderator_id=moderator_id
                    )
                )
            except Exception:
                if not reserve_channel:
                    logger.error(
                        "Nightcore nofications channel not set in %s",
                        user.guild.id,
                    )
                    return
                channel = await ensure_messageable_channel_exists(
                    user.guild, reserve_channel
                )
                if not channel:
                    logger.error(
                        "Failed to fetch nightcore notifications channel %s in %s",  # noqa: E501
                        reserve_channel,
                        user.guild.id,
                    )
                    return

                await channel.send(  # type: ignore
                    REQUESTED_MESSAGE.format(
                        user_id=user.id, moderator_id=moderator_id
                    )
                )

        case RoleRequestStateEnum.APPROVED:
            await user.send(
                APPROVED_MESSAGE.format(
                    user_id=user.id, moderator_id=moderator_id
                )
            )
        case RoleRequestStateEnum.DENIED:
            await user.send(
                DENIED_MESSAGE.format(
                    user_id=user.id,
                    moderator_id=moderator_id,
                    reason=reason,
                )
            )
        case _:
            ...
