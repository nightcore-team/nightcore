"""Command to notify a user about a rule violation."""

import logging
from typing import TYPE_CHECKING, Any, cast

from discord import Guild, Member, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.infra.db.models._annot import Chapter
from src.infra.db.operations import (
    get_guild_rules,
    get_moderation_access_roles,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.components.embed import (
    EntityNotFoundEmbed,
    MissingPermissionsEmbed,
    ValidationErrorEmbed,
)
from src.nightcore.exceptions import FieldNotConfiguredError
from src.nightcore.features.meta.utils import convert_dict_to_rules
from src.nightcore.features.moderation.components.v2 import PrepareNotifyViewV2
from src.nightcore.features.moderation.utils import (
    find_rule_by_index,
)
from src.nightcore.utils import (
    ensure_member_exists,
    has_any_role_from_sequence,
)
from src.nightcore.utils.time_utils import calculate_end_time, parse_duration

logger = logging.getLogger(__name__)


class Notify(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

    @app_commands.command(
        name="notify", description="Отправить оповещение пользователю"
    )
    @app_commands.describe(
        user="Пользователь для оповещения",
        duration="Длительность оповещения",
        reason="Причина оповещения (номер правила или текст)",
    )
    async def notify(
        self,
        interaction: Interaction["Nightcore"],
        user: Member,
        duration: str,
        reason: str,
    ):
        """Sends a notification to a user."""

        guild = cast(Guild, interaction.guild)

        member = await ensure_member_exists(guild, user.id)

        if member is None:
            return await interaction.response.send_message(
                embed=EntityNotFoundEmbed(
                    "пользователь",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        async with self.bot.uow.start() as session:
            if not (
                moderation_access_roles := await get_moderation_access_roles(
                    session, guild_id=guild.id
                )
            ):
                raise FieldNotConfiguredError("доступ к модерации")

            if not (
                rules_data := cast(
                    dict[str, Any],
                    await get_guild_rules(session, guild_id=guild.id),
                )
            ):
                raise FieldNotConfiguredError("правила")

        has_moder_role = has_any_role_from_sequence(
            cast(Member, interaction.user), moderation_access_roles
        )
        if not has_moder_role:
            return await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        rules = convert_dict_to_rules(rules_data)

        rule, index = find_rule_by_index(rules, reason)  # type: ignore
        if isinstance(rule, Chapter):
            return await interaction.response.send_message(
                embed=ValidationErrorEmbed(
                    "Пожалуйста, укажите действительный номер правила, а не главы.",  # noqa: E501
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        parsed_duration = parse_duration(duration)

        if not parsed_duration:
            return await interaction.response.send_message(
                embed=ValidationErrorEmbed(
                    "Неверная продолжительность. Используйте s/m/h/d (например, 1h, 1d, 7d).",  # noqa: E501
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        end_time = calculate_end_time(parsed_duration)

        await interaction.response.send_message(
            view=PrepareNotifyViewV2(
                bot=self.bot,
                user_id=member.id,
                end_time=end_time,
                content=f"{index}. {rule.text}"  # type: ignore
                if index and rule.text  # type: ignore
                else reason,
            ),
            ephemeral=True,
        )


async def setup(bot: "Nightcore") -> None:
    """Setup the Notify cog."""
    await bot.add_cog(Notify(bot))
