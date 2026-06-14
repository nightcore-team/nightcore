"""Pydantic schemas for guild configurations."""

from typing import Annotated, Any

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    PlainSerializer,
    computed_field,
)

from src.nightcore.api.utils.validators import (
    validate_category_id,
    validate_role_id,
    validate_role_no_adm_id,
    validate_text_channel_id,
    validate_voice_channel_id,
)
from src.utils._enums import (
    ConfigMuteTypeEnum,
    ConfigTypeEnum,
    MessageCountTypeEnum,
)


def _parse_snowflake(v: Any) -> int:
    return int(v)


def _serialize_snowflake(v: int) -> str:
    return str(v)


SnowflakeValidator = BeforeValidator(_parse_snowflake)
SnowflakeSerializer = PlainSerializer(
    _serialize_snowflake, return_type=str, when_used="json"
)

DiscordRoleID = Annotated[
    int,
    SnowflakeValidator,
    SnowflakeSerializer,
    AfterValidator(validate_role_id),
]
DiscordRoleNoAdmID = Annotated[
    int,
    SnowflakeValidator,
    SnowflakeSerializer,
    AfterValidator(validate_role_no_adm_id),
]
DiscordTextChannelID = Annotated[
    int,
    SnowflakeValidator,
    SnowflakeSerializer,
    AfterValidator(validate_text_channel_id),
]
DiscordCategoryID = Annotated[
    int,
    SnowflakeValidator,
    SnowflakeSerializer,
    AfterValidator(validate_category_id),
]
DiscordVoiceChannelID = Annotated[
    int,
    SnowflakeValidator,
    SnowflakeSerializer,
    AfterValidator(validate_voice_channel_id),
]

DiscordRoleIDList = Annotated[list[DiscordRoleID], Field(max_length=250)]
DiscordChannelIDList = Annotated[
    list[DiscordTextChannelID], Field(max_length=500)
]
DiscordCategoryIDList = Annotated[
    list[DiscordCategoryID], Field(max_length=50)
]
AutocompleteableString = Annotated[str, Field(max_length=100)]
SelectMenuLabelString = Annotated[str, Field(max_length=100)]
NickNameTagString = Annotated[str, Field(max_length=7)]
TitleString = Annotated[str, Field(max_length=256)]
EmbedDescriptionString = Annotated[str, Field(max_length=4096)]


class BaseGuildConfig(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        extra="ignore",
    )


class GuildOrgRoleSchema(BaseGuildConfig):
    role_id: DiscordRoleNoAdmID
    tag: NickNameTagString
    name: SelectMenuLabelString


class GuildOrgRolesConfigSchema(BaseGuildConfig):
    illegal_roles: list[GuildOrgRoleSchema] | None = Field(
        max_length=25, default=None
    )
    organizational_roles: list[GuildOrgRoleSchema] | None = Field(
        max_length=25, default=None
    )
    check_role_requests_channel_id: DiscordTextChannelID | None = None


class GuildSubRuleSchema(BaseGuildConfig):
    text: EmbedDescriptionString


class GuildRuleSchema(BaseGuildConfig):
    text: EmbedDescriptionString
    subrules: list[GuildSubRuleSchema]


class RulesChapterSchema(BaseGuildConfig):
    text: TitleString
    rules: list[GuildRuleSchema]


class GuildRulesSchema(BaseGuildConfig):
    chapters: list[RulesChapterSchema]


class GuildRulesConfigSchema(BaseGuildConfig):
    guild_rules: GuildRulesSchema | None = None
    rules_channel_id: DiscordTextChannelID | None = None


class GuildProposalConfigSchema(BaseGuildConfig):
    create_proposal_channel_id: DiscordTextChannelID | None = None


class GuildLoggingConfigSchema(BaseGuildConfig):
    bans_log_channel_id: DiscordTextChannelID | None = None
    clans_log_channel_id: DiscordTextChannelID | None = None
    members_log_channel_id: DiscordTextChannelID | None = None
    messages_log_channel_id: DiscordTextChannelID | None = None
    voices_log_channel_id: DiscordTextChannelID | None = None
    moderation_log_channel_id: DiscordTextChannelID | None = None
    tickets_log_channel_id: DiscordTextChannelID | None = None
    roles_log_channel_id: DiscordTextChannelID | None = None
    channels_log_channel_id: DiscordTextChannelID | None = None
    reactions_log_channel_id: DiscordTextChannelID | None = None
    private_rooms_log_channel_id: DiscordTextChannelID | None = None
    economy_log_channel_id: DiscordTextChannelID | None = None
    message_log_ignoring_channels_ids: DiscordChannelIDList | None = None


class GuildEconomyShopItemSchema(BaseGuildConfig):
    name: SelectMenuLabelString
    cost: int


class GuildEconomyConfigSchema(BaseGuildConfig):
    coin_name: str | None = Field(max_length=20, default=None)
    economy_access_roles_ids: DiscordRoleIDList | None = None
    reward_bonus: int = 0
    economy_shop_buy_ping_roles_ids: DiscordRoleIDList | None = None
    economy_shop_items: list[GuildEconomyShopItemSchema] | None = Field(
        max_length=25, default=None
    )
    casino_multiplayer_channel_id: DiscordTextChannelID | None = None
    color_drop_compensation: int = 0


class GuildLevelRoleSchema(BaseGuildConfig):
    level: int
    role_id: DiscordRoleNoAdmID


class GuildBonusRoleSchema(BaseGuildConfig):
    role_id: DiscordRoleID
    coins: int


class GuildLevelsConfigSchema(BaseGuildConfig):
    count_messages_channel_id: DiscordTextChannelID | None = None
    level_notify_channel_id: DiscordTextChannelID | None = None
    bonus_access_roles_ids: list[GuildBonusRoleSchema] | None = None
    level_roles: list[GuildLevelRoleSchema] | None = None
    count_messages_type: MessageCountTypeEnum | None = None


class GuildMultiplersConfigSchema(BaseGuildConfig):
    base_exp_multiplier: int = 1
    temp_exp_multiplier: int | None = None
    base_coins_multiplier: int = 1
    temp_coins_multiplier: float | None = None
    base_battlepass_multiplier: int = 1
    temp_battlepass_multiplier: int | None = None


class GuildClanShopItemSchema(BaseGuildConfig):
    name: SelectMenuLabelString
    cost: int


class GuildClansConfigSchema(BaseGuildConfig):
    create_clan_channel_category_id: DiscordCategoryID | None = None
    clan_payday_channel_id: DiscordTextChannelID | None = None
    clan_shop_channel_id: DiscordTextChannelID | None = None
    clan_shop_items: list[GuildClanShopItemSchema] | None = None
    clans_access_roles_ids: DiscordRoleIDList | None = None
    clan_buy_ping_roles_ids: DiscordRoleIDList | None = None
    clan_reputation_per_payday: int = 1
    base_exp_multiplier: int = 1
    clan_improvements: list[int] | None = Field(
        max_length=3, min_length=3, default=None
    )


class GuildPrivateChannelsConfigSchema(BaseGuildConfig):
    private_rooms_create_channel_id: DiscordVoiceChannelID | None = None


class GuildFractionRoleSchema(BaseGuildConfig):
    access_roles: DiscordRoleIDList | None = None
    role_id: DiscordRoleNoAdmID


class GuildModerationConfigSchema(BaseGuildConfig):
    moderation_access_roles_ids: DiscordRoleIDList | None = None
    leadership_access_roles_ids: DiscordRoleIDList | None = None
    count_moderator_messages_channel_id: DiscordTextChannelID | None = None
    ban_access_roles_ids: DiscordRoleIDList | None = None
    unban_access_roles_ids: DiscordRoleIDList | None = None
    mute_score: float | None = 0.0
    ban_score: float | None = 0.0
    kick_score: float | None = 0.0
    ticket_score: float | None = 0.0
    role_request_score: float | None = 0.0
    role_remove_score: float | None = 0.0
    ticket_ban_score: float | None = 0.0
    mpmute_score: float | None = 0.0
    vmute_score: float | None = 0.0
    message_score: float | None = 0.0
    notification_score: float | None = 0.0
    trackable_moderation_role_id: DiscordRoleID | None = None
    ban_request_ping_role_id: DiscordRoleID | None = None
    send_ban_request_channel_id: DiscordTextChannelID | None = None
    mpmute_role_id: DiscordRoleID | None = None
    vmute_role_id: DiscordRoleID | None = None
    mute_role_id: DiscordRoleID | None = None
    mute_type: ConfigMuteTypeEnum | None = None
    fraction_roles_access_roles_ids: list[GuildFractionRoleSchema] | None = (
        Field(max_length=25, default=None)
    )
    leader_access_rr_roles_ids: DiscordRoleIDList | None = None
    inactive_channel_id: DiscordTextChannelID | None = None


class GuildNotificationsConfigSchema(BaseGuildConfig):
    notifications_channel_id: DiscordTextChannelID | None = None
    notifications_for_moderation_channel_id: DiscordTextChannelID | None = None
    notifications_from_bot_channel_id: DiscordTextChannelID | None = None


class GuildTicketsConfigSchema(BaseGuildConfig):
    tickets_count: int = 0
    new_tickets_category_id: DiscordCategoryID | None = None
    closed_tickets_category_id: DiscordCategoryID | None = None
    create_ticket_channel_id: DiscordTextChannelID | None = None
    pinned_tickets_category_id: DiscordCategoryID | None = None
    create_ticket_ping_role_id: DiscordRoleID | None = None


class GuildInfomakerConfigSchema(BaseGuildConfig):
    admins_roles_ids: DiscordRoleIDList | None = None
    leaders_roles_ids: DiscordRoleIDList | None = None
    admins_roles_logging_channel_id: DiscordTextChannelID | None = None
    leaders_roles_logging_channel_id: DiscordTextChannelID | None = None


class GuildForumConfigSchema(BaseGuildConfig):
    is_enabled: bool = False
    role_id: int | None = None
    channel_id: int | None = None
    section_id: int | None = Field(exclude=True, default=None)

    @computed_field
    @property
    def available(self) -> bool:  # noqa: D102
        return self.section_id is not None


class GuildAccessConfigSchema(BaseGuildConfig):
    forum_config_access_roles_ids: DiscordRoleIDList | None = None
    org_roles_config_access_roles_ids: DiscordRoleIDList | None = None
    proposal_config_access_roles_ids: DiscordRoleIDList | None = None
    rules_config_access_roles_ids: DiscordRoleIDList | None = None
    multiplers_config_access_roles_ids: DiscordRoleIDList | None = None
    logging_config_access_roles_ids: DiscordRoleIDList | None = None
    economy_config_access_roles_ids: DiscordRoleIDList | None = None
    levels_config_access_roles_ids: DiscordRoleIDList | None = None
    clans_config_access_roles_ids: DiscordRoleIDList | None = None
    private_channels_config_access_roles_ids: DiscordRoleIDList | None = None
    moderation_config_access_roles_ids: DiscordRoleIDList | None = None
    notifications_config_access_roles_ids: DiscordRoleIDList | None = None
    tickets_config_access_roles_ids: DiscordRoleIDList | None = None
    infomaker_config_access_roles_ids: DiscordRoleIDList | None = None


CONFIG_SCHEMA_MODEL_MAP = {
    ConfigTypeEnum.PRIVATE_CHANNELS: GuildPrivateChannelsConfigSchema,
    ConfigTypeEnum.MODERATION: GuildModerationConfigSchema,
    ConfigTypeEnum.NOTIFICATIONS: GuildNotificationsConfigSchema,
    ConfigTypeEnum.TICKETS: GuildTicketsConfigSchema,
    ConfigTypeEnum.INFOMAKER: GuildInfomakerConfigSchema,
    ConfigTypeEnum.FORUM: GuildForumConfigSchema,
    ConfigTypeEnum.ACCESS: GuildAccessConfigSchema,
    ConfigTypeEnum.ECONOMY: GuildEconomyConfigSchema,
    ConfigTypeEnum.LEVELS: GuildLevelsConfigSchema,
    ConfigTypeEnum.CLANS: GuildClansConfigSchema,
    ConfigTypeEnum.MULTIPLERS: GuildMultiplersConfigSchema,
    ConfigTypeEnum.RULES: GuildRulesConfigSchema,
    ConfigTypeEnum.PROPOSALS: GuildProposalConfigSchema,
    ConfigTypeEnum.ROLE_REQUEST: GuildOrgRolesConfigSchema,
    ConfigTypeEnum.LOGGING: GuildLoggingConfigSchema,
}


class ConfigUpdateBody(BaseModel):
    config_type: ConfigTypeEnum
    data: dict[str, Any]
