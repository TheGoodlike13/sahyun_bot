from typing import Iterator

from sahyun_bot.commander_settings import ResponseHook
from sahyun_bot.utils import Closeable


class ResponseMock(ResponseHook, Closeable):
    def __init__(self):
        self.__all_to_sender = []
        self.__all_to_channel = []

    def __exit__(self, *args):
        self.__all_to_sender.clear()
        self.__all_to_channel.clear()

    def to_sender(self, message: str):
        self.__all_to_sender.append(message)

    def to_channel(self, message: str):
        self.__all_to_channel.append(message)

    def all_to_sender(self) -> str:
        return '\n'.join(self.__all_to_sender)

    def all_to_channel(self) -> str:
        return '\n'.join(self.__all_to_channel)

    def all(self) -> str:
        return '\n'.join(self.__all())

    def __all(self) -> Iterator[str]:
        yield from self.__all_to_sender
        yield from self.__all_to_channel
