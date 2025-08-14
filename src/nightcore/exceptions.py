"""Custom exceptions for the Nightcore application."""


class ConfigMissingError(Exception):
    def __init__(self, guild_id: int | None):
        self.guild_id = guild_id
        super().__init__(f"Guild config missing (guild_id={guild_id})")
