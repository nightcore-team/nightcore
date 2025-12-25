"""DTO for clan manage notify event."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from discord import Colour, Embed, Guild

from src.infra.db.models._enums import ClanManageActionEnum
from src.nightcore.events.dto.base import BaseEventDTO

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


@dataclass
class ClanManageAction:
    type: ClanManageActionEnum
    before: str | None = None
    after: str | None = None


@dataclass
class ClanManageNotifyDTO(BaseEventDTO):
    guild: Guild
    event_type: str
    clan_name: str
    actions: list[ClanManageAction]
    actor_id: int
    logging_channel_id: int | None

    def build_log_embed(self, bot: "Nightcore") -> Embed:
        """Build and return the log embed for the event."""

        embed = (
            Embed(
                title="Клан был изменен",
                timestamp=datetime.now(UTC),
                color=Colour.blue(),
            )
            .add_field(
                name="Клан",
                value=f"**{self.clan_name}**",
                inline=True,
            )
            .add_field(
                name="Инициатор",
                value=f"<@{self.actor_id}> (`{self.actor_id}`)",
                inline=True,
            )
            .set_footer(
                text="Powered by nightcore",
                icon_url=bot.user.display_avatar.url,  # type: ignore
            )
        )

        for action in self.actions:
            match action.type:
                case ClanManageActionEnum.CREATE:
                    embed.title = "Создание клана"
                    embed.color = Colour.green()
                case ClanManageActionEnum.DELETE:
                    embed.title = "Удаление клана"
                    embed.color = Colour.red()
                case _:
                    value = (
                        action.after
                        if action.before is None
                        else f"{action.before} -> {action.after}"
                    )

                    embed.add_field(name=action.type, value=value, inline=True)

        return embed
