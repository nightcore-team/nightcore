"""Role members view v2 component."""

from typing import Self

from discord import ButtonStyle, Color
from discord.ui import (
    ActionRow,
    Button,
    Container,
    LayoutView,
    Separator,
    TextDisplay,
)

DOCS_URL = "https://docs.nightcore.space/"
PANEL_URL = "https://nightcore.space/"


class HelpLinksActionRow(ActionRow["HelpViewV2"]):
    def __init__(self) -> None:
        super().__init__()

        self.add_item(
            Button(
                style=ButtonStyle.link,
                label="Nightcore Documentation",
                url=DOCS_URL,
                emoji="<:nightcoreDocs:1542917035703668861>",
            )
        )
        self.add_item(
            Button(
                style=ButtonStyle.link,
                label="Nightcore Dashboard",
                url=PANEL_URL,
                emoji="<:nightcoreDashboard:1542917258970669137>",
            )
        )


class HelpViewV2(LayoutView):
    def __init__(self) -> None:
        super().__init__(timeout=None)

        container = Container[Self](accent_color=Color.from_str("#D896C8"))

        container.add_item(
            TextDisplay(
                "### <:nightcoreLogoPink:1542907722939236424> Nightcore /help\n"  # noqa: E501
                "Вся информация о боте — в документации, "
                "управление — через панель."
            )
        )
        container.add_item(Separator())
        container.add_item(HelpLinksActionRow())

        self.add_item(container)
