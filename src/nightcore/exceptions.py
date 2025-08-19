"""Custom exceptions for the Nightcore application."""


class ConfigMissingError(Exception):
    def __init__(self, guild_id: int | None):
        self.guild_id = guild_id
        super().__init__(f"Guild config missing (guild_id={guild_id})")


class OrgRolesParsingError(Exception):
    def __init__(self, msg: str):
        self.msg = msg
        super().__init__(f"Organization roles parsing error: {msg}")


class LevelRolesParsingError(Exception):
    def __init__(self, msg: str):
        self.msg = msg
        super().__init__(f"Level roles parsing error: {msg}")
