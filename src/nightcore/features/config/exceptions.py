"""Exceptions for configuration parsing errors in Nightcore."""


class OrgRolesParsingError(Exception):
    def __init__(self, msg: str):
        self.msg = msg
        super().__init__(f"Organization roles parsing error: {msg}")


class LevelRolesParsingError(Exception):
    def __init__(self, msg: str):
        self.msg = msg
        super().__init__(f"Level roles parsing error: {msg}")


class TempVoiceRolesParsingError(Exception):
    def __init__(self, msg: str):
        self.msg = msg
        super().__init__(f"Temporary voice roles parsing error: {msg}")
