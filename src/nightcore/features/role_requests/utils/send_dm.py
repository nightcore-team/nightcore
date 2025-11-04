import logging

from discord import Member

from src.infra.db.models._enums import RoleRequestStateEnum

logger = logging.getLogger(__name__)

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
