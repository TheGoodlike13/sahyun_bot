from itertools import zip_longest
from threading import RLock
from typing import Generic, List, Optional, Iterator, Callable

from sahyun_bot.utils import T, NON_EXISTENT


class MemoryQueue(Generic[T]):
    """
    Queue which remembers items that were put into it, until forced to forget.

    Items can be added to the queue without limits.

    Offering items, however, comes with limitations. Item cannot be offered twice, as long as it is in the queue or
    memory.
    """
    def __init__(self):
        self.__lock = RLock()
        self.__queue: List[T] = []
        self.__memory: List[T] = []

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
        """
        FIFO pop operation. If an item is returned, it is memorized so that it still cannot be offered again.
        :returns next item in the queue, if any
        """
        with self.__lock:
            try:
                item = self.__queue.pop(0)
            except IndexError:
                return None

            self.__memory.append(item)
            return item

    def add(self, item: T) -> int:
        """
        Adds item to the end of this queue. Uniqueness or memory is ignored.
        :returns position the item was added to
        """
        if item is not None:
            with self.__lock:
                self.__queue.append(item)
                return len(self)

    def add_all(self, *items: T) -> List[int]:
        """
        Adds multiple items to the end of this queue. Uniqueness or memory is ignored.
        :returns positions the item were added to
        """
        with self.__lock:
            return [self.add(item) for item in items]

    def offer(self, item: T, match: Callable[[T], bool]) -> int:
        """
        Adds an item to the queue, but only if this item has not been added yet. Does not allow to add items in memory.

        If an item that matches given predicate is already in the queue, it is replaced instead. Only the last matching
        item will be replaced.

        :returns position the item was added to; 0 if it is in memory; -position if it is in queue
        """
        with self.__lock:
            if item in self.__memory:
                return 0

            return self.__already_in_queue(item) or self.__replace_or_add(item, match)

    def bump(self, match: Callable[[T], bool]) -> bool:
        """
        Bumps the last matching item to the top of the queue.
        :returns true if item was bumped, false or None if it was not found
        """
        with self.__lock:
            i = self.__find(match)
            if i >= 0:
                self.__queue.insert(0, self[i])
                del self[i + 1]
                return True

    def last(self) -> Optional[T]:
        """
        :returns last item in memory, if any
        """
        with self.__lock:
            return self.__memory[-1] if self.__memory else None

    def memory(self) -> List[T]:
        """
        :returns copy of memory
        """
        with self.__lock:
            return self.__memory[:]

    def forget(self):
        """
        Clears memory
        """
        with self.__lock:
            self.__memory.clear()

    def __already_in_queue(self, item: T) -> int:
        return -1 - self.__find(lambda t: t == item)

    def __replace_or_add(self, item, match: Callable[[T], bool]) -> int:
        i = self.__find(match)
        if i >= 0:
            self[i] = item
            return i + 1

        return self.add(item)

    def __find(self, match: Callable[[T], bool]) -> int:
        i = len(self)
        for in_queue in reversed(self):
            i -= 1
            if match(in_queue):
                return i

        return -1
