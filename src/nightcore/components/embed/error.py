"""Error embeds for the Nightcore bot."""

from discord import Color, Embed


class NoConfigFoundButCreatedEmbed(Embed):
    def __init__(self, footer_text: str, footer_icon_url: str):
        super().__init__(
            title="Конфигурация не найдена",
            description="Конфигурация не найдена для этого сервера, но она будет создана сейчас. Пожалуйста, выполните эту команду снова.",  # noqa: E501
            color=Color.red(),
        )
        self.set_footer(text=footer_text, icon_url=footer_icon_url)


class NoConfigFoundEmbed(Embed):
    def __init__(self, footer_text: str, footer_icon_url: str):
        super().__init__(
            title="Конфигурация не найдена",
            description="Конфигурация не найдена для этого сервера.",
            color=Color.red(),
        )
        self.set_footer(text=footer_text, icon_url=footer_icon_url)


class NoOptionsSuppliedEmbed(Embed):
    def __init__(self, footer_text: str, footer_icon_url: str):
        super().__init__(
            title="Не предоставлены параметры",  # noqa: RUF001
            description="Для этой команды не было предоставлено никаких параметров.",  # noqa: E501
            color=Color.yellow(),
        )
        self.set_footer(text=footer_text, icon_url=footer_icon_url)


class ValidationErrorEmbed(Embed):
    def __init__(self, msg: str, footer_text: str, footer_icon_url: str):
        super().__init__(
            title="Ошибка валидации данных",
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
            title="Отсутствие необходимых прав",
            description=msg
            or "У вас нет прав для использования этой команды.",
            color=Color.red(),
        )
        self.set_footer(text=footer_text, icon_url=footer_icon_url)


class EntityNotFoundEmbed(Embed):
    def __init__(self, entity: str, footer_text: str, footer_icon_url: str):
        super().__init__(
            title="Сущность не найдена",
            description=f"Указанная сущность `{entity}` не найдена на сервере.",  # noqa: E501
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
