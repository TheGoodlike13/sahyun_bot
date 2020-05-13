from configparser import ConfigParser
from typing import Any, Callable, Optional, TypeVar

T = TypeVar('T')

config = ConfigParser()


def identity(o: Any):
    return o


# noinspection PyProtectedMember
def parse_bool(s: str):
    return config._convert_to_boolean(s)


# noinspection PyBroadException
def read_config(section: str,
                key: str,
                fallback: T = None,
                allow_empty: bool = False,
                convert: Callable[[str], T] = identity) -> Optional[T]:
    value = config.get(section, key, fallback=fallback)
    if not allow_empty and not value or value is None:
        return fallback

    try:
        return convert(value.strip())
    except Exception:
        return fallback


def print_error(e: Exception, trying_to: str = 'do something'):
    print('Error while trying to {}: {}: {}'.format(trying_to, type(e).__name__, e))
