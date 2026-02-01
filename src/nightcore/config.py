"""Defines the Config class for bot environment settings."""

from src.config.env import BaseEnvConfig


class Config(BaseEnvConfig):
    BOT_TOKEN: str
    EMBED_DESCRIPTION_LIMIT: int = 4096
    VIEW_V2_DESCRIPTION_LIMIT: int = 3000
    VIEW_V2_COMPONENTS_LIMIT: int = 40
    DELETE_MESSAGES_SECONDS: int = 604800
    VOTEBAN_ATTACHMENTS_LIMIT: int = 7
    CLOSED_TICKET_ALIVE_HOURS: int = 48
    ROLE_REQUESTS_ALIVE_HOURS: int = 2
    CASE_REWARDS_LIMIT: int = 30
    MAX_CUSTOM_REWARD_SIZE: int = 100
    BUG_REPORT_CHANNEL_ID: int = 1442803332233171088
    DISABLE_FORUM_TASK: bool = False
    DEVELOPER_IDS: list[int] = [  # noqa: RUF012
        1280700292530176131,
        566255833684508672,
        451359852418039808,
    ]
