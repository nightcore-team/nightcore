"""View for sending role requests."""

from typing import TYPE_CHECKING, Self

from discord import ButtonStyle, Color, SelectOption
from discord.ui import (
    ActionRow,
    Button,
    Container,
    LayoutView,
    Select,
    Separator,
    TextDisplay,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


class SelectOrgRoleActionRow(ActionRow["SendRoleRequestView"]):
    def __init__(self, org_options: list[SelectOption]) -> None:
        super().__init__()

        org_select = Select["SendRoleRequestView"](
            placeholder="Выберите нужную роль.",
            min_values=1,
            max_values=1,
            custom_id="role_request:select_org_role",
            options=org_options,
        )
        self.add_item(org_select)


class SelectIllRoleActionRow(ActionRow["SendRoleRequestView"]):
    def __init__(self, ill_options: list[SelectOption]) -> None:
        super().__init__()

        ill_select = Select["SendRoleRequestView"](
            placeholder="Выберите вашу нелегальную организацию.",
            min_values=1,
            max_values=1,
            custom_id="role_request:select_ill_role",
            options=ill_options,
        )
        self.add_item(ill_select)


class OtherRoleRequestButtons(ActionRow["SendRoleRequestView"]):
    def __init__(self) -> None:
        super().__init__()

        self.add_item(
            Button["SendRoleRequestView"](
                label="Отменить текущий запрос",
                custom_id="role_request:cancel",
                style=ButtonStyle.grey,
                emoji="<:nightcoreDeclineBlue:1540815862288752883>",
            )
        )

        self.add_item(
            Button["SendRoleRequestView"](
                label="Снять запрашиваемые роли",
                custom_id="role_request:remove_roles",
                style=ButtonStyle.grey,
                emoji="<:nightcoreOrgRole:1540815640951136347>",
            )
        )


class SendRoleRequestView(LayoutView):
    def __init__(
        self,
        bot: "Nightcore",
        org_options: list[SelectOption] | None = None,
        ill_options: list[SelectOption] | None = None,
    ) -> None:
        super().__init__(timeout=None)
        self.bot = bot

        container = Container[Self](accent_color=Color.from_str("#5DADE2"))

        # header
        container.add_item(
            TextDisplay[Self](
                "## <:nightcoreRoleRequest:1540815323488460810> Отправить запрос на роль"  # noqa: E501
            )
        )
        container.add_item(Separator[Self]())

        # main text
        container.add_item(
            TextDisplay[Self](
                "**Для запроса роли, пожалуйста, выберите нужную роль...**\n"
                "**...из списка ниже.**"
            )
        )

        # select
        if org_options:
            container.add_item(
                SelectOrgRoleActionRow(
                    org_options=org_options,
                )
            )
        if ill_options:
            container.add_item(
                SelectIllRoleActionRow(
                    ill_options=ill_options,
                )
            )
        container.add_item(Separator[Self]())

        # other buttons
        container.add_item(OtherRoleRequestButtons())
        container.add_item(Separator[Self]())

        self.add_item(container)
