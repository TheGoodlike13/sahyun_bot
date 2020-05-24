from typing import Iterator, List


class Command:
    def __init__(self, **beans):
        pass

    def alias(self) -> Iterator[str]:
        yield type(self).__name__.lower()

    def execute(self, nick: str, params: str) -> List[str]:
        raise NotImplementedError


class CommandError(Exception):
    pass
