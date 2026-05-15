import asyncio
from collections.abc import Hashable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum, auto


class AsyncioLockTypeEnum(Enum):
    TicketManageAction = auto()


@dataclass
class _LockEntry:
    lock: asyncio.Lock = field(init=False)
    refs: int = 0

    def __post_init__(self):
        self.lock = asyncio.Lock()


class AsyncioLockManager:
    def __init__(self) -> None:
        self._locks: dict[
            tuple[AsyncioLockTypeEnum, Hashable], _LockEntry
        ] = {}

    @asynccontextmanager
    async def acquire(self, type_: AsyncioLockTypeEnum, key: Hashable):
        k = (type_, key)
        if k not in self._locks:
            self._locks[k] = _LockEntry()

        entry = self._locks[k]
        entry.refs += 1
        try:
            async with entry.lock:
                yield
        finally:
            entry.refs -= 1
            if entry.refs == 0:
                del self._locks[k]
