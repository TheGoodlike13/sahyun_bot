from configparser import ConfigParser
from typing import Callable, Optional, TypeVar

# general purpose generic variable to be used in generic functions
T = TypeVar('T')

# if next(it, default=non_existent) is non_existent: <do stuff if 'it' was empty>
non_existent = object()

config = ConfigParser()


def identity(o: T) -> T:
    return o


# noinspection PyProtectedMember
def parse_bool(s: str, fallback: bool = None) -> bool:
    try:
        return config._convert_to_boolean(s)
    except ValueError:
        if fallback:
            return fallback

        raise


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
