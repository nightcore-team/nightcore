"""Command to get specified clause of the rules."""

from discord import Interaction, app_commands

from src.nightcore.bot import Nightcore
from src.nightcore.features.meta.components.v2.view.rules_get import (
    RulesGetViewV2,
)
from src.nightcore.features.moderation.utils.transformers.string_to_rule import (  # noqa: E501
    StringToRuleTransformer,
)
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

from ._groups import rules as rules_group


@rules_group.command(name="get", description="Получить пункт правила")  # type: ignore
@app_commands.describe(
    clause="Номер пункта (например, '1' для главы, '1.1' для правила, '1.1.1' для подпункта)"  # noqa: E501
)
@check_required_permissions(PermissionsFlagEnum.MODERATION_ACCESS)
async def get_rules(
    interaction: Interaction["Nightcore"],
    clause: app_commands.Transform[
        app_commands.Range[str, 1, 1000], StringToRuleTransformer
    ],
):
    """Retrieves and displays a specific rule clause via an interactive view."""  # noqa: E501

    view = RulesGetViewV2(bot=interaction.client, clause=clause)

    await interaction.response.send_message(view=view, ephemeral=True)
