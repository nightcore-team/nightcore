import asyncio


class TaskOffsetManager:
    def __init__(self) -> None:
        self._task_offsets: dict[str, float] = {}
        self._offset = 0.3
        self._max_offset = 0

    def get_offset(self, name: str) -> float:
        task_offset = self._task_offsets.get(name)

        if task_offset is not None:
            return task_offset

        self._max_offset += self._offset

        return self._task_offsets.setdefault(name, self._max_offset)

    async def sleep(self, name: str) -> None:
        offset = self.get_offset(name)
        await asyncio.sleep(offset)
