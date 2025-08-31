"""Error embeds for the Nightcore bot."""

from discord import Color, Embed


class NoConfigFoundButCreatedEmbed(Embed):
    def __init__(self, footer_text: str, footer_icon_url: str):
        super().__init__(
            title="No Configuration Found",
            description="No config found for this guild, but it will be created now. Please run this command again.",  # noqa
            color=Color.red(),
        )
        self.set_footer(text=footer_text, icon_url=footer_icon_url)


class NoConfigFoundEmbed(Embed):
    def __init__(self, footer_text: str, footer_icon_url: str):
        super().__init__(
            title="No Configuration Found",
            description="No config found for this guild.",
            color=Color.red(),
        )
        self.set_footer(text=footer_text, icon_url=footer_icon_url)


class NoOptionsSuppliedEmbed(Embed):
    def __init__(self, footer_text: str, footer_icon_url: str):
        super().__init__(
            title="No Options Supplied",
            description="No options were supplied for this command.",
            color=Color.yellow(),
        )
        self.set_footer(text=footer_text, icon_url=footer_icon_url)


class ValidationErrorEmbed(Embed):
    def __init__(self, msg: str, footer_text: str, footer_icon_url: str):
        super().__init__(
            title="Validation Error occurred",
            description=msg,
            color=Color.red(),
        )

        self.set_footer(text=footer_text, icon_url=footer_icon_url)


class MissingPermissionsEmbed(Embed):
    def __init__(
        self,
        footer_text: str,
        footer_icon_url: str,
        msg: str | None = None,
    ):
        super().__init__(
            title="Missing Permissions",
            description=msg
            or "You do not have permission to use this command.",
            color=Color.red(),
        )
        self.set_footer(text=footer_text, icon_url=footer_icon_url)


class EntityNotFoundEmbed(Embed):
    def __init__(self, entity: str, footer_text: str, footer_icon_url: str):
        super().__init__(
            title="Entity Not Found",
            description=f"The specified {entity} was not found.",
            color=Color.red(),
        )
        self.set_footer(text=footer_text, icon_url=footer_icon_url)


class ErrorEmbed(Embed):
    def __init__(
        self,
        title: str,
        description: str,
        footer_text: str,
        footer_icon_url: str,
    ):
        super().__init__(
            title=title,
            description=description,
            color=Color.red(),
        )
        self.set_footer(text=footer_text, icon_url=footer_icon_url)
