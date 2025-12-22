"""DTO for clan shop order notification event."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import discord
from discord import Colour, Embed, Guild

from src.infra.db.models._enums import ClanManageActionEnum
from src.nightcore.events.dto.base import BaseEventDTO

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


@dataclass
class ClanManageNotifyDTO(BaseEventDTO):
    guild: Guild
    event_type: str
    clan_name: str
    actions: set[ClanManageActionEnum]
    actor: discord.Member
    logging_channel_id: int | None

    def build_log_embed(self, bot: "Nightcore") -> Embed:
        """Build and return the log embed for the event."""

        ...
