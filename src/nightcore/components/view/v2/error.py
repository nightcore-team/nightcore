"""
Error view v2 components.

Used for displaying error messages.
"""

from typing import Any, Self

from discord import Color
from discord.ui import Container, LayoutView, TextDisplay


class ErrorViewV2(LayoutView):
    def __init__(self, title: str, description: str) -> None:
        super().__init__(timeout=None)

        container = Container[Self](
            accent_color=Color.from_str("#E05263"),
        )

        container.add_item(TextDisplay[Self](f"### {title}"))
        container.add_item(TextDisplay[Self](description))

        self.add_item(container)


class NoConfigFoundButCreatedViewV2(ErrorViewV2):
    def __init__(self) -> None:
        super().__init__(
            title="Конфигурация не найдена",
            description=(
                "Конфигурация не найдена для этого сервера, но она будет "
                "создана сейчас. Пожалуйста, выполните эту команду снова."
            ),
        )


class NoConfigFoundViewV2(ErrorViewV2):
    def __init__(self) -> None:
        super().__init__(
            title="Конфигурация не найдена",
            description="Конфигурация не найдена для этого сервера.",
        )


class NoOptionsSuppliedViewV2(ErrorViewV2):
    def __init__(self) -> None:
        super().__init__(
            title="Не предоставлены параметры",
            description=(
                "Для этой команды не было предоставлено никаких параметров."
            ),
        )


class ValidationErrorViewV2(ErrorViewV2):
    def __init__(self, msg: str) -> None:
        super().__init__(
            title="Ошибка валидации данных",
            description=msg,
        )


class MissingPermissionsViewV2(ErrorViewV2):
    def __init__(self, msg: str | None = None) -> None:
        super().__init__(
            title="Отсутствие необходимых прав",
            description=msg
            or "У вас нет прав для использования этой команды.",
        )


class EntityNotFoundViewV2(ErrorViewV2):
    def __init__(self, entity: str) -> None:
        super().__init__(
            title="Сущность не найдена",
            description=(
                f"Указанная сущность `{entity}` не найдена на сервере."
            ),
        )


class StrToIntTransformFailedViewV2(ErrorViewV2):
    def __init__(self, value: Any) -> None:
        super().__init__(
            title="Ошибка валидации данных",
            description=(
                f"Ожидалось число в параметре с автокомплитом, получено {value}"  # noqa: E501
            ),
        )
