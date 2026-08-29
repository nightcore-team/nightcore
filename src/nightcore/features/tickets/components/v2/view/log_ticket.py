"""View for logging deleted user tickets."""

from typing import Self

from discord import Color, File, MediaGalleryItem
from discord.ui import (
    Container,
    LayoutView,
    MediaGallery,
    Separator,
    TextDisplay,
)


class LogDeletedTicketViewV2(LayoutView):
    def __init__(
        self, ticket_channel_name: str, guild_name: str, log_file: File
    ):
        """Create the layout view component."""
        super().__init__(timeout=None)

        container = Container[Self](accent_color=Color.from_str("#5DADE2"))

        container.add_item(
            TextDisplay[Self](
                "### <:nightcoreTicketDeleted:1543208049588568104> Тикен удалён"  # noqa: E501
            )
        )
        container.add_item(
            TextDisplay[Self](
                f"Ваш тикет {ticket_channel_name} на сервере {guild_name} был удален.\n"  # noqa: E501
                "Для просмотра истории сообщений загрузите файл и откройте в браузере."  # noqa: E501
            )
        )
        container.add_item(Separator())
        container.add_item(MediaGallery[Self](MediaGalleryItem(log_file)))

        self.add_item(container)
