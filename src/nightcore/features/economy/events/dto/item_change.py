"""DTO for item change notify event."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from discord import Color, Embed, Guild, Role

from src.infra.db.models._annot import CaseDropAnnot
from src.infra.db.models._enums import ItemChangeActionEnum
from src.infra.db.models.case import Case

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


@dataclass
class ChangedRole:
    after: Role
    before: Role | None = None


@dataclass
class ChangedReward:
    after: CaseDropAnnot
    before: CaseDropAnnot | None = None


@dataclass
class ChangedCase:
    after: Case
    before: Case | None = None


@dataclass
class ItemChangeNotifyEventDTO:
    """DTO for item change notify event."""

    guild: Guild
    event_type: str
    logging_channel_id: int | None
    moderator_id: int
    item_name: str
    item: ChangedRole | ChangedReward | ChangedCase

    def build_log_embed(self, bot: "Nightcore") -> Embed:
        """Build and return the log embed for the event."""

        color = Color.dark_purple()
        title = "Изменение предмета"

        field_name, field_value = None, None

        match self.event_type:
            case ItemChangeActionEnum.CREATE.value:
                color = Color.green()
                title = "Создание предмета"

            case ItemChangeActionEnum.COLOR_UPDATE.value:
                if isinstance(self.item, ChangedRole) and self.item.before:
                    field_name = "Изменение цвета"
                    field_value = (
                        f"{self.item.before.id} -> {self.item.after.id}"
                    )

            case ItemChangeActionEnum.UPDATE_REWARD.value:
                field_name = "Изменение награды"
                if isinstance(self.item, ChangedReward) and self.item.before:
                    field_value = f"{_format_reward(self.item.after)} -> {_format_reward(self.item.before)}"  # noqa: E501

            case ItemChangeActionEnum.DELETE_REWARD.value:
                field_name = "Удаленная награда"
                if isinstance(self.item, ChangedReward):
                    field_value = _format_reward(self.item.after)

            case ItemChangeActionEnum.ADD_REWARD.value:
                if isinstance(self.item, ChangedReward):
                    field_name = "Добавленная награда"

                    field_value = _format_reward(self.item.after)

            case ItemChangeActionEnum.CASE_UPDATE:
                if isinstance(self.item, ChangedCase) and self.item.before:
                    field_name = "Изменение кейса"

                    field_value = f"Название: {self.item.after.name} -> {self.item.before.name} "  # noqa: E501
            case _:
                pass

        embed = (
            Embed(
                title=title,
                color=color,
                timestamp=datetime.now(UTC),
            )
            .add_field(
                name="Инициатор",
                value=f"<@{self.moderator_id}> (`{self.moderator_id}`)",
            )
            .add_field(name="Предмет", value=f"**{self.item_name}**")
            .set_footer(
                text="Powered by nightcore",
                icon_url=bot.user.display_avatar.url,  # type: ignore
            )
        )

        if field_value and field_name:
            embed.add_field(name=field_name, value=field_value)

        return embed


def _format_reward(reward: CaseDropAnnot) -> str:
    return (
        f"{reward['name']}, "
        f"шанс: {reward['chance']}, "
        f"количество: {reward['amount']}, "
        f"тип награды: {reward['type'].name}"
    )
