from typing import Iterator, List

from assertpy import assert_that

from sahyun_bot.commander_settings import ResponseHook
from sahyun_bot.utils import Closeable


class ResponseMock(ResponseHook, Closeable):
    def __init__(self):
        self.__all_to_sender: List[str] = []
        self.__all_to_channel: List[str] = []
        self.__all_to_debug: List[str] = []

    def close(self):
        self.__all_to_sender.clear()
        self.__all_to_channel.clear()
        self.__all_to_debug.clear()

    def to_sender(self, message: str):
        self.__all_to_sender.append(message)
        return True

    def to_channel(self, message: str):
        self.__all_to_channel.append(message)
        return True

    def to_debug(self, message: str):
        self.__all_to_debug.append(message)

    def all_to_sender(self) -> str:
        return '\n'.join(self.__all_to_sender)

    def all_to_channel(self) -> str:
        return '\n'.join(self.__all_to_channel)

    def all_to_debug(self) -> str:
        return '\n'.join(self.__all_to_debug)

    def all_back(self) -> str:
        return '\n'.join(self.__messages())

    def all(self) -> str:
        return '\n'.join(self.__all())

    def assert_silent_failure(self):
        assert_that(self.all()).is_equal_to('failure')

    def assert_failure(self, *args):
        self.__assert_response('failure', *args)

    def assert_success(self, *args):
        self.__assert_response('success', *args)

    def __assert_response(self, debug: str, *args):
        if args:
            assert_that(self.all_back()).contains(*args)

        assert_that(self.all_to_debug()).contains(debug)

    def __messages(self) -> Iterator[str]:
        yield from self.__all_to_sender
        yield from self.__all_to_channel

    def __all(self) -> Iterator[str]:
        yield from self.__messages()
        yield from self.__all_to_debug
