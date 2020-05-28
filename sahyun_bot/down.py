from datetime import timedelta, datetime, timezone
from threading import RLock
from typing import Dict, Optional, Tuple, List

from twitch.cache import Cache

from sahyun_bot.commander_settings import Command
from sahyun_bot.down_settings import *
from sahyun_bot.users_settings import User
from sahyun_bot.utils import debug_ex
from sahyun_bot.utils_logging import get_logger

LOG = get_logger(__name__)

ZERO_DOWNTIME = timedelta(seconds=0)


class Downtime:
    """
    Downtime for command usage.
    Supports global timeout (command can only be used once every X seconds).
    Supports per-user timeout (each user can only use the command Y times every X seconds).

    Perfect accuracy is not guaranteed.

    Supports leniency, which is 1 second by default. Can be only increased by configuration.
    Leniency ignores remaining timeouts less than itself.

    Example config:
    {'time': '10'} -> 10s global timeout for !time (and aliases)
    {'request': '900:2'} -> 15min per-user timeout for !request (and aliases) with allowance of 2
    {'any': ':2'} -> ignored, as it is not valid format
    """
    def __init__(self,
                 leniency: int = DEFAULT_LENIENCY,
                 config: Dict[str, str] = None):
        self.__leniency = timedelta(seconds=max(leniency, DEFAULT_LENIENCY))

        self.__index = 0
        self.__uses = Cache()
        self.__uses_lock = RLock()

        self.__timeout: Dict[str, timedelta] = {}
        self.__per_user: Dict[str, int] = {}
        self.__parse(config or {})

    def is_global(self, command: Command) -> bool:
        for alias in command.alias():
            if alias in self.__per_user:
                return False

        return True

    def remember_use(self, command: Command, user: User):
        downtime = self.__downtime(command)
        if downtime:
            with self.__uses_lock:
                ref = self.__key(command, user)
                self.__uses.set(ref, {'timestamp': self.__now()}, duration=downtime)

    def downtime_left(self, command: Command, user: User) -> timedelta:
        downtime = self.__downtime(command)
        if not downtime:
            return ZERO_DOWNTIME

        prefix = self.__prefix(command, user)
        with self.__uses_lock:
            matches = self.__get_matches(prefix)
            if not matches or len(matches) < self.__use_limit(command):
                return ZERO_DOWNTIME

            oldest = min(matches)
            expires_at = oldest + downtime
            remaining = expires_at - self.__now()
            return remaining if remaining > self.__leniency else ZERO_DOWNTIME

    def __downtime(self, command: Command) -> Optional[timedelta]:
        for alias in command.alias():
            if alias in self.__timeout:
                return self.__timeout[alias]

    def __key(self, command: Command, user: User) -> str:
        self.__index += 1
        return f'{command}!{user}#{self.__index}'

    def __prefix(self, command: Command, user: User) -> str:
        return f'{command}!' if self.is_global(command) else f'{command}!{user}#'

    def __get_matches(self, prefix: str) -> List[datetime]:
        self.__cleanup_cache_if_needed()
        all_matches = (self.__uses.get(k) for k in self.__uses._store if k.startswith(prefix))
        return [m['timestamp'] for m in all_matches if m]

    def __cleanup_cache_if_needed(self):
        if self.__index % 100 == 0:
            self.__uses.clean()

    def __use_limit(self, command: Command) -> int:
        for alias in command.alias():
            if alias in self.__per_user:
                return self.__per_user[alias]

        return 1

    def __now(self) -> datetime:
        return datetime.now(tz=timezone.utc)

    def __parse(self, param: Dict[str, str]):
        for alias, config in param.items():
            seconds, per_user = self.__parse_config(config)
            if seconds:
                self.__timeout[alias] = timedelta(seconds=seconds)
                if per_user:
                    self.__per_user[alias] = per_user

    def __parse_config(self, s: str) -> Tuple[int, int]:
        left, colon, right = s.partition(':')
        try:
            left = max(int(left), 0)
        except Exception as e:
            debug_ex(e, f'convert {left} to int', silent=True)
            return 0, 0

        try:
            return left, max(int(right), 0) if right else 0
        except Exception as e:
            debug_ex(e, f'convert {right} to int', silent=True)
            return left, 0
