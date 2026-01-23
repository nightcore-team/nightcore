"""Custom exceptions for the Nightcore application."""


class ConfigMissingButCreatingError(Exception):
    def __init__(self, guild_id: int | None):
        self.guild_id = guild_id
        super().__init__(f"Guild config missing (guild_id={guild_id})")


class ConfigMissingError(Exception):
    def __init__(self, guild_id: int | None):
        self.guild_id = guild_id
        super().__init__(f"Guild config missing (guild_id={guild_id})")


class FieldNotConfiguredError(Exception):
    def __init__(self, field_name: str):
        self.field_name = field_name
        super().__init__(
            f"Необходимый параметр (`{field_name}`) не настроен в конфигурации сервера."  # noqa: E501
        )


class CommandDontHavePermissionsFlagError(Exception):
    def __init__(self, command_name: str):
        self.command_name = command_name
        super().__init__(f"{command_name}")


class TransformStrToIntError(Exception):
    def __init__(self, msg: str) -> None:
        self.msg = msg
        super().__init__(msg)
