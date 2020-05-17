from configparser import ConfigParser
from typing import Callable, Optional, List

from sahyun_bot.utils import T, identity, debug_ex

config = ConfigParser()


def parse_bool(s: str, fallback: bool = None) -> bool:
    try:
        # noinspection PyProtectedMember
        return config._convert_to_boolean(s)
    except ValueError:
        if fallback:
            return fallback

        raise


def parse_list(s: str, convert: Callable[[str], T] = identity, fallback: List[T] = None) -> List[T]:
    if not s or s.isspace():
        return fallback or []

    try:
        return [convert(item.strip()) for item in s.split(',') if item and not item.isspace()]
    except Exception:
        if fallback is not None:
            return fallback

        raise


def read_config(section: str,
                key: str,
                convert: Callable[[str], T] = identity,
                fallback: T = None,
                allow_empty: bool = False) -> Optional[T]:
    value = config.get(section, key, fallback=fallback)
    if value is None or value is fallback or not allow_empty and not value:
        return fallback

    try:
        return convert(value.strip())
    except Exception as e:
        debug_ex(e, 'convert config value [{}]->{}: {}', section, key, value, silent=True)
        return fallback
