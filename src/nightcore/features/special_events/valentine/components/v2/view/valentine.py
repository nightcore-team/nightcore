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

    async def interaction_check(self, interaction: Interaction) -> bool:
        """Check if the user can interact with the button."""
        if interaction.user.id != self.view.to_user.id:  # type: ignore
            await interaction.response.send_message(
                "Извините, но вы не можете взаимодействовать с этой кнопкой, так как она предназначена для другого пользователя.",  # noqa: E501
                ephemeral=True,
            )
            return False
        return True

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

        self.to_user = to_user

        container = Container[Self](accent_color=Color.from_str("#fed8df"))

        header_text = (
            f"{to_user.mention}, для вас есть валентинка <:heart1:1470356474525122613>\n"  # noqa: E501
            f"От **{from_user}**, с теплом и симпатией"
            if not is_anonymous
            else f"{to_user.mention}, для вас есть валентинка <:heart1:1470356474525122613>\n"  # noqa: E501
            "От кого-то, кто решил остаться инкогнито..."
        )

        valentine_text = (
            "> Это ваша самая первая валентинка <:heart1:1470356474525122613>\n"  # noqa: E501
            "> Пусть она поднимет вам настроение"
            if to_user_valentine_count == 0
            else "> Любовь снова нашла вас <:heart1:1470356474525122613>\n"
            "> Вы уже не в первый раз получаете валентинку"
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
