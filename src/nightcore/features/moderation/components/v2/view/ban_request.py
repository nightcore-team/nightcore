"""View for paginating infractions."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Self

from discord import (
    ButtonStyle,
    Color,
    MediaGalleryItem,
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
)

if TYPE_CHECKING:
    from discord import Member, User

    from src.nightcore.bot import Nightcore

from src.infra.db.models._enums import VoteBanStateEnum
from src.nightcore.utils import discord_ts


class BanRequestViewV2(LayoutView):
    def __init__(
        self,
        bot: "Nightcore",
        moderator_id: int,
        user: "User | Member",
        reason: str,
        original_duration: str,
        original_delete_messages_per: str | None = None,
        ping_role_id: int | None = None,
        state: "VoteBanStateEnum" = VoteBanStateEnum.PENDING,
        attachments: list[str] | None = None,
        for_moderators_ids: list[int] | None = None,
        against_moderators_ids: list[int] | None = None,
    ):
        super().__init__(timeout=None)

        self.bot = bot
        self.moderator_id = moderator_id
        self.user = user
        self.reason = reason
        self.original_duration = original_duration
        self.original_delete_messages_per = original_delete_messages_per
        self.ping_role_id = ping_role_id
        self.state = state
        self.attachments = attachments
        self.for_moderators_ids = for_moderators_ids
        self.against_moderators_ids = against_moderators_ids

    def create_component(self) -> Self:
        """Create the view component based on the current state."""

        accent_color: Color | None = None

        match self.state:
            case VoteBanStateEnum.APPROVED:
                accent_color = Color.green()
            case VoteBanStateEnum.DENIED:
                accent_color = Color.red()
            case _:
                accent_color = None

        container = Container[Self](accent_color=accent_color)

        pre_header_text = "## Запрос на бан"
        if self.ping_role_id:
            pre_header_text += f" <@&{self.ping_role_id}>"

        container.add_item(TextDisplay[Self](pre_header_text))
        container.add_item(Separator[Self]())

        container.add_item(
            Section[Self](
                TextDisplay[Self](
                    f"**Пользователь:** {self.user.mention} (`{self.user.id}`)\n"  # noqa: E501
                    f"**Модератор:** <@{self.moderator_id}>\n"
                    f"**Причина: {self.reason}**\n"
                    f"**Длительность: {self.original_duration}**\n"
                    f"**Удалить сообщения за последние: `{self.original_delete_messages_per if self.original_delete_messages_per else 'N/A'}`**\n"  # noqa: E501
                ),
                accessory=Thumbnail(self.user.display_avatar.url),
            )
        )
        container.add_item(Separator[Self]())

        container.add_item(TextDisplay[Self]("### За:"))
        if self.for_moderators_ids:
            container.add_item(
                TextDisplay[Self](
                    "".join(f"- <@{id}>\n" for id in self.for_moderators_ids)
                )
            )

        container.add_item(TextDisplay[Self]("### Против:"))
        if self.against_moderators_ids:
            container.add_item(
                TextDisplay[Self](
                    "".join(
                        f"- <@{id}>\n" for id in self.against_moderators_ids
                    )
                )
            )

        container.add_item(Separator[Self]())

        if self.attachments:
            container.add_item(TextDisplay[Self]("### Вложения:"))
            container.add_item(
                MediaGallery[Self](
                    *[MediaGalleryItem(url) for url in self.attachments]
                )
            )
            container.add_item(Separator[Self]())

        container.add_item(
            ActionRow[Self](
                Button(
                    style=ButtonStyle.green,
                    emoji="<:check:1442915033079353404>",
                    label="Одобрить",
                    custom_id=f"voteban:{self.user.id}:approve",
                    disabled=self.state != VoteBanStateEnum.PENDING,
                ),
                Button(
                    style=ButtonStyle.red,
                    emoji="<:failed:1442915170320912506>",
                    label="Отклонить",
                    custom_id=f"voteban:{self.user.id}:deny",
                    disabled=self.state != VoteBanStateEnum.PENDING,
                ),
            )
        )
        container.add_item(Separator[Self]())

        # Footer
        now = datetime.now(UTC)

        container.add_item(
            TextDisplay["BanRequestViewV2"](
                f"-# Powered by {self.bot.user.name} in {discord_ts(now)}"
            )
        )

        self.add_item(container)

        return self
