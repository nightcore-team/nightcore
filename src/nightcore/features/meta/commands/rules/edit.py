"""Command to edit chapters or rules."""

import json
import logging
from typing import cast

from discord import Guild, Interaction, app_commands

from src.config.config import config
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


@rules_group.command(name="edit", description="Изменить главу или правило")  # type: ignore
@app_commands.describe(
    clause="Номер пункта (например, '1' для главы, '1.1' для правила, '1.1.1' для подпункта)",  # noqa: E501
    text="Новый текст главы или правила",
)
@check_required_permissions(PermissionsFlagEnum.ADMINISTRATOR)
async def edit_chapter_or_rule(
    interaction: Interaction["Nightcore"],
    clause: str,
    text: str,
):
    """Edit a chapter or rule."""
    bot = interaction.client

    indexes = parse_clause(clause)
    if not indexes:
        await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка изменения главы или правила",
                "Неверный ввод пункта правил или главы",
                bot.user.display_name,  # type: ignore
                bot.user.avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )
        return

    guild = cast(Guild, interaction.guild)

    async with specified_guild_config(
        bot=bot, guild_id=guild.id, config_type=MainGuildConfig, _create=True
    ) as (guild_config, _):
        rules_data = cast(
            dict[str, object], guild_config.guild_rules or {"chapters": []}
        )

        # json -> dataclass
        rules = convert_dict_to_rules(rules_data)

        message = ""

        try:
            # 1 level: change chapter title
            if len(indexes) == 1:
                ch_index = indexes[0] - 1
                if ch_index >= len(rules.chapters):
                    raise IndexError("Указанной главы не существует")
                if len(text) > 256:
                    raise ValueError(
                        "Название главы не может быть длиннее 256 символов"
                    )
                rules.chapters[ch_index].title = text
                message = "Название главы изменено"

            # 2 level: change rule text
            elif len(indexes) == 2:
                ch_index, rule_index = indexes[0] - 1, indexes[1] - 1
                if ch_index >= len(rules.chapters):
                    raise IndexError("Указанной главы не существует")
                r = rules.chapters[ch_index].rules
                if rule_index >= len(r):
                    raise IndexError("Указанного правила не существует")
                if len(text) > config.bot.EMBED_DESCRIPTION_LIMIT:
                    raise ValueError(
                        f"Текст правила не может быть длиннее {config.bot.EMBED_DESCRIPTION_LIMIT} символов"  # noqa: E501
                    )
                r[rule_index].text = text
                message = "Правило изменено"

            # 3 level: change subrule text
            elif len(indexes) == 3:
                ch_index, rule_index, sub_index = [i - 1 for i in indexes]
                if ch_index >= len(rules.chapters):
                    raise IndexError("Указанной главы не существует")
                r = rules.chapters[ch_index].rules
                if rule_index >= len(r):
                    raise IndexError("Указанного правила не существует")
                subrules = r[rule_index].subrules
                if sub_index >= len(subrules):
                    raise IndexError("Указанного подпункта не существует")
                if len(text) > config.bot.EMBED_DESCRIPTION_LIMIT:
                    raise ValueError(
                        f"Текст подпункта не может быть длиннее {config.bot.EMBED_DESCRIPTION_LIMIT} символов"  # noqa: E501
                    )
                subrules[sub_index].text = text
                message = "Подпункт изменен"

            else:
                raise ValueError(
                    "Поддерживаются только до 3 уровней вложенности"
                )

            guild_config.guild_rules = json.loads(
                json.dumps(rules, default=lambda o: o.__dict__)
            )

        except (IndexError, ValueError) as e:
            await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка изменения главы или правила",
                    str(e),
                    bot.user.display_name,  # type: ignore
                    bot.user.avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )
            return

    await interaction.response.send_message(
        embed=SuccessMoveEmbed(
            "Изменение правил",
            message,
            bot.user.display_name,  # type: ignore
            bot.user.avatar.url,  # type: ignore
        ),
        ephemeral=False,
    )

    logger.info(
        "[command] - invoked user=%s guild=%s clause=%s text=%s",
        interaction.user.id,
        guild.id,
        clause,
        text,
    )
