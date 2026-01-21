import logging  # noqa: D100
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Self, cast

from discord import (
    ButtonStyle,
    Color,
    Guild,
    Message,
    SelectOption,
    app_commands,
)
from discord.components import ActionRow as ActionRowOverride
from discord.components import TextDisplay as TextDisplayOverride
from discord.interactions import Interaction
from discord.ui import (
    ActionRow,
    Button,
    Container,
    Item,
    LayoutView,
    Select,
    Separator,
    TextDisplay,
    button,
)

from src.infra.db.models import (
    GuildNotificationsConfig,
    GuildTicketsConfig,
    MainGuildConfig,
    NotifyState,
)
from src.infra.db.models._enums import ChannelType, NotifyStateEnum
from src.infra.db.operations import (
    get_specified_channel,
    get_user_notify_by_end_time,
)
from src.nightcore.components.embed import (
    EntityNotFoundEmbed,
    ErrorEmbed,
    MissingPermissionsEmbed,
    SuccessMoveEmbed,
)
from src.nightcore.features.tickets.utils import (
    extract_id_from_str,
    extract_str_by_pattern,
)
from src.nightcore.utils import discord_ts, ensure_messageable_channel_exists
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)
from src.nightcore.utils.types import MessageComponentType

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


class NotifySelect(Select["PrepareNotifyViewV2"]):
    def __init__(self) -> None:
        super().__init__(
            placeholder="Выберите части профиля",
            min_values=1,
            max_values=10,
            custom_id="preparenotify:select",
            options=[
                SelectOption(label="Аватар", value="аватар"),
                SelectOption(label="Описание", value="описание"),
                SelectOption(label="Обо мне", value="обо мне"),
                SelectOption(label="Статус", value="статус"),
                SelectOption(label="Баннер", value="баннер"),
                SelectOption(label="Никнейм", value="никнейм"),
                SelectOption(label="Тег гильдии", value="тег гильдии"),
                SelectOption(label="Персональная роль", value="перс. роль"),
                SelectOption(label="Местоимение", value="местоимение"),
                SelectOption(label="Интеграции", value="интеграции"),
            ],
        )

    async def callback(self, interaction: Interaction):
        """Handles the selection of profile parts."""
        values: list[str] = interaction.data.get("values", [])  # type: ignore
        guild = cast(Guild, interaction.guild)

        view = cast("PrepareNotifyViewV2", self.view)

        await interaction.response.defer(ephemeral=True, thinking=True)

        async with view.bot.uow.start() as session:
            if not (
                notifications_channel_id := await get_specified_channel(
                    session,
                    guild_id=guild.id,
                    config_type=GuildNotificationsConfig,
                    channel_type=ChannelType.NOTIFICATIONS,
                )
            ):
                return await interaction.followup.send(
                    embed=ErrorEmbed(
                        "Ошибка отправки оповещения",
                        "Канал оповещений не настроен.",
                        view.bot.user.display_name,  # type: ignore
                        view.bot.user.display_avatar.url,  # type: ignore
                    )
                )

            if not (
                rules_channel := await get_specified_channel(
                    session,
                    guild_id=guild.id,
                    config_type=MainGuildConfig,
                    channel_type=ChannelType.RULES_CHANNEL,
                )
            ):
                return await interaction.followup.send(
                    embed=ErrorEmbed(
                        "Ошибка отправки оповещения",
                        "Канал с правилами не настроен.",
                        view.bot.user.display_name,  # type: ignore
                        view.bot.user.display_avatar.url,  # type: ignore
                    )
                )

            if not (
                create_ticket_channel_id := await get_specified_channel(
                    session,
                    guild_id=guild.id,
                    config_type=GuildTicketsConfig,
                    channel_type=ChannelType.CREATE_TICKETS,
                )
            ):
                return await interaction.followup.send(
                    embed=ErrorEmbed(
                        "Ошибка отправки оповещения",
                        "Канал создания тикетов не настроен.",
                        view.bot.user.display_name,  # type: ignore
                        view.bot.user.display_avatar.url,  # type: ignore
                    )
                )

        notifications_channel = await ensure_messageable_channel_exists(
            guild, notifications_channel_id
        )
        if not notifications_channel:
            return await interaction.followup.send(
                embed=EntityNotFoundEmbed(
                    "channel",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        nview = NotifyViewV2(
            bot=view.bot,
            guild_id=guild.id,
            user_id=view.user_id,
            moderator_id=interaction.user.id,
            rules_channel_id=rules_channel,
            create_ticket_channel_id=create_ticket_channel_id,
            content=view.content,
            profile_parts=values,
            end_time=view.end_time,
            _build=True,
        )

        try:
            message = await notifications_channel.send(view=nview)  # type: ignore
        except Exception as e:
            logger.exception(
                "[notify] Failed to send notify message in guild %s: %s",
                guild.id,
                e,
            )
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    title="Ошибка отправки сообщения",
                    description="Не удалось отправить сообщение в канал оповещений.",  # noqa: E501
                    footer_text=view.bot.user.display_name,  # type: ignore
                    footer_icon_url=view.bot.user.display_avatar.url,  # type: ignore
                )
            )

        async with view.bot.uow.start() as session:
            notifystate = NotifyState(
                guild_id=guild.id,
                user_id=view.user_id,
                moderator_id=interaction.user.id,
                message_id=message.id,  # type: ignore
                state=NotifyStateEnum.PENDING,
                end_time=view.end_time,
            )

            session.add(notifystate)

        return await interaction.followup.send(
            embed=SuccessMoveEmbed(
                title="Оповещение отправлено",
                description=(
                    f"Оповещение для пользователя <@{view.user_id}> было успешно отправлено."  # noqa: E501
                ),
                footer_text=view.bot.user.display_name,  # type: ignore
                footer_icon_url=view.bot.user.display_avatar.url,  # type: ignore
            )
        )


class NotifyActionRow(ActionRow["PrepareNotifyViewV2"]):
    def __init__(self) -> None:
        super().__init__()
        self.add_item(NotifySelect())


class PrepareNotifyViewV2(LayoutView):
    def __init__(
        self,
        bot: "Nightcore",
        user_id: int | None = None,
        end_time: datetime | None = None,
        content: str | None = None,
    ) -> None:
        super().__init__(timeout=None)

        self.bot = bot
        self.user_id = user_id
        self.end_time = end_time
        self.content = content

        container = Container[Self]()

        # header
        container.add_item(
            TextDisplay[Self]("### Выберите одно или несколько параметров")
        )

        # select
        container.add_item(NotifyActionRow())
        container.add_item(Separator[Self]())

        # footer
        now = datetime.now(UTC)

        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {self.bot.user.name} in {discord_ts(now)}\n"  # type: ignore
            )
        )

        self.add_item(container)


class NotifyButtonsActionRow(ActionRow["NotifyViewV2"]):
    def __init__(
        self,
        guild_id: int | None = None,
        create_ticket_channel_id: int | None = None,
    ) -> None:
        super().__init__()

        self.guild_id = guild_id
        self.create_ticket_channel_id = create_ticket_channel_id

        self.add_item(
            Button["NotifyViewV2"](
                style=ButtonStyle.link,
                emoji="<:29909ticket:1442924723528007700>",
                label="Задать вопрос",
                url=f"https://discord.com/channels/{self.guild_id}/{self.create_ticket_channel_id}",  # type: ignore
            )
        )

    @button(
        style=ButtonStyle.red,
        emoji="<:failed:1442915170320912506>",
        label="Отозвать оповещение",
        custom_id="notify:revoke",
    )  # type: ignore
    @check_required_permissions(PermissionsFlagEnum.MODERATION_ACCESS)  # type: ignore
    async def revoke(
        self, interaction: Interaction, button: Button["NotifyViewV2"]
    ):
        """Handles the revocation of the notification."""
        guild = cast(Guild, interaction.guild)
        view = cast("NotifyViewV2", self.view)

        message = cast(Message, interaction.message)

        view.guild_id = guild.id

        for component in message.components:
            for item in component.children:  # type: ignore
                if isinstance(item, TextDisplayOverride):
                    match item.id:
                        case 8:
                            view.end_time = datetime.fromtimestamp(
                                float(
                                    extract_str_by_pattern(
                                        item.content, r"<t:(\d+):[A-Za-z]>"
                                    )  # type: ignore
                                ),
                                tz=UTC,
                            )
                        case _:
                            ...
        async with view.bot.uow.start() as session:
            notifystate = await get_user_notify_by_end_time(
                session,
                guild_id=guild.id,
                message_id=message.id,
                ts=cast(int, cast(datetime, view.end_time).timestamp()),
            )
            if not notifystate or notifystate.state != NotifyStateEnum.PENDING:
                logger.error(
                    "[notify] No pending notify state found for user %s in guild %s",  # noqa: E501
                    view.user_id,
                    guild.id,
                )
            else:
                await session.delete(notifystate)

        await message.delete()


class NotifyViewV2(LayoutView):
    def __init__(
        self,
        bot: "Nightcore",
        guild_id: int | None = None,
        user_id: int | None = None,
        moderator_id: int | None = None,
        rules_channel_id: int | None = None,
        create_ticket_channel_id: int | None = None,
        content: str | None = None,
        profile_parts: list[str] | None = None,
        end_time: datetime | None = None,
        _build: bool = False,
    ) -> None:
        super().__init__(timeout=None)

        self.bot = bot
        self.guild_id = guild_id
        self.user_id = user_id
        self.moderator_id = moderator_id
        self.rules_channel_id = rules_channel_id
        self.content = content
        self.profile_parts = profile_parts
        self.end_time = end_time
        self.create_ticket_channel_id = create_ticket_channel_id

        self.actions: NotifyButtonsActionRow | None = None

        if _build:
            self.make_component()

    async def on_error(
        self,
        interaction: Interaction,
        error: Exception,
        item: Item[Self],
    ):
        """Handle errors for button interactions."""
        original = getattr(error, "original", error)

        if not isinstance(original, app_commands.MissingPermissions):
            return

        missing_perms: list[str] = getattr(original, "missing_permissions", [])

        _missing_perms = ", ".join(missing_perms)

        if not interaction.response.is_done():
            await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    interaction.client.user.name,  # type: ignore
                    interaction.client.user.display_avatar.url,  # type: ignore
                    f"Вам не хватает следующих прав для использования этой команды: {_missing_perms}.",  # noqa: E501
                ),
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                embed=MissingPermissionsEmbed(
                    interaction.client.user.name,  # type: ignore
                    interaction.client.user.display_avatar.url,  # type: ignore
                    f"Вам не хватает следующих прав для использования этой команды: {missing_perms}.",  # noqa: E501
                ),
                ephemeral=True,
            )

    def disable_buttons(self):
        """Disable all buttons in the view."""
        if self.actions:
            for item in self.actions.children:
                if isinstance(item, Button):
                    item.disabled = True  # type: ignore

    def rebuild_component(
        self, components: list[MessageComponentType], disabled: bool = False
    ) -> Self:
        """Rebuilds the notify view component from existing components."""

        for component in components:
            for item in component.children:  # type: ignore
                if isinstance(item, TextDisplayOverride):
                    match item.id:
                        case 2:
                            self.user_id = extract_id_from_str(
                                item.content.split(" ")[-1]
                            )
                        case 4:
                            self.moderator_id = extract_str_by_pattern(
                                item.content, r"<@!?(\d+)>"
                            )
                            self.profile_parts = extract_str_by_pattern(
                                item.content, r"\*\*`(.*?)`\*\*"
                            )
                        case 6:
                            self.rules_channel_id = extract_str_by_pattern(
                                item.content, r"<#(\d+)>"
                            )
                            self.content = extract_str_by_pattern(
                                item.content, r"\`\`\`(.+)\`\`\`"
                            )
                        case 8:
                            self.end_time = datetime.fromtimestamp(
                                float(
                                    extract_str_by_pattern(
                                        item.content, r"<t:(\d+):[A-Za-z]>"
                                    )  # type: ignore
                                ),
                                tz=UTC,
                            )
                        case _:
                            ...

                if isinstance(item, ActionRowOverride):
                    for btn in item.children:  # type: ignore
                        if btn.id == 12:
                            self.create_ticket_channel_id = btn.url[-19:-1]  # type: ignore

        view = self.make_component(disabled=disabled)

        return view

    def make_component(self, disabled: bool = False) -> Self:
        """Creates the notify view component."""
        self.clear_items()

        container = Container[Self](accent_color=Color.from_str("#ffffff"))

        # header
        container.add_item(
            TextDisplay[Self](
                f"### <:2904notifymember:1442924357524394066> | Оповещение <:42920arrowrightalt:1442924551880314921> <@{self.user_id}>"  # noqa: E501
            )
        )
        container.add_item(Separator[Self]())

        profile_parts = (
            ",".join(self.profile_parts)
            if isinstance(self.profile_parts, list)
            else self.profile_parts
        )

        container.add_item(
            TextDisplay[Self](
                f"**Модератор** <@{self.moderator_id}> обнаружил нарушение в персонализации вашего профиля Discord.\n"  # noqa: E501
                f"Пожалуйста, смените **`{profile_parts}`** в соответствии с правилами сервера.\n"  # noqa: E501
                "\n**В случае отказа или игнорирования требования — будет применено наказание.**"  # noqa: E501
            )
        )
        container.add_item(Separator[Self]())

        # body
        container.add_item(
            TextDisplay[Self](
                f"Пункт из <#{self.rules_channel_id}>: \n```{self.content}```"
            )
        )
        container.add_item(Separator[Self]())

        if self.end_time:
            container.add_item(
                TextDisplay[Self](
                    f"Оповещение истекает через: {discord_ts(self.end_time, 'R')}"  # type: ignore  # noqa: E501
                )
            )
            container.add_item(Separator[Self]())

        self.actions = NotifyButtonsActionRow(
            guild_id=self.guild_id,
            create_ticket_channel_id=self.create_ticket_channel_id,  # type: ignore
        )
        container.add_item(self.actions)
        container.add_item(Separator[Self]())

        # footer
        now = datetime.now(UTC)

        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {self.bot.user.name} in {discord_ts(now)}\n"  # type: ignore
            )
        )

        if disabled:
            self.disable_buttons()

        self.add_item(container)

        return self


class NotifyTimedOutViewV2(LayoutView):
    def __init__(
        self, bot: "Nightcore", moderator_id: int, message_url: str
    ) -> None:
        super().__init__(timeout=None)

        self.bot = bot

        container = Container[Self]()

        # header
        container.add_item(
            TextDisplay[Self](
                f"### <:8736notifyout:1442924239001878538> | Оповещение <:42920arrowrightalt:1442924551880314921> <@{moderator_id}>"  # noqa: E501
            )
        )
        container.add_item(Separator[Self]())

        # body
        container.add_item(
            TextDisplay[Self](f"Срок действия {message_url} оповещения истек.")
        )
        container.add_item(Separator[Self]())

        # footer
        now = datetime.now(UTC)

        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {self.bot.user.name} in {discord_ts(now)}\n"  # type: ignore
            )
        )

        self.add_item(container)
