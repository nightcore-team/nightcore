import inspect  # noqa: D100
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class CallSite:
    file: str
    line: int
    function: str

    def __str__(self) -> str:
        """Return a human-readable string representation of the call site, e.g. 'src/infra/db/uow.py:42 in my_function()'."""  # noqa: E501
        return f"{self.file}:{self.line} in {self.function}()"


def find_callsite(
    *, skip_functions: set[str] | None = None
) -> CallSite | None:
    """Find the first call site outside of internal/library frames."""
    if skip_functions is None:
        skip_functions = set()

    skip_functions |= {
        "find_callsite",
        "__aenter__",
        "__aexit__",
        "__enter__",
        "__exit__",
        "start",  # uow method
    }

    for frame_info in inspect.stack()[1:]:  # [0] — сам find_callsite
        func = frame_info.function
        filename = frame_info.filename

        if func in skip_functions:
            continue

        if "contextlib.py" in filename or "asyncio" in filename:
            continue

        if "site-packages" in filename:
            continue

        try:
            rel_path = Path(filename).relative_to(Path.cwd())
            file_display = str(rel_path)
        except ValueError:
            file_display = filename

        return CallSite(
            file=file_display,
            line=frame_info.lineno,
            function=func,
        )

    return None
