"""1."""

import io
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Self

from discord import (
    ButtonStyle,
    Color,
    File,
    Interaction,
    MediaGalleryItem,
    Member,
    User,
)
from discord.ui import (
    ActionRow,
    Button,
    Container,
    LayoutView,
    MediaGallery,
    Section,
    Separator,
    TextDisplay,
    Thumbnail,
    button,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.utils import discord_ts


class ValentineMediaView(LayoutView):
    def __init__(self, image_bytes: bytes) -> None:
        super().__init__(timeout=None)

        image_file = File(fp=io.BytesIO(image_bytes), filename="image.png")
        media_gallery_item = MediaGalleryItem(image_file)

        container = Container[Self](accent_color=Color.from_str("#fed8df"))

        container.add_item(MediaGallery[Self](media_gallery_item))

        self.add_item(container)


class ShowValetineActionRow(ActionRow["ValentineViewV2"]):
    def __init__(self, image_bytes: bytes) -> None:
        super().__init__()

        self.image_bytes = image_bytes

    @button(
        label="Посмотреть валентинку",
        style=ButtonStyle.grey,
        emoji="<:heart2:1470360578316046426>",
        custom_id="valentine:show",
    )
    async def show_valentine(
        self, interaction: Interaction, button: Button["ValentineViewV2"]
    ):
        """Show valentine button callback."""

        image_file = File(
            fp=io.BytesIO(self.image_bytes), filename="image.png"
        )
        return await interaction.response.send_message(
            view=ValentineMediaView(image_bytes=self.image_bytes),
            files=[image_file],
            ephemeral=True,
        )


class ValentineViewV2(LayoutView):
    def __init__(
        self,
        bot: "Nightcore",
        image_bytes: bytes,
        from_user: User | Member,
        to_user: User | Member,
        to_user_valentine_count: int,
        is_anonymous: bool,
    ) -> None:
        super().__init__(timeout=None)

        container = Container[Self](accent_color=Color.from_str("#fed8df"))

        header_text = (
            f"{to_user.mention}, Вы получити валентинку от пользователя **{from_user}**"  # noqa: E501
            if not is_anonymous
            else f"{to_user.mention}, Вы получили анонимную валентинку"
        )

        valentine_text = (
            "> Это ваша первая валентинка <:heart2:1470360578316046426>"
            if to_user_valentine_count == 0
            else "> Это уже не первая валентинка, которую вы получаете <:heart2:1470360578316046426>"  # noqa: E501
        )

        container.add_item(
            Section[Self](
                TextDisplay[Self](
                    "## <:valentine_paper:1470362624267911306> День святого Валентина"  # noqa: E501
                    f"\n{header_text}\n{valentine_text}"
                ),
                accessory=Thumbnail[Self](to_user.display_avatar.url),
            )
        )
        container.add_item(Separator[Self]())

        container.add_item(ShowValetineActionRow(image_bytes))
        container.add_item(Separator[Self]())

        now = datetime.now(UTC)

        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {bot.user.name} in {discord_ts(now)}"  # type: ignore
            )
        )

        self.add_item(container)
