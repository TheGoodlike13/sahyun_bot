from datetime import timedelta
from threading import RLock

from twitch.cache import Cache

from sahyun_bot.elastic import ManualUserRank
from sahyun_bot.twitchy import Twitchy
from sahyun_bot.users_settings import UserRank, User
from sahyun_bot.utils import debug_ex
from sahyun_bot.utils_logging import get_logger

LOG = get_logger(__name__)


TRANSIENT_RANKS = frozenset([
    UserRank.VWR,
    UserRank.FLWR,
    UserRank.SUB,
])


class Users:
    def __init__(self, streamer: str, tw: Twitchy = None, use_elastic: bool = False):
        self.__streamer = streamer.lower()
        self.__tw = tw
        self.__use_elastic = use_elastic

        self.__rank_cache = Cache()
        self.__rank_lock = RLock()

    def set_use_elastic(self, use: bool):
        self.__use_elastic = use

    def get(self, nick: str) -> User:
        """
        Determines rank (and id, if possible) for given nick.
        Checks against streamer, elastic index, twitch cached & live status, in that order.
        If any of these do not contain the value, defaults to viewer.
        Finally, if twitch isn't even available, defaults to unknown. This enables basic functionality.

        :returns user object for nick
        """
        nick = nick.lower()
        user_id = self.__tw.get_id(nick) if self.__tw else None
        rank = self.__get_rank(nick, user_id)
        return User(nick=nick, rank=rank, user_id=user_id)

    def set_manual(self, nick: str, rank: UserRank) -> bool:
        """
        Sets manual rank for given nick. Only possible if twitch & elastic index are available.

        :returns true if rank was updated, false otherwise
        """
        if not self.__tw:
            return False

        user_id = self.__tw.get_id(nick.lower())
        if not user_id:
            return False

        try:
            return ManualUserRank(_id=user_id).set_rank(rank)
        except Exception as e:
            return debug_ex(e, f'set rank {rank} to <{nick}>', LOG)

    def __get_rank(self, nick: str, user_id: str = None) -> UserRank:
        if nick == self.__streamer:
            return UserRank.ADMIN

        if user_id and self.__use_elastic:
            try:
                manual = ManualUserRank.get(user_id)
                if manual:
                    return manual.rank
            except Exception as e:
                debug_ex(e, f'get manual rank for <{nick}>', LOG)

        if user_id:
            with self.__rank_lock:
                try:
                    cached = self.__rank_cache.get(user_id)
                    if cached:
                        return cached['rank']

                    is_follower = self.__tw.is_following(self.__streamer, user_id)
                    live = UserRank.FLWR if is_follower else UserRank.VWR
                    duration = timedelta(minutes=5) if is_follower else timedelta(seconds=10)
                    self.__rank_cache.set(user_id, {'rank': live}, duration=duration)
                    return live
                except Exception as e:
                    debug_ex(e, f'get live twitch rank for <{nick}>', LOG)

        return UserRank.VWR if self.__tw else UserRank.UNKNW
