"""
Contains utilities which help with parsing settings & similar.

This module contains a reference to a global config parser. Please initialize it before use.
"""
from configparser import ConfigParser
from typing import Callable, Optional, List, Dict

from sahyun_bot.utils import T, V, identity, debug_ex

config = ConfigParser()


def parse_bool(s: str, fallback: bool = None) -> bool:
    """
    :returns true or false, using ConfigParser semantics
    :raises ValueError if value cannot be parsed and no fallback is provided
    """
    try:
        return config._convert_to_boolean(s)
    except ValueError:
        if fallback is not None:
            return fallback

        raise


def parse_list(s: str, convert: Callable[[str], T] = identity, fallback: List[T] = None) -> List[T]:
    """
    :returns list of values converted from comma separated substrings
    :raises ValueError if value cannot be parsed and no fallback is provided
    """
    if not s or s.isspace():
        return fallback or []

    try:
        return [convert(item.strip()) for item in s.split(',') if item and not item.isspace()]
    except Exception as e:
        if fallback is not None:
            return fallback

        raise ValueError(f'Could not parse as comma separated list: {s}') from e


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
        debug_ex(e, f'convert config value [{section}]->{key}: {value}', silent=True)
        return fallback


def read_dynamic_config(section: str,
                        convert_key: Callable[[str], T] = identity,
                        convert_value: Callable[[str], V] = identity,
                        fallback: V = None) -> Dict[T, V]:
    result = {}

    if config.has_section(section):
        for key, value in config.items(section):
            try:
                key = convert_key(key.strip())
            except Exception as e:
                debug_ex(e, f'convert config key [{section}]->{key}: {value}', silent=True)
                key = None

            try:
                value = convert_value(value.strip())
            except Exception as e:
                debug_ex(e, f'convert config value [{section}]->{key}: {value}', silent=True)
                value = fallback

            if key and value:
                result[key] = value

    return result
