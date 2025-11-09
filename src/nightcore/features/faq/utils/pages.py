"""Utility function to build FAQ pages corrent components."""

from __future__ import annotations

from discord import ButtonStyle
from discord.ui import (
    Button,
    Item,
    LayoutView,
    Section,
    Separator,
    TextDisplay,
)

from src.infra.db.models._annot import FAQPageAnnot


def build_faq_page_components(
    pages: list[FAQPageAnnot],
    items_per_page: int = 5,  # ✅ 5 FAQ items на сторінку
) -> list[list[Item[LayoutView]]]:
    """Build FAQ page components for the FAQ overview.

    Args:
        pages: List of FAQ pages from database
        items_per_page: How many FAQ items per page (default: 5)

    Returns:
        List of pages, each page is a list of components
    """

    result: list[list[Item[LayoutView]]] = []
    current_page: list[Item[LayoutView]] = []
    items_count = 0

    for page in pages:
        if items_count >= items_per_page:
            result.append(current_page)
            current_page = []
            items_count = 0

        current_page.append(TextDisplay[LayoutView](f"### {page['title']}"))
        current_page.append(
            Section[LayoutView](
                TextDisplay[LayoutView](f"> {page['description']}"),
                accessory=Button[LayoutView](
                    label="Подробнее",
                    style=ButtonStyle.secondary,
                    custom_id=f"faq_page:{page['title']}",
                ),
            )
        )
        current_page.append(Separator[LayoutView]())

        items_count += 1

    if current_page:
        result.append(current_page)

    return result if result else [[]]
