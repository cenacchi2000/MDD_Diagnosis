import random
from typing import Generic, TypeVar, Callable, Iterator

T = TypeVar("T")


class CyclingShuffleIterator(Generic[T]):
    def __init__(
        self, data: list[T], compleat_iteration_cb: Callable[[None], None] | None = None
    ):
        self.data = data.copy()
        self.index = 0
        self._shuffle_data()
        self.callback = compleat_iteration_cb

    def _shuffle_data(self):
        random.shuffle(self.data)

    def __iter__(self) -> Iterator:
        return self

    def __next__(self) -> T | None:
        if len(self.data) == 0:
            if self.callback:
                self.callback()
            return None
        elif self.index >= len(self.data):
            self.index = 0
            self._shuffle_data()
            if self.callback:
                self.callback()

        value = self.data[self.index]
        self.index += 1
        return value
