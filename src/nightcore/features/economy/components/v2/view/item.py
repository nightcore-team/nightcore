from datetime import datetime, timezone
from typing import TYPE_CHECKING, Self

from discord.ui import Container, LayoutView, Separator, TextDisplay

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.utils import discord_ts


class AwardNotificationViewV2(LayoutView):
    def __init__(
        self, bot: "Nightcore", user_id: int, item_name: str, amount: int
    ):
        super().__init__(timeout=30)

        container = Container[Self]()

        container.add_item(
            TextDisplay[Self](
                "## <:73173rocket:1432056646456049736> Уведомление о выдаче предмета"  # noqa: E501, RUF001
            )
        )
        container.add_item(Separator[Self]())

        container.add_item(
            TextDisplay[Self](f"<@{user_id}> вам выдал(а) предмет.")  # noqa: RUF001
        )
        container.add_item(Separator[Self]())

        container.add_item(TextDisplay[Self]("### Информация о предмете: "))  # noqa: RUF001
        container.add_item(
            TextDisplay[Self](
                f"> Название: **{item_name}**\n> Количество: **{amount}**"
            )
        )
        container.add_item(Separator[Self]())

        now = datetime.now(timezone.utc)
        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {bot.user.name} in {discord_ts(now)}"  # type: ignore
            )
        )

        self.add_item(container)
