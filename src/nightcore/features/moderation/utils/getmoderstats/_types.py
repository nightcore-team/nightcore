from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Self

if TYPE_CHECKING:
    from src.infra.db.models import ChangeStat


@dataclass
class ModerationScores:
    """Configuration for moderation action scores."""

    mute: float
    ban: float
    kick: float
    vmute: float
    mpmute: float
    ticketban: float
    closed_tickets: float
    approved_role_requests: float
    removed_roles: float
    message: float

    @classmethod
    def from_dict(cls, data: dict[str, float]) -> Self:
        """Create ModerationScores from database config dict.

        Args:
            data: Dict with score values from database

        Returns:
            ModerationScores instance

        Example:
            >>> scores_dict = {"mute_score": 1.0, "ban_score": 5.0, ...}
            >>> scores = ModerationScores.from_dict(scores_dict)
        """

        return cls(
            mute=data.get("mute_score", 0),
            ban=data.get("ban_score", 0),
            kick=data.get("kick_score", 0),
            vmute=data.get("vmute_score", 0),
            mpmute=data.get("mpmute_score", 0),
            ticketban=data.get("ticketban_score", 0),
            closed_tickets=data.get("tickets_score", 0),
            approved_role_requests=data.get("approved_role_requests_score", 0),
            removed_roles=data.get("changed_roles_score", 1.0),
            message=data.get("message_score", 0.01),
        )


@dataclass
class ModeratorStats:
    """Calculated moderation statistics for a single moderator."""

    moderator_id: int
    nickname: str

    mute_count: int = 0
    ban_count: int = 0
    kick_count: int = 0
    vmute_count: int = 0
    mpmute_count: int = 0
    ticketban_count: int = 0
    removed_roles_count: int = 0

    closed_tickets_count: int = 0
    approved_role_requests_count: int = 0
    total_messages: int = 0

    deducted_points: float = 0.0

    changestat_details: list[ChangeStat] = field(default_factory=list)  # type: ignore

    def calculate_total_points(self, scores: ModerationScores) -> float:
        """Calculate total points based on scores configuration.

        Args:
            scores: ModerationScores with point values

        Returns:
            Total calculated points
        """

        return (
            self.mute_count * scores.mute
            + self.ban_count * scores.ban
            + self.kick_count * scores.kick
            + self.vmute_count * scores.vmute
            + self.mpmute_count * scores.mpmute
            + self.ticketban_count * scores.ticketban
            + self.removed_roles_count * scores.removed_roles
            + self.closed_tickets_count * scores.closed_tickets
            + self.total_messages * scores.message
            + self.approved_role_requests_count * scores.approved_role_requests
            + self.deducted_points
        )

    def format_stats(self) -> str:
        """Format statistics as display string.

        Args:
            scores: ModerationScores for total points calculation

        Returns:
            Formatted string for display
        """

        return (
            f"> **Муты:** {self.mute_count}\n"
            f"> **Баны:** {self.ban_count}\n"
            f"> **Кики:** {self.kick_count}\n"
            f"> **Войс муты:** {self.vmute_count}\n"
            f"> **МП муты:** {self.mpmute_count}\n"
            f"> **Тикет баны:** {self.ticketban_count}\n"
            f"> **Снятые роли:** {self.removed_roles_count}\n"
            f"> **Закрытые тикеты:** {self.closed_tickets_count}\n"
            f"> **Одобренные запросы ролей:** {self.approved_role_requests_count}\n"  # noqa: E501
            f"> **Всего сообщений:** {self.total_messages}\n"
        )

    def format_changestat_history_first_5(self) -> str:
        """Format changestat history for display.

        Returns:
            Formatted history string or message if empty
        """

        if not self.changestat_details:
            return "> Нет истории изменений статистики."

        lines: list[str] = []
        for cs in self.changestat_details[:5]:
            timestamp = f"<t:{int(cs.time_now.timestamp())}:R>"
            lines.append(
                f"> {timestamp} <:42920arrowrightalt:1421170550759489616> **`{cs.type.value.upper()}`** | **Баллы:** **`{cs.amount}`** | **Причина:** {cs.reason}"  # noqa: E501
            )

        return "\n".join(lines)

    def format_changestats_history(self) -> str:
        """Format full changestat history for display.

        Returns:
            Formatted history string or message if empty
        """

        if not self.changestat_details:
            return "> Нет истории изменений статистики."

        lines: list[str] = []
        for cs in self.changestat_details:
            timestamp = f"<t:{int(cs.time_now.timestamp())}:R>"
            lines.append(
                f"{timestamp} <:42920arrowrightalt:1421170550759489616> **`{cs.type.value.upper()}`** | **Баллы:** **`{cs.amount}`** | **Причина:** {cs.reason}"  # noqa: E501
            )

        return "\n".join(lines)
