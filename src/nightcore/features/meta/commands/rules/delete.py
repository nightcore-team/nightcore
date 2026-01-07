"""Command to delete chapters or rules."""

import json
import logging
from typing import Any, cast

from discord import Guild, Interaction, app_commands

from src.infra.db.models import MainGuildConfig
from src.nightcore.bot import Nightcore
from src.nightcore.components.embed import ErrorEmbed, SuccessMoveEmbed
from src.nightcore.features.meta.utils import (
    convert_dict_to_rules,
    parse_clause,
)
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

from ._groups import rules as rules_group

logger = logging.getLogger(__name__)


@rules_group.command(name="delete", description="Удалить главу или правило")  # type: ignore
@app_commands.describe(
    clause="Номер пункта (например, '1' для главы, '1.1' для правила, '1.1.1' для подпункта)",  # noqa: E501
)
@check_required_permissions(PermissionsFlagEnum.HEAD_MODERATION_ACCESS)
async def delete_chapter_or_rule(
    interaction: Interaction["Nightcore"],
    clause: str,
):
    """Delete a chapter or rule."""
    bot = interaction.client
    guild = cast(Guild, interaction.guild)

    async with specified_guild_config(
        bot=bot, guild_id=guild.id, config_type=MainGuildConfig, _create=True
    ) as (guild_config, _):
        rules_data = cast(
            dict[str, Any], guild_config.guild_rules or {"chapters": []}
        )

        # json -> dataclass
        rules = convert_dict_to_rules(rules_data)

        # parse clause
        indexes = parse_clause(clause)
        if not indexes:
            await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка удаления главы или правила",
                    "Неверный ввод пункта правил или главы",
                    bot.user.display_name,  # type: ignore
                    bot.user.avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )
            return

        # delete chapter/rule/subrule
        try:
            if len(indexes) == 1:
                # delete chapter
                ch_index = indexes[0] - 1
                if ch_index >= len(rules.chapters):
                    await interaction.response.send_message(
                        embed=ErrorEmbed(
                            "Ошибка удаления главы",
                            "Указанной главы не существует",
                            bot.user.display_name,  # type: ignore
                            bot.user.avatar.url,  # type: ignore
                        ),
                        ephemeral=True,
                    )
                    return

                del rules.chapters[ch_index]
                message = "Глава успешно удалена!"

            elif len(indexes) == 2:
                # delete rule in chapter
                ch_index = indexes[0] - 1
                rule_index = indexes[1] - 1

                if ch_index >= len(rules.chapters):
                    await interaction.response.send_message(
                        embed=ErrorEmbed(
                            "Ошибка удаления главы",
                            "Указанной главы не существует",
                            bot.user.display_name,  # type: ignore
                            bot.user.avatar.url,  # type: ignore
                        ),
                        ephemeral=True,
                    )
                    return
                if rule_index >= len(rules.chapters[ch_index].rules):
                    await interaction.response.send_message(
                        embed=ErrorEmbed(
                            "Ошибка удаления правила",
                            "Указанного правила не существует",
                            bot.user.display_name,  # type: ignore
                            bot.user.avatar.url,  # type: ignore
                        ),
                        ephemeral=True,
                    )
                    return

                del rules.chapters[ch_index].rules[rule_index]
                message = "Правило успешно удалено!"

            elif len(indexes) == 3:
                # delete subrule in rule
                ch_index = indexes[0] - 1
                rule_index = indexes[1] - 1
                subrule_index = indexes[2] - 1

                if ch_index >= len(rules.chapters):
                    await interaction.response.send_message(
                        embed=ErrorEmbed(
                            "Ошибка удаления главы",
                            "Указанной главы не существует",
                            bot.user.display_name,  # type: ignore
                            bot.user.avatar.url,  # type: ignore
                        ),
                        ephemeral=True,
                    )
                    return
                if rule_index >= len(rules.chapters[ch_index].rules):
                    await interaction.response.send_message(
                        embed=ErrorEmbed(
                            "Ошибка удаления правила",
                            "Указанного правила не существует",
                            bot.user.display_name,  # type: ignore
                            bot.user.avatar.url,  # type: ignore
                        ),
                        ephemeral=True,
                    )
                    return
                if subrule_index >= len(
                    rules.chapters[ch_index].rules[rule_index].subrules
                ):
                    await interaction.response.send_message(
                        embed=ErrorEmbed(
                            "Ошибка удаления подправила",
                            "Указанного подправила не существует",
                            bot.user.display_name,  # type: ignore
                            bot.user.avatar.url,  # type: ignore
                        ),
                        ephemeral=True,
                    )
                    return

                del (
                    rules.chapters[ch_index]
                    .rules[rule_index]
                    .subrules[subrule_index]
                )
                message = "Подправило успешно удалено!"

            else:
                await interaction.response.send_message(
                    embed=ErrorEmbed(
                        "Ошибка удаления подправила",
                        "Глубже третьего уровня нельзя удалять!",
                        bot.user.display_name,  # type: ignore
                        bot.user.avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )
                return

        except Exception:
            await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка при удалении",
                    "Произошла ошибка при удалении",
                    bot.user.display_name,  # type: ignore
                    bot.user.avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )
            return

        # renumerate all rules
        for i, chapter in enumerate(rules.chapters, start=1):
            chapter.number = i
            for j, rule in enumerate(chapter.rules, start=1):
                rule.number = f"{i}.{j}"
                for k, subrule in enumerate(rule.subrules, start=1):
                    subrule.number = f"{i}.{j}.{k}"

        guild_config.guild_rules = json.loads(
            json.dumps(rules, default=lambda o: o.__dict__)
        )

    await interaction.response.send_message(
        embed=SuccessMoveEmbed(
            "Удаление главы или правила",
            message
            + "\n\nНе забудьте заново опубликовать правила командой /rules send",  # noqa: E501
            bot.user.display_name,  # type: ignore
            bot.user.avatar.url,  # type: ignore
        ),
        ephemeral=True,
    )

    logger.info(
        "[command] - invoked user=%s guild=%s clause=%s",
        interaction.user.id,
        guild.id,
        clause,
    )
