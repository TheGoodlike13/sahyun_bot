from datetime import timedelta
from threading import RLock
from typing import Optional

from twitch.cache import Cache

from sahyun_bot.elastic import ManualUserRank
from sahyun_bot.twitchy import Twitchy
from sahyun_bot.users_settings import *
from sahyun_bot.utils import debug_ex, Closeable
from sahyun_bot.utils_elastic import ElasticAware
from sahyun_bot.utils_logging import get_logger

LOG = get_logger(__name__)

TRANSIENT_RANKS = frozenset([
    UserRank.VWR,
    UserRank.FLWR,
    UserRank.SUB,
])


class Users(ElasticAware):
    def __init__(self,
                 streamer: str,
                 tw: Twitchy = None,
                 cache_follows: int = DEFAULT_CACHE_FOLLOWS,
                 cache_viewers: int = DEFAULT_CACHE_VIEWERS,
                 use_elastic: bool = None):
        super().__init__(use_elastic)

        self.__streamer = streamer.lower()
        self.__tw = tw
        self.__cache_follows = cache_follows
        self.__cache_viewers = cache_viewers

        self.__rank_cache = Cache()
        self.__rank_lock = RLock()

    def admin(self) -> User:
        """
        :returns the admin user (streamer), with id if twitch is available
        """
        user_id = self.__tw.get_id(self.__streamer) if self.__tw else None
        return User(nick=self.__streamer, rank=UserRank.ADMIN, user_id=user_id)

    def user(self, nick: str) -> User:
        """
        Determines rank (and id, if possible) for given nick.
        :returns user object for nick
        """
        nick = nick.lower()
        rank = self.rank(nick)
        user_id = self.id(nick)
        return User(nick=nick, rank=rank, user_id=user_id)

    def rank(self, nick: str) -> UserRank:
        """
        Checks against streamer, elastic index, twitch cached & live status, in that order.
        If any of these do not contain the value, defaults to viewer.
        Finally, if twitch isn't even available, defaults to unknown. This enables basic functionality.

        :returns rank for given user
        """
        nick = nick.lower()
        user_id = self.id(nick)
        return self.__check_streamer(nick)\
            or self.__check_elastic(nick, user_id)\
            or self.__check_twitch(nick, user_id)\
            or self.__fallback()

    def id(self, nick: str) -> Optional[str]:
        """
        :returns twitch id for nick, if available
        """
        return self.__tw.get_id(nick.lower()) if self.__tw else None

    def set_manual(self, nick: str, rank: UserRank) -> bool:
        """
        Sets manual rank for given nick. Only possible if twitch & elastic index are available.

        :returns true if rank was updated, false otherwise
        """
        user_id = self.id(nick)
        if self.use_elastic and user_id:
            try:
                return ManualUserRank(_id=user_id).set_rank(rank)
            except Exception as e:
                return debug_ex(e, f'set <{nick}> to rank {rank.name}', LOG)

    def remove_manual(self, nick: str) -> bool:
        """
        Removes manual rank for given nick. Only possible if twitch & elastic index are available.

        :returns true if rank was removed, false otherwise
        """
        user_id = self.id(nick)
        if self.use_elastic and user_id:
            try:
                return ManualUserRank(_id=user_id).delete()
            except Exception as e:
                return debug_ex(e, f'remove rank for <{nick}>', LOG)

    def _manual(self, nick: str, rank: UserRank) -> Closeable:
        this = self

        class CleanManual(Closeable):
            def __enter__(self):
                this.set_manual(nick, rank)

            def close(self):
                this.remove_manual(nick)

        return CleanManual()

    def __check_streamer(self, nick: str) -> Optional[UserRank]:
        return UserRank.ADMIN if nick == self.__streamer else None

    def __check_elastic(self, nick: str, user_id: str) -> Optional[UserRank]:
        if user_id and self.use_elastic:
            try:
                manual = ManualUserRank.get(user_id, ignore=[404])
                if manual:
                    return manual.rank
            except Exception as e:
                debug_ex(e, f'get manual rank for <{nick}>', LOG)

    def __check_twitch(self, nick: str, user_id: str) -> Optional[UserRank]:
        if user_id:
            with self.__rank_lock:
                try:
                    cached = self.__rank_cache.get(user_id)
                    if cached:
                        return cached['rank']

                    is_follower = self.__tw.is_following(self.__streamer, user_id)
                    live = UserRank.FLWR if is_follower else UserRank.VWR
                    self.__rank_cache.set(user_id, {'rank': live}, duration=self.__cache_duration(is_follower))
                    return live
                except Exception as e:
                    debug_ex(e, f'get live twitch rank for <{nick}>', LOG)

    def __cache_duration(self, is_follower: bool) -> timedelta:
        seconds = self.__cache_follows if is_follower else self.__cache_viewers
        return timedelta(seconds=seconds)

    def __fallback(self) -> UserRank:
        return UserRank.VWR if self.__tw else UserRank.UNKNW
