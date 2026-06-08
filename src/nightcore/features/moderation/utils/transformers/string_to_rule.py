"""Transform string to rule text."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from discord import AppCommandOptionType, Guild
from discord.app_commands import Transformer
from discord.interactions import Interaction

from src.infra.db.models.configurations.rules import GuildRulesChapter
from src.infra.db.operations import get_guild_rules

from ..parse_rules import find_rule_by_index, parse_clause

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


class StringToRuleTransformer(Transformer["Nightcore"]):
    """Transform string to rule text."""

    @property
    def type(self) -> AppCommandOptionType:
        """Get the type of the transformer."""
        return AppCommandOptionType.string

    async def transform(
        self,
        interaction: Interaction[Nightcore],
        value: str,
    ) -> str | None:
        """
        Transform string to rule text or return passed value.

        Args:
            interaction (Interaction[Nightcore]): The interaction object.
            value (str): The string value to transform.

        Returns:
            str: The transformed rule text or the original value.
        """

        guild = cast(Guild, interaction.guild)
        bot = interaction.client

        if not parse_clause(value):
            return value

        async with bot.uow.start(readonly=True) as session:
            rules = await get_guild_rules(session, guild_id=guild.id)
            session.expunge_all()

        rule, index = find_rule_by_index(rules, value)  # type: ignore

        if isinstance(rule, GuildRulesChapter):
            return value

        if rule and index:
            return f"{index}. {rule.text}"

        return value
