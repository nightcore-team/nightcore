"""
V2 views components related to cases.

Used for displaying case opening results and help information about cases.
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Self, cast

from discord import ButtonStyle, Color, Interaction
from discord.ui import (
    ActionRow,
    Button,
    Container,
    LayoutView,
    Section,
    Separator,
    TextDisplay,
    button,
)

from src.nightcore.features.economy.utils.pages import build_case_reroll_pages

if TYPE_CHECKING:
    from src.infra.db.models.case import CaseDropAnnot
    from src.nightcore.bot import Nightcore


class CaseOpenViewV2(LayoutView):
    def __init__(
        self,
        bot: "Nightcore",
        case_name: str,
        total_weight: int,
        opened_amount: int,
        rewards: list["CaseDropAnnot"],
    ):
        super().__init__()

        self.bot = bot
        self.case_name = case_name

        container = Container[Self](accent_color=Color.from_str("#5EC9B3"))

        title_suffix = f" x{opened_amount}" if opened_amount > 1 else ""
        container.add_item(
            TextDisplay(
                f"### <:nightcoreStarUp:1540441938979983482> Открытие кейса{title_suffix}\n"  # noqa: E501
            )
        )
        # Aggregate rewards
        aggregated_rewards: dict[str, dict[str, int | float]] = {}
        processed_drop_ids: set[tuple[str, int, int]] = set()

        for r in rewards:
            name = r["name"]
            if name not in aggregated_rewards:
                aggregated_rewards[name] = {"amount": 0, "chance": 0.0}

            aggregated_rewards[name]["amount"] += r["amount"]

            drop_key = (name, r["drop_id"], r["type"])
            if drop_key not in processed_drop_ids:
                aggregated_rewards[name]["chance"] += r["chance"]
                processed_drop_ids.add(drop_key)

        lines: list[str] = []
        for name, data in aggregated_rewards.items():
            chance_str = f"**`{data['chance'] / total_weight * 100:.2f}%`**"
            if opened_amount > 1:
                lines.append(
                    f"> **{name}**: {data['amount']} шт. (Шанс: {chance_str})"
                )
            else:
                lines.append(
                    f"> **Ваш приз:** {data['amount']} {name}\n> **Шанс выпадения:** {chance_str}"  # noqa: E501
                )

        rewards_text = "\n".join(lines) + "\n"

        container.add_item(
            TextDisplay(
                f"Вы успешно открыли **{self.case_name}**\n" + rewards_text
            )
        )
        container.add_item(Separator())

        self.add_item(container)


class CaseOpenRerollPaginationActionRow(ActionRow["CaseOpenRerollViewV2"]):
    @button(
        style=ButtonStyle.secondary,
        label="Назад",
        custom_id="case:open:page:prev",
    )
    async def previous(
        self, interaction: Interaction, button: Button["CaseOpenRerollViewV2"]
    ):
        """Go to the previous rewards page."""
        view = cast(CaseOpenRerollViewV2, self.view)

        if view.current_page > 0:
            view.current_page -= 1
        await interaction.response.edit_message(
            view=view.make_component(),
        )

    @button(
        style=ButtonStyle.secondary,
        label="Далее",
        custom_id="case:open:page:next",
    )
    async def next(
        self, interaction: Interaction, button: Button["CaseOpenRerollViewV2"]
    ):
        """Go to the next rewards page."""
        view = cast(CaseOpenRerollViewV2, self.view)

        if view.current_page < len(view.pages) - 1:
            view.current_page += 1
        await interaction.response.edit_message(
            view=view.make_component(),
        )


class CaseOpenRerollViewV2(LayoutView):
    def __init__(
        self,
        bot: "Nightcore",
        *,
        session_id: int,
        case_name: str,
        pages: list[list[dict[str, Any]]],
        rerolls_left: int,
        disabled: bool = False,
    ) -> None:
        super().__init__(timeout=None)

        self.bot = bot
        self.session_id = session_id
        self.case_name = case_name
        self.pages = pages
        self.rerolls_left = rerolls_left
        self.disabled = disabled
        self.current_page = 0

        self.pagination: CaseOpenRerollPaginationActionRow | None = None

        self.make_component()

    @property
    def page_count(self) -> int:
        """Return the number of reward pages."""
        return max(1, len(self.pages))

    def _update_buttons(self):
        """Update button states based on the current page."""
        if not self.pagination:
            return
        for child in self.pagination.children:
            if isinstance(child, Button):
                if child.custom_id == "case:open:page:prev":
                    child.disabled = self.disabled or self.current_page == 0  # type: ignore
                elif child.custom_id == "case:open:page:next":
                    child.disabled = (
                        self.disabled
                        or self.current_page == len(self.pages) - 1  # type: ignore
                    )

    def make_component(self) -> Self:
        """Build the current pending rewards page."""
        self.clear_items()
        self.current_page = min(
            self.current_page,
            self.page_count - 1,
        )

        container = Container[Self](accent_color=Color.from_str("#5EC9B3"))
        container.add_item(
            TextDisplay[Self](
                f"### <:nightcoreStarUp:1540441938979983482> "
                f"Награды кейса: {self.case_name}"
            )
        )
        container.add_item(
            TextDisplay[Self](f"> Доступно рероллов: **{self.rerolls_left}**")
        )
        container.add_item(Separator[Self]())

        for reward in self.pages[self.current_page]:
            reroll_cost = 2 ** reward.get("rerolls_used", 0)
            reward_text = (
                f"**{reward['name']}**\n"
                f"> Шанс: **`{reward['chance_percent']:.2f}%`**"
            )
            container.add_item(
                Section[Self](
                    TextDisplay[Self](reward_text),
                    accessory=Button[Self](
                        label=f"Реролл ({reroll_cost})",
                        style=ButtonStyle.secondary,
                        custom_id=(
                            f"case:open:{self.session_id}:reroll:"
                            f"{reward['reward_id']}:{self.current_page}"
                        ),
                        disabled=(
                            self.disabled or self.rerolls_left < reroll_cost
                        ),
                    ),
                )
            )

        container.add_item(Separator[Self]())
        container.add_item(
            ActionRow[Self](
                Button[Self](
                    label="Забрать награды",
                    style=ButtonStyle.success,
                    custom_id=f"case:open:{self.session_id}:claim",
                    disabled=self.disabled,
                )
            )
        )

        if self.page_count > 1:
            container.add_item(Separator[Self]())
            self.pagination = CaseOpenRerollPaginationActionRow()
            container.add_item(self.pagination)

        container.add_item(Separator[Self]())
        container.add_item(
            TextDisplay[Self](
                f"-# Страница {self.current_page + 1} из {self.page_count}"
            )
        )

        self._update_buttons()

        self.add_item(container)
        return self


def build_case_reroll_view(
    bot: "Nightcore",
    *,
    session_id: int,
    case_name: str,
    total_weight: int,
    rewards: Sequence[dict[str, Any]],
    rerolls_left: int,
    disabled: bool = False,
    current_page: int = 0,
) -> CaseOpenRerollViewV2:
    """Build a pending case reroll view from prepared reward data.

    Args:
        bot: The bot instance.
        session_id: Pending case opening session id.
        case_name: Display name of the opened case.
        total_weight: Sum of the case drop chances.
        rewards: Case reward rows enriched with the ``reward_id``.
        rerolls_left: Amount of remaining rerolls for the user.
        disabled: Whether the view is in a read-only state.
        current_page: Page to display.
    """

    view = CaseOpenRerollViewV2(
        bot,
        session_id=session_id,
        case_name=case_name,
        pages=build_case_reroll_pages(rewards, total_weight),
        rerolls_left=rerolls_left,
        disabled=disabled,
    )
    view.current_page = current_page

    return view.make_component()


class CaseHelpPaginationActionRow(ActionRow["CaseHelpViewV2"]):
    def __init__(self):
        super().__init__()

        """Handle case help pagination button callback."""

    @button(
        style=ButtonStyle.secondary,
        emoji="<:nightcoreArrowLeftCyan:1540434220436951172>",
        custom_id="case:help:prev",
    )
    async def previous(
        self, interaction: Interaction, button: Button["CaseHelpViewV2"]
    ):
        """Go to the previous page."""
        view = cast(CaseHelpViewV2, self.view)

        if view.current_page > 0:
            view.current_page -= 1
        await interaction.response.edit_message(
            view=view.make_component(),
        )

    @button(
        style=ButtonStyle.secondary,
        emoji="<:nightcoreArrowRightCyan:1540434390780477551>",
        custom_id="case:help:next",
    )
    async def next(
        self, interaction: Interaction, button: Button["CaseHelpViewV2"]
    ):
        """Go to the next page."""
        view = cast(CaseHelpViewV2, self.view)
        if view.current_page < len(view.pages) - 1:  # type: ignore
            view.current_page += 1  # type: ignore
        await interaction.response.edit_message(
            view=view.make_component(),  # type: ignore
        )


class CaseHelpViewV2(LayoutView):
    def __init__(self, bot: "Nightcore", pages: list[list[TextDisplay[Any]]]):
        super().__init__(timeout=None)

        self.pages = pages
        self.current_page = 0
        self.bot = bot

        self.pagination: CaseHelpPaginationActionRow | None = None

        self.make_component()

    def _update_buttons(self):
        """Update button states based on current page."""
        if not self.pagination:
            return
        for child in self.pagination.children:
            if isinstance(child, Button):
                if child.custom_id == "case:help:prev":
                    child.disabled = self.current_page == 0  # type: ignore
                elif child.custom_id == "case:help:next":
                    child.disabled = self.current_page == len(self.pages) - 1  # type: ignore

    def make_component(self) -> Self:
        """Create a new component for the current page."""

        self.clear_items()

        container = Container[Self](accent_color=Color.from_str("#5EC9B3"))

        container.add_item(
            TextDisplay(
                "## <:nightcoreCase:1540678039841673216> Информация о кейсах"
            )
        )
        container.add_item(Separator())
        container.add_item(
            TextDisplay(
                "**Доступные виды кейсов.**\n"
                "> Чтобы открыть кейс, используйте команду **`/case open`**"
            )
        )
        container.add_item(Separator())

        if len(self.pages) > 1:
            for item in self.pages[self.current_page]:
                container.add_item(item)

            container.add_item(Separator[Self]())

            self.pagination = CaseHelpPaginationActionRow()
            container.add_item(self.pagination)
        else:
            for item in self.pages[0]:
                container.add_item(item)

        container.add_item(Separator())

        container.add_item(
            TextDisplay[Self](
                f"-# Page {self.current_page + 1} of {len(self.pages)}"
            )
        )

        self._update_buttons()

        self.add_item(container)

        return self
