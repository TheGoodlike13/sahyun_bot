from itertools import zip_longest
from threading import RLock
from typing import Generic, List, Optional, Iterator, Callable

from sahyun_bot.utils import T, NON_EXISTENT


class BumpQueue(Generic[T]):
    def __init__(self):
        self.__lock = RLock()
        self.__queue: List[T] = []
        self.__dump: List[T] = []

    def __len__(self) -> int:
        with self.__lock:
            return len(self.__queue)

    def __getitem__(self, key) -> T:
        with self.__lock:
            return self.__queue[key]

    def __setitem__(self, key, value):
        with self.__lock:
            self.__queue[key] = value

    def __delitem__(self, key):
        with self.__lock:
            del self.__queue[key]

    def __iter__(self) -> Iterator[T]:
        with self.__lock:
            copy = self.__queue[:]

        return iter(copy)

    def __reversed__(self) -> Iterator[T]:
        with self.__lock:
            reverse_copy = self.__queue[::-1]

        return iter(reverse_copy)

    def __contains__(self, item: T) -> bool:
        with self.__lock:
            return item in self.__queue

    def __str__(self) -> str:
        with self.__lock:
            return str(self.__queue)

    def __eq__(self, o: object) -> bool:
        try:
            # noinspection PyTypeChecker
            other = iter(o)
        except TypeError:
            return False

        with self.__lock:
            return all(a == b for a, b in zip_longest(self, other, fillvalue=NON_EXISTENT))

    def next(self) -> Optional[T]:
        with self.__lock:
            try:
                item = self.__queue.pop(0)
            except IndexError:
                return None

            self.__dump.append(item)
            return item

    def add(self, item: T):
        if item is not None:
            with self.__lock:
                self.__queue.append(item)
                return len(self)

    def add_all(self, *items: T) -> List[int]:
        with self.__lock:
            return [self.add(item) for item in items]

    def replace(self, item: T, match: Callable[[T], bool]) -> int:
        with self.__lock:
            i = self.__find(match)
            if i >= 0:
                self[i] = item
                return i + 1

            return self.add(item)

    def bump(self, match: Callable[[T], bool]) -> bool:
        with self.__lock:
            i = self.__find(match)
            if i >= 0:
                self.__queue.insert(0, self[i])
                del self[i + 1]
                return True

    def last(self) -> Optional[T]:
        with self.__lock:
            return self.__dump[-1] if self.__dump else None

    def dump(self) -> List[T]:
        with self.__lock:
            return self.__dump[:]

    def clean(self):
        with self.__lock:
            return self.__dump.clear()

    def __find(self, match: Callable[[T], bool]) -> int:
        i = len(self)
        for in_queue in reversed(self):
            i -= 1
            if match(in_queue):
                return i

        return -1
