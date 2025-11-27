"""Forum API configuration."""

from typing import Final

from src.config.env import BaseEnvConfig
from src.infra.api.forum.dto import Server

# SERVERS: Final[list[Server]] = [
#     Server(
#         section_id=538,
#         guild_id=952303456222318693,
#         channel_id=1428784779842683123,
#         role_id=1406731851577430108,
#     ),
#     Server(
#         section_id=714,
#         guild_id=347728316557426688,
#         channel_id=1401322529607516290,
#         role_id=1401220493385924638,
#     ),
#     Server(
#         section_id=592,
#         guild_id=1036712610919370834,
#         channel_id=1351882503929073777,
#         role_id=1298730558012264448,
#     ),
# ]


class Config(BaseEnvConfig):
    FORUM_API_URL: str
    FORUM_API_KEY: str

    SERVERS: Final[list[Server]] = [
        Server(
            section_id=538,
            guild_id=952303456222318693,
            channel_id=1329005115377717258,
            role_id=1259548132853944473,
        ),
        Server(
            section_id=714,
            guild_id=347728316557426688,
            channel_id=1401322529607516290,
            role_id=1401220493385924638,
        ),
        Server(
            section_id=592,
            guild_id=1036712610919370834,
            channel_id=1351882503929073777,
            role_id=1298730558012264448,
        ),
    ]
