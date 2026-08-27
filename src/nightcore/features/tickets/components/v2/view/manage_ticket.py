"""View for managing tickets."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Self, cast

from discord import ButtonStyle, Color
from discord.ui import (
    ActionRow,
    Button,
    Container,
    LayoutView,
    Separator,
    TextDisplay,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.components.view.v2 import BaseErrorViewV2
from src.nightcore.utils.time_utils import discord_ts
from src.utils._enums import TicketStateEnum


class TicketStateViewV2(LayoutView):
    def __init__(
        self,
        bot: "Nightcore",
        state: TicketStateEnum,
        moderator_id: int,
        author_id: int,
    ) -> None:
        super().__init__(timeout=None)

        self.clear_items()

        container = Container[Self](accent_color=Color.from_str("#5DADE2"))

        message: str = ""
        match state:
            case TicketStateEnum.OPENED:
                message = f"### <@{author_id}>, тикет был открыт модератором <@{moderator_id}>"  # noqa: E501
            case TicketStateEnum.PINNED:
                message = f"### <@{author_id}>, тикет был закреплен модератором <@{moderator_id}>"  # noqa: E501
            case TicketStateEnum.CLOSED:
                message = f"### <@{author_id}>, тикет был закрыт модератором <@{moderator_id}>"  # noqa: E501
            case _:
                message = "Неизвестное состояние."

        container.add_item(
            TextDisplay[Self](message.format(f"<@{moderator_id}>"))
        )

        self.add_item(container)


class ManageTicketButtons(ActionRow["ManageTicketViewV2"]):
    def __init__(self):
        super().__init__()

        self.add_item(
            Button[Any](
                style=ButtonStyle.grey,
                label="Закрепить",
                emoji="<:nightcoreTicketPin:1540819251508682782>",
                custom_id="ticket:pin",
            )
        )

        self.add_item(
            Button[Any](
                style=ButtonStyle.grey,
                label="Открыть",
                emoji="<:nightcoreTicketOpen:1540818951586586754>",
                custom_id="ticket:reopen",
            )
        )

        self.add_item(
            Button[Any](
                style=ButtonStyle.grey,
                label="Закрыть",
                emoji="<:nightcoreTicketClose:1540819066694926456>",
                custom_id="ticket:close",
            )
        )


class ManageTicketViewV2(BaseErrorViewV2, LayoutView):
    def __init__(
        self,
        bot: "Nightcore",
        ping_role_id: int | None = None,
        interaction_user_id: int | None = None,
    ):
        """Create the layout view component."""
        super().__init__(timeout=None)

        self.bot = bot
        self.ping_role_id = cast(int, ping_role_id)
        self.interaction_user_id = interaction_user_id

        self.clear_items()

        container = Container[Self](accent_color=Color.from_str("#5DADE2"))

        # Main text
        container.add_item(
            TextDisplay[Self](
                f"### <:nightcoreTicketNew:1540818406977052812> Обращение от пользователя <@{interaction_user_id}> \n> Если у вас есть жалобы на работу модераторов, пожалуйста, обратитесь на [форум Arz Guard](https://forum.arzguard.com)."  # noqa: E501
            )
        )

        # Action row
        container.add_item(Separator[Self]())
        container.add_item(ManageTicketButtons())
        container.add_item(Separator[Self]())

        # Footer
        now = datetime.now(UTC)
        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {self.bot.user.name} in {discord_ts(now)} | <@&{ping_role_id}>"  # type: ignore  # noqa: E501
            )
        )

        self.add_item(container)
